#!/usr/bin/env python3
"""Engram CLI."""

import argparse
import json
import sys

import uvicorn

from engram.agents.summary import format_run
from engram.config import get_settings
from engram.engine import EngramEngine
from engram.eval.harness import run_eval
from engram.eval.summary import format_eval
from engram.ingestion.github import ingest_github
from engram.ingestion.seed import seed_from_sample
from engram.learning.store import OutcomeStore
from engram.models.schemas import AgentRunRequest, PreflightRequest, QueryRequest


def cmd_seed(_: argparse.Namespace) -> int:
    result = seed_from_sample(get_settings())
    print(json.dumps(result, indent=2))
    return 0


def cmd_ingest_github(args: argparse.Namespace) -> int:
    try:
        result = ingest_github(
            get_settings(),
            repo=args.repo,
            service=args.service,
            limit=args.limit,
            token=args.token,
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


def cmd_health(_: argparse.Namespace) -> int:
    eng = EngramEngine(get_settings())
    try:
        print(json.dumps({"health": eng.health()}, indent=2))
    finally:
        eng.close()
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    eng = EngramEngine(get_settings())
    try:
        packet = eng.preflight(
            PreflightRequest(
                service=args.service,
                task=args.task,
                proposed_pr_number=args.pr,
                mode=args.mode,
            )
        )
        print(packet.model_dump_json(indent=2))
    finally:
        eng.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    eng = EngramEngine(get_settings())
    try:
        response = eng.query(QueryRequest(question=args.question, service=args.service))
        print(response.model_dump_json(indent=2))
    finally:
        eng.close()
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    result = run_eval(get_settings())
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_eval(result), end="")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    eng = EngramEngine(get_settings())
    try:
        result = eng.run_agents(
            AgentRunRequest(
                service=args.service,
                task=args.task,
                mode=args.mode,
                repo=args.repo,
                token=args.token,
            )
        )
        if args.json:
            print(result.model_dump_json(indent=2))
        else:
            print(format_run(result), end="")
    finally:
        eng.close()
    return 0


def cmd_outcomes(args: argparse.Namespace) -> int:
    store = OutcomeStore(get_settings().local_data_dir / "outcomes.jsonl")
    if args.stats:
        print(json.dumps(store.stats(), indent=2))
        return 0
    rows = store.list(args.limit)
    if not rows:
        print("no outcomes yet")
        return 0
    for row in rows:
        print(
            f"{row.get('id')}  {row.get('gate')}  {row.get('human_decision')}  "
            f"{row.get('service')}  {row.get('task')}"
        )
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    store = OutcomeStore(get_settings().local_data_dir / "outcomes.jsonl")
    outcome_id = args.outcome_id
    if args.last:
        latest = store.latest()
        if not latest:
            print("no outcomes yet", file=sys.stderr)
            return 1
        outcome_id = latest["id"]
    if not outcome_id:
        print("pass an outcome id, or use --last", file=sys.stderr)
        return 1
    try:
        record = store.resolve(outcome_id, args.decision, args.note or "")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(
        f"{record['id']}  {record['gate']}  {record['human_decision']}  "
        f"merged={record.get('merged')}  {record.get('human_note') or ''}".rstrip()
    )
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    uvicorn.run("engram.api.app:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Engram Context Engine + thin Agent Router")
    sub = parser.add_subparsers(dest="command", required=True)

    p_seed = sub.add_parser("seed", help="Load sample org into Neo4j + Qdrant")
    p_seed.set_defaults(func=cmd_seed)

    p_gh = sub.add_parser("ingest-github", help="Ingest pull requests from a GitHub repo (additive, does not clear)")
    p_gh.add_argument("--repo", default="Surya7612/Engram", help="owner/name")
    p_gh.add_argument("--service", default=None, help="Attach PRs to this service (created if missing)")
    p_gh.add_argument("--limit", type=int, default=50)
    p_gh.add_argument("--token", default=None, help="Optional GitHub PAT for this call only")
    p_gh.set_defaults(func=cmd_ingest_github)

    p_health = sub.add_parser("health", help="Check Neo4j and Qdrant connectivity")
    p_health.set_defaults(func=cmd_health)

    p_preflight = sub.add_parser("preflight", help="Run a preflight packet")
    p_preflight.add_argument("--service", default="Auth Service")
    p_preflight.add_argument(
        "--task",
        default="Increase auth session TTL from 24 hours to 7 days",
    )
    p_preflight.add_argument("--pr", type=int, default=None)
    p_preflight.add_argument(
        "--mode",
        default="adaptive",
        choices=["adaptive", "hybrid", "vector", "graph", "huge"],
    )
    p_preflight.set_defaults(func=cmd_preflight)

    p_query = sub.add_parser("query", help="Run a grounded context query")
    p_query.add_argument("--question", required=True)
    p_query.add_argument("--service", default=None)
    p_query.set_defaults(func=cmd_query)

    p_eval = sub.add_parser("eval", help="Run V1.5 retrieval eval harness")
    p_eval.add_argument("--json", action="store_true", help="Print the full eval JSON")
    p_eval.set_defaults(func=cmd_eval)

    p_run = sub.add_parser("run", help="Thin V2/V2.5 agent run (sandbox + risk gate)")
    p_run.add_argument("--service", default="Auth Service")
    p_run.add_argument(
        "--task",
        default="Increase auth session TTL from 24 hours to 7 days",
    )
    p_run.add_argument(
        "--mode",
        default="adaptive",
        choices=["adaptive", "hybrid", "vector", "graph", "huge"],
    )
    p_run.add_argument(
        "--json",
        action="store_true",
        help="Print the full AgentRunResult JSON instead of the compact summary",
    )
    p_run.add_argument("--repo", default=None, help="Optional owner/name for clone worktree")
    p_run.add_argument("--token", default=None, help="Optional GitHub PAT for private clone")
    p_run.set_defaults(func=cmd_run)

    p_outcomes = sub.add_parser("outcomes", help="List V3 outcome log (telemetry, not learned policy)")
    p_outcomes.add_argument("--limit", type=int, default=20)
    p_outcomes.add_argument("--stats", action="store_true")
    p_outcomes.set_defaults(func=cmd_outcomes)

    p_resolve = sub.add_parser("resolve", help="Record a human decision on an outcome (does not merge)")
    p_resolve.add_argument("outcome_id", nargs="?", help="Outcome id from `run` / `outcomes`. Omit if using --last.")
    p_resolve.add_argument("--last", action="store_true", help="Resolve the most recent outcome")
    p_resolve.add_argument("--decision", required=True, choices=["approved", "rejected"])
    p_resolve.add_argument("--note", default="")
    p_resolve.set_defaults(func=cmd_resolve)

    p_serve = sub.add_parser("serve", help="Start FastAPI server")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
