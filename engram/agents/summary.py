from engram.models.schemas import AgentRunResult


def format_run(result: AgentRunResult) -> str:
    lines = [
        f"gate: {result.gate.value}"
        + ("  (human required)" if result.human_required else ""),
        f"org: {', '.join(result.instantiated) or 'none'}",
    ]
    if result.manager_overridden:
        proposed = ", ".join(result.manager_proposed_roles) or "none"
        lines.append(f"manager proposed: {proposed}  → Engram overrode")
    for prior in result.priors:
        note = (prior.get("human_note") or "").strip()
        line = f"prior: {prior.get('id')}  {prior.get('human_decision')}"
        if note:
            line += f"  {note}"
        lines.append(line)
    risk = result.risk or {}
    for violation in risk.get("violations") or []:
        lines.append(f"violation: {violation.get('detail')} ({violation.get('evidence_id')})")
    if result.review:
        highs = sum(1 for item in result.review.findings if item.severity == "high")
        lines.append(f"reviewer: {len(result.review.findings)} findings ({highs} high); read-only")
        for item in result.review.findings[:3]:
            evidence = ",".join(item.evidence_ids) or "unlinked"
            lines.append(f"  - [{item.severity}] {item.claim} [{evidence}]")
    if result.candidate:
        origin = "origin unchanged" if not result.candidate.applied_to_origin else "ORIGIN MUTATED"
        branch = result.candidate.branch or "n/a"
        lines.append(
            f"sandbox: {result.candidate.sandbox_id}  "
            f"{result.candidate.kind} {branch}  {origin}"
        )
        if result.candidate.source_repo:
            lines.append(f"source: {result.candidate.source_repo}")
        if result.candidate.diff.strip():
            lines.append(result.candidate.diff.rstrip())
    if result.outcome_id:
        decision = result.human_decision or "pending"
        lines.append(f"outcome: {result.outcome_id}  {decision}")
        if decision == "pending":
            lines.append("resolve: python main.py resolve --last --decision rejected")
    lines.append("nothing merged")
    return "\n".join(lines) + "\n"
