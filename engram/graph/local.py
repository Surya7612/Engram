import json
from copy import deepcopy
from pathlib import Path

from engram.config import Settings


def _empty() -> dict:
    return {
        "services": {},
        "pull_requests": {},
        "incidents": {},
        "adrs": {},
        "depends_on": [],
        "pr_affects": [],
        "incident_affected": [],
        "incident_related_pr": [],
        "adr_governs": [],
    }


class LocalGraphStore:
    """File-backed context graph for running V1 without Neo4j/Docker."""

    def __init__(self, settings: Settings):
        self._path = settings.local_data_dir / "graph.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            return json.loads(self._path.read_text(encoding="utf-8"))
        return _empty()

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def close(self) -> None:
        return

    def ping(self) -> bool:
        return True

    def init_schema(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._data = _empty()
            self._save()

    def clear(self) -> None:
        self._data = _empty()
        self._save()

    def upsert_service(self, svc: dict) -> None:
        self._data["services"][svc["id"]] = {
            "id": svc["id"],
            "name": svc["name"],
            "owner": svc["owner"],
            "criticality": svc["criticality"],
            "description": svc["description"],
            "github_repo": svc.get("github_repo"),
        }
        self._save()

    def upsert_pr(self, pr: dict) -> None:
        self._data["pull_requests"][pr["id"]] = {
            "id": pr["id"],
            "number": pr["number"],
            "title": pr["title"],
            "status": pr["status"],
            "summary": pr["summary"],
        }
        self._data["pr_affects"] = [
            edge for edge in self._data["pr_affects"] if edge[0] != pr["id"]
        ]
        for service_id in pr.get("service_ids", []):
            self._data["pr_affects"].append([pr["id"], service_id])
        self._save()

    def upsert_incident(self, inc: dict) -> None:
        self._data["incidents"][inc["id"]] = {
            "id": inc["id"],
            "number": inc["number"],
            "title": inc["title"],
            "status": inc["status"],
            "summary": inc["summary"],
        }
        self._data["incident_affected"] = [
            edge for edge in self._data["incident_affected"] if edge[0] != inc["id"]
        ]
        for service_id in inc.get("service_ids", []):
            self._data["incident_affected"].append([inc["id"], service_id])
        self._data["incident_related_pr"] = [
            edge for edge in self._data["incident_related_pr"] if edge[0] != inc["id"]
        ]
        for pr_id in inc.get("related_pr_ids", []):
            self._data["incident_related_pr"].append([inc["id"], pr_id])
        self._save()

    def upsert_adr(self, adr: dict) -> None:
        self._data["adrs"][adr["id"]] = {
            "id": adr["id"],
            "number": adr["number"],
            "title": adr["title"],
            "status": adr["status"],
            "content": adr["content"],
        }
        self._data["adr_governs"] = [
            edge for edge in self._data["adr_governs"] if edge[0] != adr["id"]
        ]
        for service_id in adr.get("service_ids", []):
            self._data["adr_governs"].append([adr["id"], service_id])
        self._save()

    def link_dependency(self, from_id: str, to_id: str) -> None:
        edge = [from_id, to_id]
        if edge not in self._data["depends_on"]:
            self._data["depends_on"].append(edge)
        self._save()

    def find_service(self, name_or_id: str) -> dict | None:
        q = name_or_id.lower()
        for svc in self._data["services"].values():
            if svc["id"].lower() == q or svc["name"].lower() == q:
                return deepcopy(svc)
        for svc in self._data["services"].values():
            if q in svc["name"].lower():
                return deepcopy(svc)
        return None

    def service_neighborhood(self, service_id: str) -> dict:
        service = self._data["services"].get(service_id)
        if not service:
            return {}

        dependency_ids = [
            to_id
            for from_id, to_id in self._data["depends_on"]
            if from_id == service_id and to_id in self._data["services"]
        ]
        dependencies = [
            self._data["services"][to_id]["name"]
            for to_id in dependency_ids
        ]
        dependents = [
            self._data["services"][from_id]["name"]
            for from_id, to_id in self._data["depends_on"]
            if to_id == service_id and from_id in self._data["services"]
        ]
        pull_requests = [
            deepcopy(self._data["pull_requests"][pr_id])
            for pr_id, sid in self._data["pr_affects"]
            if sid == service_id and pr_id in self._data["pull_requests"]
        ]
        incidents = [
            deepcopy(self._data["incidents"][inc_id])
            for inc_id, sid in self._data["incident_affected"]
            if sid == service_id and inc_id in self._data["incidents"]
        ]
        adrs = [
            deepcopy(self._data["adrs"][adr_id])
            for adr_id, sid in self._data["adr_governs"]
            if sid == service_id and adr_id in self._data["adrs"]
        ]

        return {
            "service": deepcopy(service),
            "dependency_ids": dependency_ids,
            "dependencies": dependencies,
            "dependents": dependents,
            "pull_requests": pull_requests,
            "incidents": incidents,
            "adrs": adrs,
        }

    def relationship_paths(self, service_id: str, limit: int = 5) -> list[list[str]]:
        service = self._data["services"].get(service_id)
        if not service:
            return []
        paths: list[list[str]] = []
        pr_ids = [pr_id for pr_id, sid in self._data["pr_affects"] if sid == service_id]
        for pr_id in pr_ids:
            pr = self._data["pull_requests"].get(pr_id)
            if not pr:
                continue
            related = [
                inc_id
                for inc_id, related_pr in self._data["incident_related_pr"]
                if related_pr == pr_id
            ]
            for inc_id in related:
                inc = self._data["incidents"].get(inc_id)
                if not inc:
                    continue
                paths.append([service["name"], f"PR-{pr['number']}", f"INC-{inc['number']}"])
                if len(paths) >= limit:
                    return paths
        return paths
