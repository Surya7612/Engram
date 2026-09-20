from __future__ import annotations

import re
from engram.config import Settings
from engram.models.schemas import QueryRequest, SituationRequest, SituationResponse

_SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{10,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b"),
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
]

_SERVICE_KEYWORDS: list[tuple[tuple[str, ...], str]] = [
    (("payment-worker", "payments", "settlement", "/settlements", "settlements"), "Payments Service"),
    (("auth", "session", "token refresh", "login"), "Auth Service"),
    (("redis", "cache eviction"), "Redis Cache"),
    (("email", "password-reset"), "Email Service"),
    (("user service", "user profile"), "User Service"),
    (("api gateway",), "API Gateway"),
]

_ENTITY_PATTERNS = [
    ("incident", re.compile(r"\bINC-?(\d+)\b", re.I)),
    ("pull_request", re.compile(r"\bPR[#\s-]*(\d+)\b", re.I)),
    ("endpoint", re.compile(r"\bPOST\s+(/\S+)", re.I)),
    ("worker", re.compile(r"\b([a-z0-9]+-worker)\b", re.I)),
    ("service_slug", re.compile(r"\b([a-z0-9]+-(?:api|service|worker))\b", re.I)),
]


def redact_screen_text(text: str) -> str:
    cleaned = text or ""
    for pattern in _SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned


def extract_entities(text: str) -> list[dict]:
    entities: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in _ENTITY_PATTERNS:
        for match in pattern.finditer(text or ""):
            value = match.group(0)
            key = (kind, value.casefold())
            if key in seen:
                continue
            seen.add(key)
            entities.append({"kind": kind, "value": value})
    return entities


def infer_service_from_screen(text: str, hint: str | None = None) -> str | None:
    if hint and hint.strip():
        return hint.strip()
    lowered = (text or "").casefold()
    for keywords, service in _SERVICE_KEYWORDS:
        if any(keyword in lowered for keyword in keywords):
            return service
    return None


def load_situation_fixture(settings: Settings, name: str = "payment-worker") -> str:
    slug = name.strip().lower().replace("_", "-")
    if slug in {"payment-worker", "payment-worker-datadog", "datadog"}:
        path = settings.data_dir / "situations" / "payment-worker-datadog.txt"
    else:
        path = settings.data_dir / "situations" / f"{slug}.txt"
    if not path.exists():
        raise ValueError(f"Unknown situation fixture: {name}")
    return path.read_text(encoding="utf-8")


def explain_situation(engine, request: SituationRequest) -> SituationResponse:
    """Resolve ephemeral screen text against the context engine. Does not persist screen text."""
    redacted = redact_screen_text(request.screen_text)
    entities = extract_entities(redacted)
    service = infer_service_from_screen(redacted, request.service)
    if service is None:
        service = engine._infer_service(f"{redacted}\n{request.question}") or "Payments Service"

    question = (request.question or "").strip() or "What's happening here?"
    composed = (
        f"{question}\n\n"
        f"Visible operational context (ephemeral, not stored):\n{redacted}\n\n"
        "Prefer owner, related incidents, related PRs, ADRs/runbooks, and concrete next checks."
    )
    query = engine.query(
        QueryRequest(
            question=composed,
            service=service,
            mode=request.mode,
            top_k=request.top_k,
        )
    )
    return SituationResponse(
        service=service,
        question=question,
        entities=entities,
        answer=query.answer,
        evidence=query.evidence,
        retrieval=query.retrieval,
        ephemeral=True,
        note="Screen text was used as ephemeral query context only and was not stored as Engram memory.",
    )
