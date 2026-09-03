import shutil

import pytest

from engram.agents.org import constrain_roles, required_roles
from engram.agents.sandbox import ReadOnlySandbox, Sandbox
from engram.config import Settings
from engram.engine import EngramEngine
from engram.ingestion.seed import seed_from_sample
from engram.models.schemas import AgentRunRequest, PolicyOutcome


def test_docs_org_is_backend_only():
    assert required_roles(PolicyOutcome.ALLOW, "docs") == ["backend"]


def test_review_org_includes_independent_reviewer():
    roles = required_roles(PolicyOutcome.REVIEW, "risk_sensitive")
    assert roles == ["manager", "backend", "reviewer"]


def test_manager_cannot_drop_reviewer():
    final, added, dropped, overridden = constrain_roles(
        ["backend"],
        ["manager", "backend", "reviewer"],
    )
    assert final == ["manager", "backend", "reviewer"]
    assert added == ["reviewer"]
    assert dropped == []
    assert overridden is True


def test_sandbox_rejects_escape(tmp_path):
    origin = tmp_path / "origin"
    origin.mkdir()
    (origin / "ok.py").write_text("x = 1\n", encoding="utf-8")
    root = tmp_path / "copy"
    shutil.copytree(origin, root)
    box = Sandbox(origin=origin, root=root, sandbox_id="t", kind="copy")
    with pytest.raises(PermissionError):
        box.write("../evil.py", "nope")
    with pytest.raises(PermissionError):
        box.write(".git/config", "nope")
    with pytest.raises(PermissionError):
        ReadOnlySandbox(box).write("ok.py", "mutated")
    assert (origin / "ok.py").read_text(encoding="utf-8") == "x = 1\n"


def test_sandbox_create_uses_git_worktree(tmp_path):
    data = tmp_path / "data"
    fixture = data / "sandbox" / "auth-service"
    fixture.mkdir(parents=True)
    (fixture / "session.py").write_text("SESSION_TTL_HOURS = 24\n", encoding="utf-8")
    local = tmp_path / "local"
    box = Sandbox.create(data, local, "svc-auth")
    assert box.kind == "worktree"
    assert box.branch and box.branch.startswith("engram/")
    assert box.base_sha
    assert box.source_repo == "fixture:auth-service"
    assert (box.root / ".git").exists() or (box.root / ".git").is_file()
    before_main = (box.origin / "session.py").read_text(encoding="utf-8")
    box.write("session.py", "SESSION_TTL_HOURS = 168\n")
    assert "SESSION_TTL_HOURS = 168" in box.unified_diff()
    assert box.files_touched() == ["session.py"]
    assert (box.origin / "session.py").read_text(encoding="utf-8") == before_main
    assert box.main_unchanged() is True
    assert (fixture / "session.py").read_text(encoding="utf-8") == "SESSION_TTL_HOURS = 24\n"


def test_sandbox_from_existing_github_clone(tmp_path):
    """Offline: reuse a pre-built clone directory as if git clone already ran."""
    import subprocess

    clone = tmp_path / "clones" / "acme-demo"
    clone.mkdir(parents=True)
    (clone / "README.md").write_text("hello\n", encoding="utf-8")
    template = tmp_path / "clones" / ".git-template-empty"
    template.mkdir(exist_ok=True)
    subprocess.run(["git", "init", f"--template={template}"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "engram@local"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Engram"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=clone, check=True, capture_output=True)
    subprocess.run(["git", "branch", "-M", "main"], cwd=clone, check=True, capture_output=True)

    box = Sandbox.create(
        tmp_path / "data",
        tmp_path,
        "svc-acme-demo",
        github_repo="acme/demo",
    )
    assert box.source_repo == "acme/demo"
    box.write("ENGRAM_CANDIDATE.md", "note\n")
    assert "ENGRAM_CANDIDATE.md" in box.files_touched()
    assert box.main_unchanged() is True
    assert (clone / "README.md").read_text(encoding="utf-8") == "hello\n"


def test_ttl_run_overrides_manager_and_keeps_origin(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    seed_from_sample(settings)
    origin = settings.data_dir / "sandbox" / "auth-service" / "session.py"
    before = origin.read_text(encoding="utf-8")
    engine = EngramEngine(settings)
    try:
        result = engine.run_agents(
            AgentRunRequest(
                service="Auth Service",
                task="Increase auth session TTL from 24 hours to 7 days",
            )
        )
    finally:
        engine.close()

    assert origin.read_text(encoding="utf-8") == before
    assert result.candidate is not None
    assert result.candidate.applied_to_origin is False
    assert result.candidate.kind == "worktree"
    assert result.candidate.branch and result.candidate.branch.startswith("engram/")
    assert result.candidate.base_sha
    assert result.candidate.source_repo == "fixture:auth-service"
    repo_main = tmp_path / "repos" / "auth-service" / "session.py"
    assert repo_main.read_text(encoding="utf-8") == before
    assert "reviewer" in result.instantiated
    assert result.manager_overridden is True
    assert result.gate.value == "block"
    assert result.human_required is True
    assert result.risk.get("violations")
    assert result.review is not None
    evidence_ids = [eid for finding in result.review.findings for eid in finding.evidence_ids]
    assert "adr-12" in evidence_ids
    assert "SESSION_TTL_HOURS = 168" in result.candidate.diff
    assert result.outcome_id
    assert result.human_decision == "pending"
    assert [item["evidence_id"] for item in (result.risk or {}).get("violations") or []] == ["adr-12"]


def test_docs_run_skips_reviewer(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    seed_from_sample(settings)
    origin = settings.data_dir / "sandbox" / "email-service" / "reset_email.txt"
    before = origin.read_text(encoding="utf-8")
    engine = EngramEngine(settings)
    try:
        result = engine.run_agents(
            AgentRunRequest(
                service="Email Service",
                task="Fix a typo in the password-reset email copy",
            )
        )
    finally:
        engine.close()

    assert origin.read_text(encoding="utf-8") == before
    assert result.instantiated == ["backend"]
    assert result.review is None
    assert result.manager is None
    assert result.gate.value == "allow"
    assert result.human_required is False
    assert result.candidate is not None
    assert result.candidate.kind == "worktree"
    assert "password" in result.candidate.diff
    repo_main = tmp_path / "repos" / "email-service" / "reset_email.txt"
    assert "passwrod" in repo_main.read_text(encoding="utf-8")
