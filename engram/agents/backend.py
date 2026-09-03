from __future__ import annotations

import re

from engram.agents.llm import complete_json
from engram.agents.sandbox import Sandbox
from engram.config import Settings
from engram.models.schemas import CandidateChange, PreflightPacket

_SYSTEM = """You are Engram's Backend agent. Propose file edits inside the git worktree only.
You cannot merge, push, commit, or touch files outside the worktree.
Honor constraints when you can; if the task conflicts with an ADR, still produce a candidate so the reviewer can flag it.
Prefer editing an existing small text/code file. Do not invent large new modules.
Return JSON: {"files": [{"path": "relative/path", "content": "full file contents"}], "notes": "..."}"""

_MAX_LIST = 24
_MAX_CHARS = 2500


def implement(settings: Settings, packet: PreflightPacket, constraints: list[str], sandbox: Sandbox) -> CandidateChange:
    listing = []
    for rel in sandbox.list_files(limit=_MAX_LIST):
        body = sandbox.read(rel)
        if len(body) > _MAX_CHARS:
            body = body[:_MAX_CHARS] + "\n… [truncated]"
        listing.append(f"--- {rel} ---\n{body}")
    payload = complete_json(
        settings,
        _SYSTEM,
        (
            f"Task: {packet.task}\n"
            f"Source: {sandbox.source_repo or 'fixture'}\n"
            f"Constraints (Engram, not optional):\n- "
            + "\n- ".join(constraints)
            + "\n\nSandbox files (subset):\n"
            + "\n".join(listing)
        ),
    )
    if payload and isinstance(payload.get("files"), list):
        notes = str(payload.get("notes") or "LLM candidate")
        _apply_files(sandbox, payload["files"])
    else:
        notes = _deterministic_edit(packet.task, sandbox)

    return CandidateChange(
        sandbox_id=sandbox.sandbox_id,
        files_touched=sandbox.files_touched(),
        diff=sandbox.unified_diff(),
        notes=notes,
        applied_to_origin=False,
        kind=sandbox.kind,
        branch=sandbox.branch,
        base_sha=sandbox.base_sha,
        source_repo=sandbox.source_repo,
    )


def _apply_files(sandbox: Sandbox, files: list) -> None:
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        content = item.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            continue
        sandbox.write(path, content)


def _deterministic_edit(task: str, sandbox: Sandbox) -> str:
    task_l = task.lower()
    files = sandbox.list_files(limit=80)
    if "typo" in task_l or "copy" in task_l:
        for rel in files:
            text = sandbox.read(rel)
            if "passwrod" in text:
                sandbox.write(rel, text.replace("passwrod", "password"))
                return "Deterministic copy fix in sandbox."
        return "No copy issue found in sandbox."

    hours = _requested_hours(task_l)
    if hours is not None and "session.py" in files:
        text = sandbox.read("session.py")
        updated = re.sub(r"SESSION_TTL_HOURS\s*=\s*\d+", f"SESSION_TTL_HOURS = {hours}", text)
        sandbox.write("session.py", updated)
        return f"Deterministic sandbox edit: SESSION_TTL_HOURS = {hours}."

    # BYO GitHub clones: leave a visible candidate note in the worktree only.
    if sandbox.source_repo and not str(sandbox.source_repo).startswith("fixture:"):
        sandbox.write(
            "ENGRAM_CANDIDATE.md",
            (
                "# Engram candidate (worktree only)\n\n"
                f"Task: {task}\n\n"
                "No fixture-style deterministic edit matched. "
                "This note proves the clone worktree is writable. Nothing was merged or pushed.\n"
            ),
        )
        return "Wrote ENGRAM_CANDIDATE.md in the worktree (no merge)."
    return "No deterministic sandbox edit applied."


def _requested_hours(task_l: str) -> int | None:
    days = re.search(r"(\d+)\s*days", task_l)
    if days:
        return int(days.group(1)) * 24
    hours = re.search(r"(\d+)\s*hours", task_l)
    if hours:
        return int(hours.group(1))
    return None
