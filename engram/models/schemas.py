from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    MEDIUM_HIGH = "medium-high"
    HIGH = "high"


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    REVIEW = "review"
    BLOCK = "block"


class ArtifactType(str, Enum):
    SERVICE = "service"
    PULL_REQUEST = "pull_request"
    INCIDENT = "incident"
    ADR = "adr"


class Evidence(BaseModel):
    artifact_type: ArtifactType
    artifact_id: str
    label: str
    snippet: str
    source_uri: str | None = None
    relationship_path: list[str] = Field(default_factory=list)


class ServiceContext(BaseModel):
    id: str
    name: str
    owner: str
    criticality: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    github_repo: str | None = None


class PreflightRequest(BaseModel):
    service: str = Field(..., description="Service name or id, e.g. 'Auth Service'")
    task: str = Field(
        ...,
        description="Natural language description of proposed change",
        examples=["Increase auth session TTL from 24h to 7 days"],
    )
    proposed_pr_number: int | None = None
    mode: str = Field(
        default="adaptive",
        description="Retrieval mode: adaptive, hybrid, vector, graph, huge",
    )


class PreflightPacket(BaseModel):
    service: ServiceContext
    task: str
    risk_level: RiskLevel
    policy_outcome: PolicyOutcome
    summary: str
    reasoning: list[str]
    evidence: list[Evidence]
    related_incidents: list[dict[str, Any]]
    related_prs: list[dict[str, Any]]
    related_adrs: list[dict[str, Any]]
    manual_checks: list[str]
    confidence: str
    retrieval: dict[str, Any] = Field(default_factory=dict)


class QueryRequest(BaseModel):
    question: str
    service: str | None = None
    top_k: int = 8
    mode: str = "adaptive"


class QueryResponse(BaseModel):
    answer: str
    evidence: list[Evidence]
    retrieval: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    neo4j: bool
    qdrant: bool
    version: str


class AgentRunRequest(BaseModel):
    service: str = Field(..., description="Service name or id")
    task: str = Field(..., description="Natural language description of proposed change")
    mode: str = Field(default="adaptive", description="Context retrieval mode")
    repo: str | None = Field(
        default=None,
        description="Optional owner/name override for clone worktree (else service.github_repo)",
    )
    token: str | None = Field(
        default=None,
        description="Optional GitHub PAT for private clone only",
    )


class ManagerProposal(BaseModel):
    proposed_roles: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    rationale: str = ""


class CandidateChange(BaseModel):
    sandbox_id: str
    files_touched: list[str] = Field(default_factory=list)
    diff: str = ""
    notes: str = ""
    applied_to_origin: bool = False
    kind: str = "worktree"
    branch: str | None = None
    base_sha: str | None = None
    source_repo: str | None = None


class ReviewFinding(BaseModel):
    severity: str
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)


class ReviewReport(BaseModel):
    summary: str
    findings: list[ReviewFinding] = Field(default_factory=list)
    read_only: bool = True


class AgentRunResult(BaseModel):
    task: str
    service: str
    risk_level: RiskLevel
    gate: PolicyOutcome
    instantiated: list[str]
    manager_proposed_roles: list[str] = Field(default_factory=list)
    engram_required_roles: list[str] = Field(default_factory=list)
    manager_overridden: bool = False
    constraints: list[str] = Field(default_factory=list)
    manager: ManagerProposal | None = None
    candidate: CandidateChange | None = None
    review: ReviewReport | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    human_required: bool = False
    risk: dict = Field(default_factory=dict)
    outcome_id: str | None = None
    human_decision: str | None = None
    priors: list[dict] = Field(default_factory=list)


class ResolveRequest(BaseModel):
    decision: str = Field(..., description="approved or rejected")
    note: str = ""


class GitHubIngestRequest(BaseModel):
    repo: str = Field(..., description="owner/name or https://github.com/owner/name")
    service: str | None = Field(
        default=None,
        description="Service name to attach artifacts to (created if missing)",
    )
    limit: int = Field(default=50, ge=1, le=200, description="Max PRs (or commits) to ingest")
    token: str | None = Field(
        default=None,
        description="Optional GitHub PAT for this request only. Prefer env GITHUB_TOKEN for servers.",
    )
