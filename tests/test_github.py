import httpx

from engram.config import Settings
from engram.graph.local import LocalGraphStore
from engram.ingestion.github import _paginate, ingest_github, parse_repo, pulls_to_artifacts


def test_parse_repo():
    assert parse_repo("Surya7612/Engram") == ("Surya7612", "Engram")
    assert parse_repo("https://github.com/Surya7612/Engram.git") == ("Surya7612", "Engram")


def test_paginate_walks_pages_until_limit():
    pages = {
        1: [{"n": i} for i in range(100)],
        2: [{"n": i} for i in range(100, 150)],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json=pages.get(page, []))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        out = _paginate(client, "https://example.test/items", {}, limit=120)
    assert len(out) == 120
    assert out[0]["n"] == 0
    assert out[-1]["n"] == 119


def test_ingest_github_pulls_without_network(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    raw = [
        {
            "number": 7,
            "title": "Add context router",
            "state": "closed",
            "body": "V1.5 routing",
        }
    ]
    result = ingest_github(settings, repo="Surya7612/Engram", pulls=raw)
    assert result["pull_requests"] == 1
    assert result["commits"] == 0
    assert result["cleared"] is False
    assert result["github_repo"] == "Surya7612/Engram"
    graph = LocalGraphStore(settings)
    found = graph.find_service("Engram")
    assert found is not None
    assert found.get("github_repo") == "Surya7612/Engram"
    neighborhood = graph.service_neighborhood(found["id"])
    ids = [pr["id"] for pr in neighborhood["pull_requests"]]
    assert "gh-surya7612-engram-7" in ids


def test_pulls_to_artifacts_stable_ids():
    artifacts = pulls_to_artifacts(
        "Surya7612",
        "Engram",
        "svc-engram",
        [{"number": 1, "title": "Init", "state": "open", "body": ""}],
    )
    assert artifacts[0]["id"] == "gh-surya7612-engram-1"
    assert artifacts[0]["service_ids"] == ["svc-engram"]


def test_ingest_commits_when_repo_has_no_prs(tmp_path):
    settings = Settings(
        store="local",
        local_data_dir=tmp_path,
        openai_api_key="",
        langchain_tracing_v2=False,
        langchain_api_key="",
    )
    commits = [
        {
            "sha": "abcdef1234567890",
            "commit": {"message": "Add risk router\n\nV2.5 rules"},
        }
    ]
    result = ingest_github(settings, repo="Surya7612/Engram", pulls=[], commits=commits)
    assert result["pull_requests"] == 0
    assert result["commits"] == 1
    assert result["note"]
    graph = LocalGraphStore(settings)
    neighborhood = graph.service_neighborhood("svc-engram")
    ids = [pr["id"] for pr in neighborhood["pull_requests"]]
    assert "gh-surya7612-engram-c-abcdef1234" in ids
