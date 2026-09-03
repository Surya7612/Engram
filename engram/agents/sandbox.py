from __future__ import annotations

import difflib
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path


SERVICE_FIXTURES = {
    "svc-auth": "auth-service",
    "svc-email": "email-service",
}

_SKIP_DIR_NAMES = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
    "target",
    "vendor",
}
_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".rs",
    ".go",
    ".rb",
    ".java",
    ".kt",
    ".swift",
    ".css",
    ".html",
    ".sh",
    ".env.example",
}


class Sandbox:
    """Git worktree over a fixture or cloned GitHub repo. Never merges back to main."""

    def __init__(
        self,
        origin: Path,
        root: Path,
        sandbox_id: str,
        *,
        branch: str | None = None,
        base_sha: str | None = None,
        kind: str = "worktree",
        source_repo: str | None = None,
    ):
        self.origin = origin
        self.root = root
        self.sandbox_id = sandbox_id
        self.branch = branch
        self.base_sha = base_sha
        self.kind = kind
        self.source_repo = source_repo

    @classmethod
    def create(
        cls,
        data_dir: Path,
        local_data_dir: Path,
        service_id: str,
        *,
        github_repo: str | None = None,
        token: str | None = None,
    ) -> Sandbox:
        if github_repo:
            slug = _repo_slug(github_repo)
            repo = _ensure_github_clone(local_data_dir / "clones" / slug, github_repo, token)
            source_repo = _normalize_repo(github_repo)
        else:
            fixture_name = SERVICE_FIXTURES.get(service_id)
            if not fixture_name:
                raise ValueError(
                    f"No sandbox fixture for {service_id}. "
                    "Ingest a GitHub repo first, or pass repo=owner/name."
                )
            fixture = data_dir / "sandbox" / fixture_name
            if not fixture.exists():
                raise ValueError(f"Sandbox fixture missing: {fixture}")
            repo = _ensure_fixture_repo(local_data_dir / "repos" / fixture_name, fixture)
            source_repo = f"fixture:{fixture_name}"

        base_sha = _git(repo, "rev-parse", "HEAD").strip()
        sandbox_id = uuid.uuid4().hex[:10]
        branch = f"engram/{sandbox_id}"
        root = local_data_dir / "sandboxes" / sandbox_id
        root.parent.mkdir(parents=True, exist_ok=True)
        _git(repo, "worktree", "add", "-b", branch, str(root), base_sha)
        return cls(
            origin=repo,
            root=root,
            sandbox_id=sandbox_id,
            branch=branch,
            base_sha=base_sha,
            kind="worktree",
            source_repo=source_repo,
        )

    def _safe(self, rel: str) -> Path:
        if Path(rel).is_absolute():
            raise PermissionError("absolute paths are not allowed in the sandbox")
        if ".git" in Path(rel).parts:
            raise PermissionError("cannot mutate .git inside the sandbox")
        root = self.root.resolve()
        path = (root / rel).resolve()
        if not path.is_relative_to(root):
            raise PermissionError("sandbox escape blocked")
        return path

    def list_files(self, limit: int | None = None) -> list[str]:
        files = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or _skip(path):
                continue
            if limit is not None and not _looks_texty(path):
                continue
            files.append(str(path.relative_to(self.root)))
            if limit is not None and len(files) >= limit:
                break
        return files

    def read(self, rel: str) -> str:
        return self._safe(rel).read_text(encoding="utf-8")

    def write(self, rel: str, content: str) -> None:
        path = self._safe(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def unified_diff(self) -> str:
        if self.kind == "worktree" and self.base_sha:
            chunks = [_git(self.root, "diff", self.base_sha, "--")]
            for rel in _untracked_files(self.root):
                after = _read_text(self.root / rel)
                chunks.append(
                    "".join(
                        difflib.unified_diff(
                            [],
                            after.splitlines(keepends=True),
                            fromfile=f"a/{rel}",
                            tofile=f"b/{rel}",
                        )
                    )
                )
            return "".join(chunks)
        chunks: list[str] = []
        origin_files = _rel_files(self.origin)
        root_files = _rel_files(self.root)
        for rel in sorted(origin_files | root_files):
            before = _read_text(self.origin / rel)
            after = _read_text(self.root / rel)
            if before == after:
                continue
            chunks.append(
                "".join(
                    difflib.unified_diff(
                        before.splitlines(keepends=True),
                        after.splitlines(keepends=True),
                        fromfile=f"a/{rel}",
                        tofile=f"b/{rel}",
                    )
                )
            )
        return "".join(chunks)

    def files_touched(self) -> list[str]:
        if self.kind == "worktree" and self.base_sha:
            named = {
                line
                for line in _git(self.root, "diff", "--name-only", self.base_sha, "--").splitlines()
                if line.strip()
            }
            named.update(_untracked_files(self.root))
            return sorted(named)
        touched = []
        origin_files = _rel_files(self.origin)
        root_files = _rel_files(self.root)
        for rel in sorted(origin_files | root_files):
            if _read_text(self.origin / rel) != _read_text(self.root / rel):
                touched.append(rel)
        return touched

    def main_unchanged(self) -> bool:
        """True when the origin repo checkout still matches base_sha and is clean."""
        if self.kind != "worktree" or not self.base_sha:
            return True
        head = _git(self.origin, "rev-parse", "HEAD").strip()
        if head != self.base_sha:
            return False
        dirty = _git(self.origin, "status", "--porcelain")
        return dirty.strip() == ""


class ReadOnlySandbox:
    def __init__(self, sandbox: Sandbox):
        self._sandbox = sandbox

    def list_files(self, limit: int | None = None) -> list[str]:
        return self._sandbox.list_files(limit=limit)

    def read(self, rel: str) -> str:
        return self._sandbox.read(rel)

    def unified_diff(self) -> str:
        return self._sandbox.unified_diff()

    def write(self, rel: str, content: str) -> None:
        raise PermissionError("Reviewer is read-only")


def _normalize_repo(repo: str) -> str:
    cleaned = repo.strip().rstrip("/")
    cleaned = re.sub(r"^https?://github\.com/", "", cleaned)
    cleaned = cleaned.removesuffix(".git")
    parts = cleaned.split("/")
    if len(parts) < 2:
        raise ValueError("repo must look like owner/name")
    return f"{parts[0]}/{parts[1]}"


def _repo_slug(repo: str) -> str:
    owner, name = _normalize_repo(repo).split("/", 1)
    raw = f"{owner}-{name}".lower()
    return re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-")


def _clone_url(repo: str, token: str | None) -> str:
    owner_name = _normalize_repo(repo)
    if token:
        return f"https://x-access-token:{token}@github.com/{owner_name}.git"
    return f"https://github.com/{owner_name}.git"


def _ensure_github_clone(dest: Path, repo: str, token: str | None) -> Path:
    """Shallow-clone owner/name into dest if missing. Reuses existing clone offline."""
    if (dest / ".git").exists():
        return dest
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = _clone_url(repo, token)
    result = subprocess.run(
        ["git", "clone", "--depth", "1", url, str(dest)],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        # Avoid leaking token in errors
        detail = detail.replace(token or "", "***") if token else detail
        raise RuntimeError(f"git clone failed for { _normalize_repo(repo) }: {detail}")
    _git(dest, "config", "user.email", "engram@local")
    _git(dest, "config", "user.name", "Engram")
    return dest


def _ensure_fixture_repo(repo: Path, fixture: Path) -> Path:
    """Create a local git repo from the sample fixture if needed. Returns repo path."""
    if (repo / ".git").exists():
        return repo
    if repo.exists():
        shutil.rmtree(repo)
    repo.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture, repo, ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store"))
    template = repo.parent / ".git-template-empty"
    template.mkdir(exist_ok=True)
    _git(repo, "init", f"--template={template}")
    _git(repo, "config", "user.email", "engram@local")
    _git(repo, "config", "user.name", "Engram")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "engram fixture baseline")
    _git(repo, "branch", "-M", "main")
    return repo


def _git(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")
    return result.stdout


def _skip(path: Path) -> bool:
    return any(part in _SKIP_DIR_NAMES for part in path.parts) or path.name in {".DS_Store"}


def _looks_texty(path: Path) -> bool:
    if path.suffix.lower() in _TEXT_SUFFIXES:
        return True
    name = path.name.lower()
    return name in {"readme", "license", "makefile", "dockerfile"}


def _untracked_files(root: Path) -> list[str]:
    out = []
    for line in _git(root, "status", "--porcelain", "-u").splitlines():
        if line.startswith("?? "):
            path = line[3:].strip()
            if path and not _skip(root / path):
                out.append(path)
    return out


def _rel_files(root: Path) -> set[str]:
    if not root.exists():
        return set()
    out = set()
    for path in root.rglob("*"):
        if path.is_file() and not _skip(path):
            out.add(str(path.relative_to(root)))
    return out


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""
