from __future__ import annotations

import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from engram.models.schemas import AgentRunResult

DECISIONS = ("pending", "not_required", "approved", "rejected")
RESOLVED = ("approved", "rejected")
_STOP = {"the", "and", "for", "from", "with", "that", "this", "into"}


def _norm(text: str) -> str:
    return " ".join((text or "").casefold().split())


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in "".join(ch if ch.isalnum() else " " for ch in (text or "").casefold()).split()
        if len(token) > 2 and token not in _STOP
    }


def _task_score(query: str, stored: str) -> float:
    if _norm(query) == _norm(stored):
        return 1.0
    left, right = _tokens(query), _tokens(stored)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


class OutcomeStore:
    """Append-only outcome log. This is telemetry, not a learned routing policy."""

    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, result: AgentRunResult, extra: dict | None = None) -> dict:
        payload = extra or {}
        record = {
            "id": uuid.uuid4().hex[:12],
            "ts": datetime.now(timezone.utc).isoformat(),
            "task": result.task,
            "service": result.service,
            "gate": result.gate.value,
            "human_required": result.human_required,
            "human_decision": "pending" if result.human_required else "not_required",
            "instantiated": result.instantiated,
            "manager_overridden": result.manager_overridden,
            "violations": (result.risk or {}).get("violations") or [],
            "reviewer_findings": len(result.review.findings) if result.review else 0,
            "high_findings": (
                sum(1 for item in result.review.findings if item.severity == "high")
                if result.review
                else 0
            ),
            "sandbox_id": result.candidate.sandbox_id if result.candidate else None,
            "merged": False,
            **payload,
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        return record

    def list(self, limit: int = 20) -> list[dict]:
        rows = self._read()
        if limit <= 0:
            return rows
        return rows[-limit:]

    def latest(self) -> dict | None:
        rows = self._read()
        return rows[-1] if rows else None

    def similar(self, service: str, task: str, *, limit: int = 5) -> list[dict]:
        """Resolved human decisions on similar tasks. Lookup, not a trained policy."""
        want_service = (service or "").casefold().strip()
        hits: list[tuple[float, dict]] = []
        for row in reversed(self._read()):
            if row.get("human_decision") not in RESOLVED:
                continue
            if (row.get("service") or "").casefold().strip() != want_service:
                continue
            score = _task_score(task, row.get("task") or "")
            if score < 0.5:
                continue
            hits.append((score, row))
        seen: set[str] = set()
        out: list[dict] = []
        for _, row in hits:
            rid = str(row.get("id") or "")
            if not rid or rid in seen:
                continue
            seen.add(rid)
            out.append(
                {
                    "id": rid,
                    "human_decision": row.get("human_decision"),
                    "human_note": row.get("human_note") or "",
                    "gate": row.get("gate"),
                    "task": row.get("task"),
                }
            )
            if len(out) >= limit:
                break
        return out

    def get(self, outcome_id: str) -> dict | None:
        for record in reversed(self._read()):
            if record.get("id") == outcome_id or str(record.get("id") or "").startswith(outcome_id):
                return record
        return None

    def resolve(self, outcome_id: str, decision: str, note: str = "") -> dict:
        decision = decision.lower().strip()
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        found = self.get(outcome_id)
        if not found:
            raise ValueError(f"Outcome not found: {outcome_id}")
        rows = self._read()
        updated = None
        for record in rows:
            if record.get("id") != found["id"]:
                continue
            record["human_decision"] = decision
            record["human_note"] = note
            record["merged"] = False
            updated = record
        if updated is None:
            raise ValueError(f"Outcome not found: {outcome_id}")
        self._path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        return updated

    def stats(self) -> dict:
        rows = self._read()
        gates = Counter(row.get("gate") for row in rows)
        decisions = Counter(row.get("human_decision") for row in rows)
        return {
            "n": len(rows),
            "gates": dict(gates),
            "human_decisions": dict(decisions),
            "manager_override_rate": round(
                sum(1 for row in rows if row.get("manager_overridden")) / len(rows), 3
            )
            if rows
            else 0.0,
            "block_rate": round(sum(1 for row in rows if row.get("gate") == "block") / len(rows), 3)
            if rows
            else 0.0,
            "note": "Telemetry only. Not a learned routing policy.",
        }

    def _read(self) -> list[dict]:
        if not self._path.exists():
            return []
        rows = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
        return rows
