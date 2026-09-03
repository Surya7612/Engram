from engram.routing.context import ContextRouter


def test_docs_task_stays_narrow():
    policy = ContextRouter().route("Fix a typo in the password-reset email copy")
    assert policy.task_class == "docs"
    assert policy.include_incidents is False
    assert policy.top_k <= 3


def test_ttl_task_pulls_incidents_and_adrs():
    policy = ContextRouter().route("Increase auth session TTL from 24 hours to 7 days")
    assert policy.task_class == "risk_sensitive"
    assert policy.include_incidents is True
    assert policy.include_adrs is True
    assert policy.expand_dependencies is True


def test_vector_mode_skips_graph():
    policy = ContextRouter().route("Increase auth session TTL from 24 hours to 7 days", mode="vector")
    assert policy.mode == "vector"
    assert policy.include_graph is False
    assert policy.include_vectors is True
    assert policy.expand_dependencies is False


def test_graph_mode_does_not_expand_deps():
    policy = ContextRouter().route("Increase auth session TTL from 24 hours to 7 days", mode="graph")
    assert policy.mode == "graph"
    assert policy.include_graph is True
    assert policy.expand_dependencies is False
