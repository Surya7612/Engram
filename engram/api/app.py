from contextlib import asynccontextmanager
from pathlib import Path
import threading

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from engram import __version__
from engram.config import get_settings
from engram.engine import EngramEngine
from engram.eval.harness import run_eval
from engram.ingestion.github import GitHubRateLimitError, ingest_github
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
    SituationRequest,
    SituationResponse,
)
from engram.situation.resolve import explain_situation

engine: EngramEngine | None = None
_WEBSITE = Path(__file__).resolve().parents[2] / "website"
_SAMPLE_RUN_SERVICES = {"auth service", "email service", "svc-auth", "svc-email"}
_boot: dict = {"seeded": False, "seed_error": None, "seeding": False}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bind quickly on cold start; seed demo org without blocking health/meta."""
    global engine
    settings = get_settings()
    _boot.update(seeded=False, seed_error=None, seeding=False)
    engine = EngramEngine(settings)

    def _seed() -> None:
        _boot["seeding"] = True
        try:
            seed_from_sample(settings, graph=engine.graph, vectors=engine.vectors)
            _boot["seeded"] = True
            _boot["seed_error"] = None
        except Exception as exc:  # noqa: BLE001 — surface on /meta for operators
            _boot["seed_error"] = str(exc)
            _boot["seeded"] = False
        finally:
            _boot["seeding"] = False

    if settings.seed_on_boot or settings.public_mode:
        thread = threading.Thread(target=_seed, name="engram-boot-seed", daemon=True)
        thread.start()
        # Hash seed is typically <2s; don't hold Render's gate open longer than this.
        thread.join(timeout=12.0)
    else:
        _boot["seeded"] = True

    yield
    if engine:
        engine.close()


settings = get_settings()
app = FastAPI(
    title="Engram",
    description=(
        "Context, routing & safety layer around coding agents (V1–V3 alpha). "
        "Public try: seeded query, preflight, sample Auth risk loop. "
        "Not multi-tenant SaaS; candidates are never merged."
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
    if get_settings().public_mode and not _boot["seeded"]:
        raise HTTPException(status_code=503, detail="Public demo seed is not ready.")
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")
    return engine


def _capabilities(settings) -> dict:
    return {
        "github_ingest": not settings.public_mode,
        "outcome_resolve": not settings.public_mode,
        "query": True,
        "preflight": True,
        "situation": True,
        "sample_risk_run": True,
        "clone_run": not settings.public_mode,
        "eval": not settings.public_mode,
        "accept_client_github_token": not settings.public_mode,
    }


@app.get("/live")
def live() -> dict:
    """Liveness for keep-alive pings — available as soon as the process accepts traffic."""
    return {"status": "live", "version": __version__}


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
        "seeded": _boot["seeded"],
        "seeding": _boot["seeding"],
        "seed_error": _boot["seed_error"],
        "github_token_configured": bool((settings.github_token or "").strip()),
        "capabilities": _capabilities(settings),
        "scope": (
            "Public try: seeded query, preflight, situation explain, "
            "sample Auth risk loop. No shared ingestion or outcome writes, no BYO clone/run, no merge/push."
            if settings.public_mode
            else "Local/dev mode: full CLI surfaces including clone worktrees and on-call companion."
        ),
    }


@app.post("/ingest/sample")
def ingest_sample() -> dict:
    if get_settings().public_mode:
        raise HTTPException(status_code=403, detail="Sample reset is disabled in public try mode.")
    eng = _get_engine()
    return seed_from_sample(get_settings(), graph=eng.graph, vectors=eng.vectors)


@app.post("/ingest/github")
def ingest_github_repo(request: GitHubIngestRequest) -> dict:
    settings = get_settings()
    if settings.public_mode:
        raise HTTPException(status_code=403, detail="GitHub ingestion is disabled on the shared public demo. Use local/dev mode.")
    eng = _get_engine()
    limit = request.limit
    token = request.token
    try:
        return ingest_github(
            settings,
            repo=request.repo,
            service=request.service,
            limit=limit,
            token=token,
            graph=eng.graph,
            vectors=eng.vectors,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GitHubRateLimitError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        # Older httpx paths may still surface GitHub's 403 rate-limit text.
        msg = str(exc)
        if "rate limit" in msg.casefold():
            raise HTTPException(
                status_code=429,
                detail=(
                    "GitHub API rate limit exceeded for this host. "
                    "For local/dev ingestion, configure a server-side GITHUB_TOKEN "
                    "(limit access to required repos). Shared public ingestion is disabled."
                ),
            ) from exc
        raise HTTPException(status_code=502, detail=f"GitHub ingest failed: {exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


@app.post("/situation", response_model=SituationResponse)
def situation(request: SituationRequest) -> SituationResponse:
    """Ephemeral on-call screen context → grounded Engram answer. Screen text is not stored."""
    eng = _get_engine()
    try:
        return explain_situation(eng, request)
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
    if get_settings().public_mode:
        raise HTTPException(status_code=403, detail="Shared outcomes are disabled in public try mode.")
    store = _outcomes()
    if stats:
        return store.stats()
    return {"outcomes": store.list(limit)}


@app.post("/outcomes/{outcome_id}/resolve")
def resolve_outcome(outcome_id: str, request: ResolveRequest) -> dict:
    if get_settings().public_mode:
        raise HTTPException(status_code=403, detail="Outcome resolution is disabled in public try mode.")
    try:
        return _outcomes().resolve(outcome_id, request.decision, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
