from __future__ import annotations

import re

import httpx

from engram.config import Settings
from engram.graph.store import open_graph_store
from engram.vector.store import EmbeddingClient, VectorStore

MAX_INGEST_LIMIT = 200


def parse_repo(repo: str) -> tuple[str, str]:
    cleaned = repo.strip().rstrip("/")
    cleaned = re.sub(r"^https?://github\.com/", "", cleaned)
    cleaned = cleaned.removesuffix(".git")
    parts = cleaned.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError("repo must look like owner/name")
    return parts[0], parts[1]


def _headers(token: str | None) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "engram"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _paginate(
    client: httpx.Client,
    url: str,
    headers: dict[str, str],
    *,
    limit: int,
    extra_params: dict | None = None,
) -> list[dict]:
    out: list[dict] = []
    page = 1
    per_page = min(100, max(1, limit))
    while len(out) < limit:
        params = {"per_page": per_page, "page": page, **(extra_params or {})}
        response = client.get(url, headers=headers, params=params)
        response.raise_for_status()
        batch = response.json()
        if not isinstance(batch, list) or not batch:
            break
        out.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return out[:limit]


def fetch_pull_requests(owner: str, name: str, token: str | None, limit: int = 50) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{name}/pulls"
    with httpx.Client(timeout=60.0) as client:
        return _paginate(
            client,
            url,
            _headers(token),
            limit=limit,
            extra_params={"state": "all"},
        )


def fetch_commits(owner: str, name: str, token: str | None, limit: int = 50) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{name}/commits"
    with httpx.Client(timeout=60.0) as client:
        return _paginate(client, url, _headers(token), limit=limit)


def pulls_to_artifacts(owner: str, name: str, service_id: str, raw: list[dict]) -> list[dict]:
    slug = f"{owner}-{name}".lower()
    artifacts = []
    for item in raw:
        number = item.get("number")
        if number is None:
            continue
        artifacts.append(
            {
                "id": f"gh-{slug}-{number}",
                "number": int(number),
                "title": item.get("title") or f"PR {number}",
                "status": (item.get("state") or "open").lower(),
                "summary": (item.get("body") or item.get("title") or "")[:400],
                "service_ids": [service_id],
                "kind": "pull_request",
            }
        )
    return artifacts


def commits_to_artifacts(owner: str, name: str, service_id: str, raw: list[dict]) -> list[dict]:
    slug = f"{owner}-{name}".lower()
    artifacts = []
    for item in raw:
        sha = str(item.get("sha") or "")
        if len(sha) < 7:
            continue
        message = ((item.get("commit") or {}).get("message") or sha).strip()
        title = message.splitlines()[0][:180]
        number = int(sha[:6], 16)
        artifacts.append(
            {
                "id": f"gh-{slug}-c-{sha[:10]}",
                "number": number,
                "title": title,
                "status": "merged",
                "summary": f"GitHub commit {sha[:12]}. {message[:360]}",
                "service_ids": [service_id],
                "kind": "commit",
                "sha": sha[:12],
            }
        )
    return artifacts


def ingest_github(
    settings: Settings,
    repo: str,
    service: str | None = None,
    limit: int = 50,
    token: str | None = None,
    pulls: list[dict] | None = None,
    commits: list[dict] | None = None,
    graph=None,
    vectors: VectorStore | None = None,
) -> dict:
    owner, name = parse_repo(repo)
    limit = max(1, min(int(limit), MAX_INGEST_LIMIT))
    auth = (token or settings.github_token or "").strip() or None
    service_name = service or name.replace("-", " ").title()
    service_id = f"svc-{re.sub(r'[^a-z0-9]+', '-', service_name.lower()).strip('-')}"
    live = pulls is None and commits is None
    raw_pulls = (
        pulls
        if pulls is not None
        else (fetch_pull_requests(owner, name, auth, limit) if live else [])
    )
    raw_commits = (
        commits
        if commits is not None
        else (fetch_commits(owner, name, auth, limit) if live else [])
    )
    # Prefer PRs; only keep commits when the repo has no PRs (or caller forced commits).
    if live and raw_pulls:
        raw_commits = []
    pr_artifacts = pulls_to_artifacts(owner, name, service_id, raw_pulls)
    commit_artifacts = commits_to_artifacts(owner, name, service_id, raw_commits)
    artifacts = pr_artifacts + commit_artifacts

    # Local Qdrant allows one open client per path — reuse the engine stores when provided.
    owns_stores = graph is None or vectors is None
    if owns_stores:
        graph = open_graph_store(settings)
        vectors = VectorStore(settings, EmbeddingClient(settings))
    try:
        graph.init_schema()
        vectors.ensure_collection()
        existing = graph.find_service(service_name) or graph.find_service(service_id)
        github_repo = f"{owner}/{name}"
        if existing:
            service_id = existing["id"]
            service_name = existing["name"]
            for item in artifacts:
                item["service_ids"] = [service_id]
            graph.upsert_service(
                {
                    "id": service_id,
                    "name": service_name,
                    "owner": existing.get("owner") or f"GitHub:{owner}",
                    "criticality": existing.get("criticality") or "medium",
                    "description": existing.get("description")
                    or f"Ingested from GitHub repository {github_repo}.",
                    "github_repo": github_repo,
                }
            )
        else:
            graph.upsert_service(
                {
                    "id": service_id,
                    "name": service_name,
                    "owner": f"GitHub:{owner}",
                    "criticality": "medium",
                    "description": f"Ingested from GitHub repository {github_repo}.",
                    "github_repo": github_repo,
                }
            )
            vectors.upsert_artifact(
                point_id=service_id,
                text=f"{service_name}. GitHub {github_repo}.",
                payload={
                    "artifact_type": "service",
                    "artifact_id": service_id,
                    "label": service_name,
                    "service_ids": [service_id],
                },
            )
        for item in artifacts:
            graph.upsert_pr(item)
            kind = item.get("kind") or "pull_request"
            label = f"COMMIT-{item.get('sha')}" if kind == "commit" else f"PR-{item['number']}"
            vectors.upsert_artifact(
                point_id=item["id"],
                text=f"{label} {item['title']}. {item['summary']}. Status: {item['status']}.",
                payload={
                    "artifact_type": "pull_request",
                    "artifact_id": item["id"],
                    "label": label,
                    "service_ids": item["service_ids"],
                },
            )
    finally:
        if owns_stores:
            graph.close()
            vectors.close()

    note = None
    if not pr_artifacts and commit_artifacts:
        note = "No pull requests on this repo; ingested recent commits instead."
    elif not artifacts:
        note = "No pull requests or commits returned. Check the repo name, visibility, and token."
    return {
        "repo": f"{owner}/{name}",
        "service": service_name,
        "service_id": service_id,
        "github_repo": f"{owner}/{name}",
        "pull_requests": len(pr_artifacts),
        "commits": len(commit_artifacts),
        "limit": limit,
        "store": settings.store,
        "embedding_backend": "openai" if vectors.uses_openai else "local-hash",
        "cleared": False,
        "note": note,
    }
