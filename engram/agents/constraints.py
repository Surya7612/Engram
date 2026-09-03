from engram.models.schemas import PreflightPacket


def constraints_from_priors(priors: list[dict]) -> list[str]:
    lines = []
    for prior in priors:
        decision = prior.get("human_decision") or "unknown"
        note = (prior.get("human_note") or "").strip()
        line = f"Prior outcome {prior.get('id')}: human {decision}"
        if note:
            line += f" — {note}"
        line += ". Recorded decision only; not a learned routing policy and not a merge."
        lines.append(line)
    return lines


def constraints_from_packet(packet: PreflightPacket) -> list[str]:
    lines = [
        f"Engram policy {packet.policy_outcome.value} is not negotiable by the manager.",
        f"Owner: {packet.service.owner}. Criticality: {packet.service.criticality}. Risk: {packet.risk_level.value}.",
    ]
    for adr in packet.related_adrs:
        number = adr.get("number")
        title = adr.get("title") or ""
        content = (adr.get("content") or "")[:220]
        lines.append(f"ADR-{number} ({adr.get('id')}): {title}. {content}")
    for inc in (packet.related_incidents or [])[:6]:
        lines.append(f"INC-{inc.get('number')} ({inc.get('id')}): {inc.get('title')}. {inc.get('summary') or ''}")
    lines.extend(packet.manual_checks)
    return [line for line in lines if line.strip()]
