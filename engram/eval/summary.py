def format_eval(result: dict) -> str:
    lines = ["retrieval"]
    for mode, stats in (result.get("summary") or {}).items():
        lines.append(
            f"  {mode:<10} recall {stats['avg_required_recall']:<5}  "
            f"waste {stats['avg_waste_count']:<4}  tokens {stats['avg_token_estimate']}"
        )
    grounded = result.get("groundedness") or {}
    lines.append(
        "groundedness  "
        f"cite {grounded.get('avg_supported_citation_rate')}  "
        f"abstain {grounded.get('avg_abstention_rate')}  "
        f"halluc {grounded.get('avg_hallucination_risk')}  "
        f"({grounded.get('answer_source')})"
    )
    disag = result.get("disagreements") or {}
    lines.append(
        f"disagreements  adaptive>vector {disag.get('cases_adaptive_beats_vector')}  "
        f"adaptive>graph {disag.get('cases_adaptive_beats_graph')}"
    )
    if result.get("winner_hint"):
        lines.append(result["winner_hint"])
    langsmith = result.get("langsmith") or {}
    if langsmith.get("logged"):
        lines.append(f"langsmith  logged project={langsmith.get('project')}")
    lines.append("cases")
    for case in result.get("cases") or []:
        adaptive = (case.get("modes") or {}).get("adaptive") or {}
        grounded_case = adaptive.get("groundedness") or {}
        if grounded_case.get("abstained"):
            cite = "abstained"
        else:
            cite = f"cites {len(grounded_case.get('cited') or [])}"
        lines.append(
            f"  {case.get('id')}: recall {adaptive.get('required_recall')}  {cite}"
        )
    return "\n".join(lines) + "\n"
