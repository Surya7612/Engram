from __future__ import annotations

import re

from engram.agents.llm import complete_text
from engram.config import Settings
from engram.models.schemas import ArtifactType, Evidence

_CITATION = re.compile(
    r"\b(?:ADR|INC|PR)-\d+\b|\bCOMMIT-[a-f0-9]+\b|\b(?:adr|inc|pr|svc)-[a-z0-9-]+\b",
    re.I,
)

_PACK_ORDER = {
    ArtifactType.ADR: 0,
    ArtifactType.INCIDENT: 1,
    ArtifactType.PULL_REQUEST: 2,
    ArtifactType.SERVICE: 3,
}

_SYSTEM = """You answer engineering questions using ONLY the supplied evidence.
You MUST cite artifact labels from the list (ADR-12, INC-45, PR-123, COMMIT-abc1234, svc-auth).
Prefer ADRs for policy/ownership questions and incidents for outage questions.
Do not invent artifact ids. Only say evidence is insufficient if the list is empty."""


def pack_evidence(evidence: list[Evidence], limit: int = 16) -> list[Evidence]:
    ordered = sorted(evidence, key=lambda item: _PACK_ORDER.get(item.artifact_type, 9))
    return ordered[:limit]


def evidence_list_answer(evidence: list[Evidence]) -> str:
    packed = pack_evidence(evidence, limit=8)
    if not packed:
        return "No grounded context found."
    lines = [f"- {item.label}: {item.snippet[:160]}" for item in packed]
    return "Grounded engineering context retrieved for your question.\n\n" + "\n".join(lines)


def answer_from_evidence(settings: Settings, task: str, evidence: list[Evidence]) -> tuple[str, str]:
    fallback = evidence_list_answer(evidence)
    packed = pack_evidence(evidence, limit=16)
    blob = "\n".join(f"{item.artifact_id} | {item.label} | {item.snippet[:220]}" for item in packed)
    generated = complete_text(
        settings,
        _SYSTEM,
        f"Task: {task}\n\nEvidence:\n{blob or '(none)'}",
    )
    if generated:
        return generated.strip(), "llm"
    return fallback, "evidence_list"


def cited_tokens(answer: str) -> list[str]:
    return _CITATION.findall(answer or "")


def _canon(token: str) -> str:
    text = token.lower().replace(" ", "")
    match = re.match(r"^(adr|inc|pr)-0*(\d+)$", text)
    if match:
        return f"{match.group(1)}-{int(match.group(2))}"
    return text


def _resolve(token: str, evidence: list[Evidence]) -> str | None:
    needle = _canon(token)
    for item in evidence:
        if needle in {_canon(item.artifact_id), _canon(item.label)}:
            return item.artifact_id
    return None


def score_groundedness(answer: str, evidence: list[Evidence]) -> dict:
    retrieved = sorted({item.artifact_id for item in evidence})
    cited = cited_tokens(answer)
    supported = []
    unsupported = []
    for token in cited:
        resolved = _resolve(token, evidence)
        if resolved:
            supported.append(resolved)
        else:
            unsupported.append(token)
    n = len(cited)
    abstained = bool(evidence) and n == 0
    if abstained:
        supported_rate = 0.0
        hallucination_risk = 0.0
    elif n:
        supported_rate = len(supported) / n
        hallucination_risk = 1.0 - supported_rate
    else:
        supported_rate = 1.0
        hallucination_risk = 0.0
    return {
        "cited": cited,
        "supported_ids": sorted(set(supported)),
        "unsupported": unsupported,
        "supported_citation_rate": round(supported_rate, 3),
        "hallucination_risk": round(hallucination_risk, 3),
        "abstained": abstained,
        "retrieved_ids": retrieved,
        "method": "lexical_citation_check",
    }
