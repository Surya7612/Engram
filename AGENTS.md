# AGENTS.md — Engram

## Canonical direction

Read **`website/product-direction.md`** before proposing architecture, scope, or marketing claims.

Summaries:

- [`README.md`](./README.md) — positioning + implemented vs vision  
- [`product-vision.md`](./product-vision.md) — product strategy (aligned to 2026 thesis)  
- [`docs/HOSTED_TRY.md`](./docs/HOSTED_TRY.md) — public demo scope

## What Engram is

**Context, routing & safety layer around coding agents**—not another coding agent, not plain RAG, not “OpenRouter for coding.”

Thesis:

```text
intent → task-specific context → risk-aware routing
  → controlled execution → independent verification
  → governance → organizational learning
```

**Moat:** risk-aware, outcome-learning context & capability routing for engineering agents.

## Non-negotiables

1. **V1 first** — Context Engine (graph + vectors + provenance + real ingestion + preflight). Do not start with a full “AI office.”
2. **Manager is not king** — Engram supplies constraints (ADRs, incidents, ownership, policy).
3. **Separation of duties** — implementer ≠ sole verifier on high-risk work.
4. **Minimum agency** — instantiate only the agent organization risk justifies.
5. **Provenance** — no unsupported “safe to merge” / root-cause claims.
6. **Honest status** — distinguish alpha-implemented / building / vision. V1–V3 alpha exists; merge automation, learned policies, and multi-tenant SaaS do not.
7. **Dogfood tenants only** — companion product orgs are test tenants, not Engram’s product surface.
8. **Public Try is tight** — no BYO clone/run, no browser PATs, no eval on the shared host.

## Build sequence

V1 Context Engine → V1.5 Context Router (+ evals) → V2 Agent Router (Manager + Backend + Reviewer) → V2.5 Risk Router (rules first) → V3 Learning Layer (log + lookup now; trained policies later).

## When editing the website

Keep marketing aligned with the control-plane story **without claiming vision features as shipped**. Point Try CTAs at the hosted `/try` URL. Bump `?v=` on CSS/JS when styles or scripts change.
