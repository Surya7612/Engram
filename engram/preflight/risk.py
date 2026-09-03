from engram.models.schemas import PolicyOutcome, RiskLevel


TTL_KEYWORDS = {"ttl", "session", "token", "expiry", "expiration", "cache", "redis", "invalidation"}
AUTH_KEYWORDS = {"auth", "authentication", "login", "session"}


def assess_risk(task: str, service: dict, neighborhood: dict) -> tuple[RiskLevel, PolicyOutcome, list[str], list[str]]:
    reasoning: list[str] = []
    manual_checks: list[str] = []
    task_lower = task.lower()

    score = 0
    criticality = (service.get("criticality") or "medium").lower()
    if criticality == "high":
        score += 2
        reasoning.append(f"{service['name']} is marked high criticality.")

    incidents = [i for i in (neighborhood.get("incidents") or []) if i.get("id")]
    open_incidents = [
        i for i in incidents if (i.get("status") or "").lower() in {"investigating", "open", "active"}
    ]
    if open_incidents:
        score += 2
        labels = ", ".join(f"INC-{i['number']}" for i in open_incidents)
        reasoning.append(f"Open or investigating incidents on this path: {labels}.")

    if len(incidents) >= 2:
        score += 1
        reasoning.append("Multiple historical incidents are linked to this service.")

    adrs = [a for a in (neighborhood.get("adrs") or []) if a.get("id")]
    ttl_adr = next((a for a in adrs if "ttl" in (a.get("title") or "").lower()), None)
    if ttl_adr and any(k in task_lower for k in TTL_KEYWORDS):
        score += 2
        reasoning.append(
            f"Task touches TTL/session/cache behavior and ADR-{ttl_adr['number']} governs Redis TTL constraints."
        )
        manual_checks.append("Validate TTL parity and cache invalidation behavior against ADR-12.")

    if any(k in task_lower for k in AUTH_KEYWORDS) and criticality == "high":
        score += 1
        reasoning.append("Auth-sensitive change on a high-criticality authentication path.")
        manual_checks.append("Confirm Platform Team owner review for auth policy changes.")

    deps = neighborhood.get("dependencies") or []
    if deps:
        reasoning.append(f"Downstream dependencies in blast radius: {', '.join(deps)}.")

    if score >= 5:
        risk = RiskLevel.MEDIUM_HIGH
        policy = PolicyOutcome.REVIEW
    elif score >= 3:
        risk = RiskLevel.MEDIUM
        policy = PolicyOutcome.REVIEW if criticality == "high" else PolicyOutcome.WARN
    elif score >= 1:
        risk = RiskLevel.MEDIUM
        policy = PolicyOutcome.WARN
    else:
        risk = RiskLevel.LOW
        policy = PolicyOutcome.ALLOW

    if not manual_checks and policy in {PolicyOutcome.REVIEW, PolicyOutcome.WARN}:
        manual_checks.append("Confirm owner availability and run targeted integration tests before merge.")

    return risk, policy, reasoning, manual_checks


def build_summary(
    service: dict,
    risk: RiskLevel,
    policy: PolicyOutcome,
    reasoning: list[str],
) -> str:
    lead = reasoning[0] if reasoning else f"Review context for {service['name']} before proceeding."
    return (
        f"Preflight for {service['name']}: risk {risk.value}, policy {policy.value}. "
        f"{lead}"
    )
