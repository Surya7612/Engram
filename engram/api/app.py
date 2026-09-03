from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from engram import __version__
from engram.config import get_settings
from engram.engine import EngramEngine
from engram.eval.harness import run_eval
from engram.ingestion.github import ingest_github
from engram.ingestion.seed import seed_from_sample
from engram.learning.store import OutcomeStore
from engram.models.schemas import (
    AgentRunRequest,
    AgentRunResult,
    GitHubIngestRequest,
    HealthResponse,
    PreflightRequest,
    PreflightPacket,
    QueryRequest,
    QueryResponse,
    ResolveRequest,
)

engine: EngramEngine | None = None
_WEBSITE = Path(__file__).resolve().parents[2] / "website"
_SAMPLE_RUN_SERVICES = {"auth service", "email service", "svc-auth", "svc-email"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    settings = get_settings()
    if settings.seed_on_boot or settings.public_mode:
        seed_from_sample(settings)
    engine = EngramEngine(settings)
    yield
    if engine:
        engine.close()


settings = get_settings()
app = FastAPI(
    title="Engram",
    description=(
        "Context engine + routers. Public try scope: GitHub ingest, query, preflight, "
        "sample Auth risk loop. Not a multi-tenant SaaS."
    ),
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/try")


@app.get("/try")
def try_ui() -> RedirectResponse:
    return RedirectResponse(url="/site/try.html")


if _WEBSITE.exists():
    app.mount("/site", StaticFiles(directory=_WEBSITE), name="site")


def _get_engine() -> EngramEngine:
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return engine


def _capabilities(settings) -> dict:
    return {
        "github_ingest": True,
        "query": True,
        "preflight": True,
        "sample_risk_run": True,
        "clone_run": not settings.public_mode,
        "eval": not settings.public_mode,
        "accept_client_github_token": not settings.public_mode,
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    eng = _get_engine()
    checks = eng.health()
    ok = checks["neo4j"] and checks["qdrant"]
    return HealthResponse(
        status="ok" if ok else "degraded",
        neo4j=checks["neo4j"],
        qdrant=checks["qdrant"],
        version=__version__,
    )


@app.get("/meta")
def meta() -> dict:
    settings = get_settings()
    return {
        "version": __version__,
        "public_mode": settings.public_mode,
        "store": settings.store,
        "capabilities": _capabilities(settings),
        "scope": (
            "Hosted try: public GitHub ingest (capped), query, preflight, sample Auth risk loop. "
            "No BYO clone/run, no merge/push, not multi-tenant SaaS."
            if settings.public_mode
            else "Local/dev mode: full CLI surfaces including clone worktrees."
        ),
    }


@app.post("/ingest/sample")
def ingest_sample() -> dict:
    return seed_from_sample(get_settings())


@app.post("/ingest/github")
def ingest_github_repo(request: GitHubIngestRequest) -> dict:
    settings = get_settings()
    limit = request.limit
    token = request.token
    if settings.public_mode:
        limit = min(limit, settings.public_ingest_limit)
        # Recruiters use public repos; do not accept browser-supplied PATs on the shared demo.
        token = None
    try:
        return ingest_github(
            settings,
            repo=request.repo,
            service=request.service,
            limit=limit,
            token=token,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"GitHub ingest failed: {exc}") from exc


@app.post("/preflight", response_model=PreflightPacket)
def preflight(request: PreflightRequest) -> PreflightPacket:
    eng = _get_engine()
    try:
        return eng.preflight(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    eng = _get_engine()
    try:
        return eng.query(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/eval")
def eval_retrieval() -> dict:
    if get_settings().public_mode:
        raise HTTPException(status_code=403, detail="Eval harness is disabled in public try mode.")
    return run_eval(get_settings())


@app.post("/run", response_model=AgentRunResult)
def run_agents(request: AgentRunRequest) -> AgentRunResult:
    settings = get_settings()
    if settings.public_mode:
        if request.repo:
            raise HTTPException(
                status_code=403,
                detail="BYO clone/run is disabled on the public demo. Use the sample Auth risk loop.",
            )
        if request.service.strip().lower() not in _SAMPLE_RUN_SERVICES:
            raise HTTPException(
                status_code=403,
                detail="Public demo only runs sample Auth Service / Email Service.",
            )
        request = request.model_copy(update={"token": None, "repo": None})
    eng = _get_engine()
    try:
        return eng.run_agents(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _outcomes() -> OutcomeStore:
    return OutcomeStore(get_settings().local_data_dir / "outcomes.jsonl")


@app.get("/outcomes")
def list_outcomes(limit: int = 20, stats: bool = False) -> dict:
    store = _outcomes()
    if stats:
        return store.stats()
    return {"outcomes": store.list(limit)}


@app.post("/outcomes/{outcome_id}/resolve")
def resolve_outcome(outcome_id: str, request: ResolveRequest) -> dict:
    try:
        return _outcomes().resolve(outcome_id, request.decision, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
