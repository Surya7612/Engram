import uuid


def artifact_point_id(artifact_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"engram:{artifact_id}"))
