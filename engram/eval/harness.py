import json
from pathlib import Path

from engram.config import Settings
from engram.engine import EngramEngine
from engram.eval.groundedness import answer_from_evidence, score_groundedness

MODES = ["vector", "graph", "hybrid", "huge", "adaptive"]


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ids(evidence) -> set[str]:
    return {item.artifact_id for item in evidence}


def score_case(retrieved_ids: set[str], case: dict, token_estimate: int, evidence_count: int) -> dict:
    required = set(case.get("required_ids") or [])
    waste = set(case.get("waste_ids") or [])
    hit_required = retrieved_ids & required
    waste_hits = retrieved_ids & waste
    recall = (len(hit_required) / len(required)) if required else 1.0
    return {
        "required_recall": round(recall, 3),
        "required_hits": sorted(hit_required),
        "required_misses": sorted(required - retrieved_ids),
        "waste_hits": sorted(waste_hits),
        "waste_count": len(waste_hits),
        "evidence_count": evidence_count,
        "token_estimate": token_estimate,
    }


def run_eval(settings: Settings) -> dict:
    cases_path = settings.data_dir.parent / "evals" / "v1.5_cases.json"
    cases = load_cases(cases_path)
    engine = EngramEngine(settings)
    try:
        rows = []
        totals: dict[str, list[float]] = {mode: [] for mode in MODES}
        waste_totals: dict[str, list[int]] = {mode: [] for mode in MODES}
        token_totals: dict[str, list[int]] = {mode: [] for mode in MODES}

        grounded_scores: list[float] = []
        hallucination_scores: list[float] = []
        abstention_flags: list[int] = []
        answer_source = "evidence_list"

        for case in cases:
            case_result = {"id": case["id"], "task": case["task"], "service": case["service"], "modes": {}}
            for mode in MODES:
                retrieval = engine.retriever.retrieve(
                    task=case["task"],
                    service_name_or_id=case["service"],
                    mode=mode,
                )
                scored = score_case(
                    _ids(retrieval["evidence"]),
                    case,
                    retrieval["token_estimate"],
                    len(retrieval["evidence"]),
                )
                scored["policy"] = retrieval.get("policy")
                if mode == "adaptive":
                    answer, answer_source = answer_from_evidence(
                        settings, case["task"], retrieval["evidence"]
                    )
                    grounded = score_groundedness(answer, retrieval["evidence"])
                    scored["groundedness"] = grounded
                    scored["answer_source"] = answer_source
                    scored["answer"] = answer[:800]
                    grounded_scores.append(grounded["supported_citation_rate"])
                    hallucination_scores.append(grounded["hallucination_risk"])
                    abstention_flags.append(1 if grounded.get("abstained") else 0)
                case_result["modes"][mode] = scored
                totals[mode].append(scored["required_recall"])
                waste_totals[mode].append(scored["waste_count"])
                token_totals[mode].append(scored["token_estimate"])
            rows.append(case_result)

        summary = {
            mode: {
                "avg_required_recall": round(sum(totals[mode]) / len(totals[mode]), 3),
                "avg_waste_count": round(sum(waste_totals[mode]) / len(waste_totals[mode]), 3),
                "avg_token_estimate": round(sum(token_totals[mode]) / len(token_totals[mode]), 1),
            }
            for mode in MODES
        }
        disagreements = _disagreements(rows)
        groundedness = {
            "avg_supported_citation_rate": round(sum(grounded_scores) / len(grounded_scores), 3)
            if grounded_scores
            else 1.0,
            "avg_hallucination_risk": round(sum(hallucination_scores) / len(hallucination_scores), 3)
            if hallucination_scores
            else 0.0,
            "avg_abstention_rate": round(sum(abstention_flags) / len(abstention_flags), 3)
            if abstention_flags
            else 0.0,
            "method": "lexical_citation_check",
            "answer_source": answer_source,
        }
        langsmith = _log_langsmith(settings, {"summary": summary, "groundedness": groundedness})
        return {
            "cases": rows,
            "summary": summary,
            "disagreements": disagreements,
            "groundedness": groundedness,
            "langsmith": langsmith,
            "winner_hint": _winner(summary, disagreements),
        }
    finally:
        engine.close()


def _disagreements(rows: list[dict]) -> dict:
    beats_vector = 0
    beats_graph = 0
    for row in rows:
        modes = row["modes"]
        adaptive = modes["adaptive"]["required_recall"]
        if adaptive > modes["vector"]["required_recall"]:
            beats_vector += 1
        if adaptive > modes["graph"]["required_recall"]:
            beats_graph += 1
    return {
        "cases_adaptive_beats_vector": beats_vector,
        "cases_adaptive_beats_graph": beats_graph,
    }


def _winner(summary: dict, disagreements: dict) -> str:
    adaptive = summary["adaptive"]
    huge = summary["huge"]
    if disagreements["cases_adaptive_beats_vector"] or disagreements["cases_adaptive_beats_graph"]:
        return (
            "adaptive beats vector and/or graph on at least one case "
            "(demo org; not a published routing result)"
        )
    if adaptive["avg_required_recall"] >= huge["avg_required_recall"] - 0.05 and adaptive["avg_token_estimate"] < huge["avg_token_estimate"]:
        return "adaptive matches huge-context recall with a smaller token budget"
    return "inspect per-case misses; expand the eval set before claiming a routing win"


def _log_langsmith(settings: Settings, payload: dict) -> dict:
    if not (settings.langchain_tracing_v2 and settings.langchain_api_key):
        return {"logged": False, "reason": "tracing disabled"}
    try:
        from langsmith import Client

        client = Client(api_key=settings.langchain_api_key)
        client.create_run(
            name="engram-eval",
            run_type="chain",
            inputs={"eval": "v1.5-groundedness"},
            outputs=payload,
            project_name=settings.langchain_project,
        )
        return {"logged": True, "project": settings.langchain_project}
    except Exception as exc:
        return {"logged": False, "error": type(exc).__name__}
