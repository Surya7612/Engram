from engram.models.schemas import PolicyOutcome
from engram.routing.risk import BlastRadius, organization_roles

KNOWN_ROLES = ("manager", "backend", "reviewer")


def required_roles(
    policy: PolicyOutcome,
    task_class: str,
    blast: BlastRadius | None = None,
) -> list[str]:
    """Minimum agent organization justified by risk. Not a learned router (that's V3)."""
    return organization_roles(policy, task_class, blast)


def constrain_roles(proposed: list[str], required: list[str]) -> tuple[list[str], list[str], list[str], bool]:
    """Engram required roles win. Manager may propose backend/reviewer; it cannot drop required review."""
    exec_required = [role for role in required if role != "manager"]
    exec_proposed = [role for role in proposed if role in {"backend", "reviewer"}]
    final = [role for role in KNOWN_ROLES if role in required]
    added = [role for role in exec_required if role not in exec_proposed]
    dropped = [role for role in exec_proposed if role not in exec_required]
    overridden = bool(added or dropped)
    return final, added, dropped, overridden
