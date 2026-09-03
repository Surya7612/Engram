from engram.eval.groundedness import score_groundedness
from engram.models.schemas import ArtifactType, Evidence


def _ev(artifact_id: str, label: str) -> Evidence:
    return Evidence(
        artifact_type=ArtifactType.ADR,
        artifact_id=artifact_id,
        label=label,
        snippet="max TTL 48 hours",
    )


def test_supported_citations_are_grounded():
    evidence = [_ev("adr-12", "ADR-12"), _ev("inc-45", "INC-45")]
    scored = score_groundedness("ADR-12 caps TTL; INC-45 is related.", evidence)
    assert scored["unsupported"] == []
    assert scored["hallucination_risk"] == 0.0
    assert scored["supported_citation_rate"] == 1.0


def test_invented_artifact_is_hallucination_risk():
    evidence = [_ev("adr-12", "ADR-12")]
    scored = score_groundedness("ADR-99 says 7 days is fine.", evidence)
    assert "ADR-99" in scored["unsupported"]
    assert scored["hallucination_risk"] == 1.0
    assert scored["abstained"] is False


def test_abstaining_with_evidence_is_not_perfect_groundedness():
    evidence = [_ev("adr-12", "ADR-12")]
    scored = score_groundedness("I cannot determine the steps from the supplied artifacts.", evidence)
    assert scored["abstained"] is True
    assert scored["supported_citation_rate"] == 0.0
    assert scored["hallucination_risk"] == 0.0


def test_adr_label_matches_zero_padded_id():
    evidence = [_ev("adr-09", "ADR-9")]
    scored = score_groundedness("ADR-9 requires owner review.", evidence)
    assert scored["supported_ids"] == ["adr-09"]
    assert scored["unsupported"] == []
