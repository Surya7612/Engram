from neo4j import GraphDatabase, Driver

from engram.config import Settings


def open_graph_store(settings: Settings):
    if settings.store == "local":
        from engram.graph.local import LocalGraphStore

        return LocalGraphStore(settings)
    return GraphStore(settings)


class GraphStore:
    def __init__(self, settings: Settings):
        self._driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    def ping(self) -> bool:
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def run(self, query: str, **params) -> list:
        with self._driver.session() as session:
            result = session.run(query, **params)
            return list(result)

    def init_schema(self) -> None:
        constraints = [
            "CREATE CONSTRAINT service_id IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE",
            "CREATE CONSTRAINT pr_id IF NOT EXISTS FOR (p:PullRequest) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE",
            "CREATE CONSTRAINT adr_id IF NOT EXISTS FOR (a:ADR) REQUIRE a.id IS UNIQUE",
        ]
        for stmt in constraints:
            self.run(stmt)

    def clear(self) -> None:
        self.run("MATCH (n) DETACH DELETE n")

    def upsert_service(self, svc: dict) -> None:
        self.run(
            """
            MERGE (s:Service {id: $id})
            SET s.name = $name,
                s.owner = $owner,
                s.criticality = $criticality,
                s.description = $description,
                s.github_repo = $github_repo
            """,
            id=svc["id"],
            name=svc["name"],
            owner=svc["owner"],
            criticality=svc["criticality"],
            description=svc["description"],
            github_repo=svc.get("github_repo"),
        )

    def upsert_pr(self, pr: dict) -> None:
        self.run(
            """
            MERGE (p:PullRequest {id: $id})
            SET p.number = $number,
                p.title = $title,
                p.status = $status,
                p.summary = $summary
            """,
            id=pr["id"],
            number=pr["number"],
            title=pr["title"],
            status=pr["status"],
            summary=pr["summary"],
        )
        for service_id in pr.get("service_ids", []):
            self.run(
                """
                MATCH (p:PullRequest {id: $pr_id}), (s:Service {id: $service_id})
                MERGE (p)-[:AFFECTS]->(s)
                """,
                pr_id=pr["id"],
                service_id=service_id,
            )

    def upsert_incident(self, inc: dict) -> None:
        self.run(
            """
            MERGE (i:Incident {id: $id})
            SET i.number = $number,
                i.title = $title,
                i.status = $status,
                i.summary = $summary
            """,
            id=inc["id"],
            number=inc["number"],
            title=inc["title"],
            status=inc["status"],
            summary=inc["summary"],
        )
        for service_id in inc.get("service_ids", []):
            self.run(
                """
                MATCH (i:Incident {id: $inc_id}), (s:Service {id: $service_id})
                MERGE (i)-[:AFFECTED]->(s)
                """,
                inc_id=inc["id"],
                service_id=service_id,
            )
        for pr_id in inc.get("related_pr_ids", []):
            self.run(
                """
                MATCH (i:Incident {id: $inc_id}), (p:PullRequest {id: $pr_id})
                MERGE (i)-[:RELATED_TO]->(p)
                """,
                inc_id=inc["id"],
                pr_id=pr_id,
            )

    def upsert_adr(self, adr: dict) -> None:
        self.run(
            """
            MERGE (a:ADR {id: $id})
            SET a.number = $number,
                a.title = $title,
                a.status = $status,
                a.content = $content
            """,
            id=adr["id"],
            number=adr["number"],
            title=adr["title"],
            status=adr["status"],
            content=adr["content"],
        )
        for service_id in adr.get("service_ids", []):
            self.run(
                """
                MATCH (a:ADR {id: $adr_id}), (s:Service {id: $service_id})
                MERGE (a)-[:GOVERNS]->(s)
                """,
                adr_id=adr["id"],
                service_id=service_id,
            )

    def link_dependency(self, from_id: str, to_id: str) -> None:
        self.run(
            """
            MATCH (a:Service {id: $from_id}), (b:Service {id: $to_id})
            MERGE (a)-[:DEPENDS_ON]->(b)
            """,
            from_id=from_id,
            to_id=to_id,
        )

    def find_service(self, name_or_id: str) -> dict | None:
        records = self.run(
            """
            MATCH (s:Service)
            WHERE toLower(s.id) = toLower($q)
               OR toLower(s.name) = toLower($q)
               OR toLower(s.name) CONTAINS toLower($q)
            RETURN s { .* } AS service
            LIMIT 1
            """,
            q=name_or_id,
        )
        return records[0]["service"] if records else None

    def service_neighborhood(self, service_id: str) -> dict:
        records = self.run(
            """
            MATCH (s:Service {id: $service_id})
            OPTIONAL MATCH (s)-[:DEPENDS_ON]->(dep:Service)
            OPTIONAL MATCH (depender:Service)-[:DEPENDS_ON]->(s)
            OPTIONAL MATCH (p:PullRequest)-[:AFFECTS]->(s)
            OPTIONAL MATCH (i:Incident)-[:AFFECTED]->(s)
            OPTIONAL MATCH (a:ADR)-[:GOVERNS]->(s)
            OPTIONAL MATCH (i2:Incident)-[:RELATED_TO]->(p)
            RETURN s { .* } AS service,
                   collect(DISTINCT dep.id) AS dependency_ids,
                   collect(DISTINCT dep.name) AS dependencies,
                   collect(DISTINCT depender.name) AS dependents,
                   collect(DISTINCT p { .id, .number, .title, .status, .summary }) AS pull_requests,
                   collect(DISTINCT i { .id, .number, .title, .status, .summary }) AS incidents,
                   collect(DISTINCT a { .id, .number, .title, .status, .content }) AS adrs
            """,
            service_id=service_id,
        )
        if not records:
            return {}
        row = dict(records[0])
        row["dependency_ids"] = [x for x in (row.get("dependency_ids") or []) if x]
        row["dependencies"] = [x for x in (row.get("dependencies") or []) if x]
        row["dependents"] = [x for x in (row.get("dependents") or []) if x]
        row["pull_requests"] = [x for x in (row.get("pull_requests") or []) if x and x.get("id")]
        row["incidents"] = [x for x in (row.get("incidents") or []) if x and x.get("id")]
        row["adrs"] = [x for x in (row.get("adrs") or []) if x and x.get("id")]
        return row

    def relationship_paths(self, service_id: str, limit: int = 5) -> list[list[str]]:
        records = self.run(
            """
            MATCH (s:Service {id: $service_id})
            OPTIONAL MATCH path = (s)<-[:AFFECTS]-(p:PullRequest)<-[:RELATED_TO]-(i:Incident)
            RETURN [n IN nodes(path) | coalesce(n.name, n.title, n.id)] AS path_nodes
            LIMIT $limit
            """,
            service_id=service_id,
            limit=limit,
        )
        paths = []
        for rec in records:
            raw = rec["path_nodes"] or []
            nodes = [n for n in raw if n]
            if nodes:
                paths.append(nodes)
        return paths
