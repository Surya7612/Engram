# Engram — Product Vision & System Strategy

### Engineering Context, Routing & Safety Layer for AI-assisted software engineering

> **2026 direction update:** The center of gravity moved from “structured engineering memory / RAG” to a **context → routing → controlled execution → verification → governance → learning** control plane.  
> Canonical write-up: [`website/product-direction.md`](./website/product-direction.md) · Summary: [`README.md`](./README.md) · Live Try: [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)  
> Sections below retain problem framing and MVP discipline. Treat **merge automation / learned policies / full AI office** as vision unless marked implemented (V1–V3 alpha).

---

## 0. Updated thesis (authoritative)

**Old thesis:** Engineering knowledge → structured memory → better answers.

**Current thesis:**

```text
Engineering intent
  → task-specific context
  → risk-aware routing
  → controlled agent execution
  → independent verification
  → organizational learning
```

Neo4j, Qdrant, and provenance **survive**—as substrate, not as the product story.

### Moat (narrow and strong)

> Risk-aware, outcome-learning **context and capability routing** for engineering agents.

Not: multi-agent orchestration alone · knowledge graphs alone · vector retrieval alone · “OpenRouter for coding agents.”

### Six planes

| Plane | Question |
|---|---|
| Context | What does this organization know about this task? |
| Routing | Which context, agent, tools, and model should handle it? |
| Execution | How should work be decomposed and performed? |
| Verification | Is the proposed change correct and safe? |
| Governance | Automatic, review, or human approval? |
| Learning | What should change about future routing? |

### Three graphs

1. **Context graph** — what the system is (services, PRs, incidents, ADRs, ownership, deps)  
2. **Task / work graph** — what needs to happen (objectives, subtasks, constraints, risk)  
3. **Agent / capability graph** — who/what can do it (skills, tools, permissions, cost, reliability)

### Three routing problems

- **Context routing** — what enters the agent’s working set for this task  
- **Capability routing** — which agent/model/tools  
- **Risk routing** — which verification / approval path  

**Constraint principle:** the manager agent proposes; Engram enforces organizational reality (ADRs, incidents, ownership, policy). Separation of duties: implementer ≠ sole verifier. Instantiate the **minimum** agent organization justified by risk.

### Build sequence (do not skip)

| Version | Focus |
|---|---|
| **V1** | Context Engine — real ingestion, graph + vectors, provenance, preflight packet |
| **V1.5** | Context Router + evaluation harness |
| **V2** | Small Agent Router (Manager + Backend + Reviewer) |
| **V2.5** | Risk Router (deterministic rules first) |
| **V3** | Learning Layer from outcomes |

A first product organization is a **dogfood tenant**, not Engram’s customer-facing feature.

### Research track (overlap with product)

1. Task-adaptive context routing under fixed token budgets  
2. Historical context on risk-sensitive software changes  
3. Capability-aware routing for heterogeneous SE agents  
4. Risk-adaptive verification  
5. Learning selection policies from engineering outcomes  

---

## 1. Introduction

Engram addresses a core failure mode of AI-assisted engineering: agents that edit code **without** operating inside the organization’s technical history, constraints, ownership boundaries, and risk model.

Engineering knowledge is still distributed across PRs, incidents, ADRs, docs, and informal channels. Connecting those artifacts into a **queryable context substrate** remains necessary—but insufficient. The product must also decide **what context matters for a task**, **who executes**, **how verification happens**, and **what the org learns**.

### 1.1 Core thesis

The central idea is not “use a smarter model” or “retrieve more docs.”

**Agents should reason and act inside structured organizational context, with explicit routing, verification, and governance—not repeatedly guess meaning and risk from disconnected text.**

Durable advantage comes from:

- **Better task-specific context** (graph + vectors + provenance)  
- **Risk-aware routing** (context / capability / verification)  
- **Independent verification + human gates** where blast radius demands it  
- **Closed-loop learning** from outcomes (later stages)

The LLM is a **reasoning and execution layer**, not the system’s long-term memory or sole risk authority.

This document outlines product vision, positioning, users, use cases, MVP boundaries, and long-term evolution. Where it conflicts with §0 or `website/product-direction.md`, **§0 and that file win**.

---

## 2. Problem Definition

### 2.1 Fragmented Knowledge

Engineering systems accumulate knowledge across:

* Code changes (PRs, commits)
* Operational events (incidents, outages)
* Architectural decisions (ADRs)
* Documentation and runbooks

These artifacts are distributed, inconsistently structured, and weakly linked—so engineers (and agents) reconstruct understanding manually.

---

### 2.2 Implicit Relationships

Critical relationships are rarely explicit:

* Which PR introduced a failure?
* Which ADR constrains this change?
* Which services sit in the blast radius?

---

### 2.3 Tribal knowledge & agent risk

System understanding concentrates in senior engineers. Meanwhile coding agents ship changes **without** that tribal context—raising the cost of wrong merges even as they raise velocity.

---

### 2.4 Limitations of current AI systems

LLMs and coding agents are strong at local code edits but weak at:

* persistent organizational memory
* blast-radius / policy awareness
* separation of implementation vs verification
* learning which context/agent policies actually work

Without structured grounding **and** routing/governance, outputs cannot be trusted for system-level change.

---

## 3. Product Vision

Engram aims to become the **context, routing, and safety layer around coding agents**—enabling increasingly autonomous engineering **without** separating execution from organizational context, provenance, and human governance.

Near-term (V1): prove the **context engine**—preflight packets grounded in graph + vectors + evidence.

Mid-term: **adaptive context routing**, then small **agent + risk routers**.

Long-term: **closed-loop learning** over which context/agent/review strategies succeed.

---

### 3.1 Core Principle

> Intelligence should not compensate for missing structure—or missing policy.  
> Provide structure and constraints so intelligence can operate reliably.

Also: **use the minimum agent organization necessary to safely complete the task.**

---

### 3.2 Strategic Positioning

Engram is not:

* a replacement for Cursor, Copilot, or Codex
* a general-purpose “chat with your docs” app
* a simple RAG pipeline
* “OpenRouter, but for coding agents”
* an unrestricted multi-agent swarm or full “AI company” on day one
* a plug-and-play enterprise platform in v1

Engram **is**:

* a structured **engineering context substrate** (graph + semantic retrieval + provenance)
* a path to **task-adaptive context routing**
* a path to **capability- and risk-aware agent routing**
* a **governance gate** (allow / review / block) with human authority on high-risk actions
* eventually an **empirical learning system** for AI engineering work

---

## 4. Target Users

Primary:

* Software engineers & tech leads (pre-merge / pre-change)
* SRE / on-call (incident context)
* Platform / DevEx (policy & agent guardrails)
* AI tooling owners embedding coding agents into SDLC

Secondary (later):

* Engineering managers / CTO offices evaluating agent adoption risk
* Security / compliance stakeholders for high-blast-radius paths

---

## 5. Core Use Cases

### 5.1 Preflight (V1 wedge)

Before a risky change: assemble evidence-backed context—related incidents, deps, ADRs, ownership—and recommend review intensity.

### 5.2 Incident context

During outages: related changes, similar incidents, owners, runbooks—without reconstructing Slack archaeology.

### 5.3 Agent-guarded change (V2+)

Given a task (“increase auth session TTL…”): route context, constrain agents, require independent review when history/policy demands it, gate on allow/review/block.

### 5.4 Outcome learning (V3)

Record which context/agent/review configs correlated with success; improve next routing policy.

---

## 6. MVP Boundaries (V1 — Context Engine)

**In scope**

* Controlled / GitHub-oriented ingestion of engineering artifacts
* Explicit entity & relationship modeling (context graph)
* Hybrid retrieval (Neo4j + Qdrant)
* Provenance / evidence links on claims
* Preflight-style query / packet API
* Clear non-claims: Engram advises; humans own critical merges

**Out of scope for V1**

* Full manager + multi-specialist agent office
* Learned routing policies from production outcomes
* Enterprise SSO / multi-tenant SaaS polish
* Claiming autonomous “safe to merge” without evidence

**Success signal (design partners):** reduced time-to-context on high-risk PRs / clearer review decisions with linked evidence—not “number of agents spun up.”

---

## 7. System Architecture (summary)

See README for diagrams. Substrate remains:

```text
Artifacts → Ingestion → Extraction
  → Context Graph (Neo4j) + Vectors (Qdrant)
  → Provenance / Semantic layer
  → Hybrid query + orchestration → API
```

Vision extends with Task Graph, Agent Registry, Risk Router, Verification plane, Governance gate, Learning store.

**Important:** Engram supplies **constraints** to any planner/manager agent. A single LLM that also judges its own safety is an anti-pattern.

---

## 8. Trust & Safety

* Risk reductions are **probabilistic**, not guarantees  
* Critical / irreversible actions remain **human-approved** by policy  
* Claims that affect merge/deploy decisions should be **source-linked**  
* No unsupported root-cause or “safe” declarations without evidence  
* Separation of duties on high-risk paths (implement ≠ verify alone)

---

## 9. Competitive reality

Multi-agent coding orchestration, codebase context layers, and engineering graphs are contested. Engram’s differentiation is the **closed loop**: task-specific context + capability matching + risk-adaptive verification + learning from outcomes—backed by provenance.

Execution and evidence matter more than architecture slides.

---

## 10. Evolution roadmap

Aligned with [`website/product-direction.md`](./website/product-direction.md):

1. **V1 Context Engine** — graph + vectors + provenance + real repo queries + preflight  
2. **V1.5 Context Router** — adaptive retrieval + evals vs static RAG / huge-context baselines  
3. **V2 Agent Router** — Manager + Backend + Reviewer only; sandboxed worktrees  
4. **V2.5 Risk Router** — rule-based blast radius → review configuration  
5. **V3 Learning** — outcome telemetry → routing policy improvement  

Research themes track this sequence (token-budget context routing first).

---

## 11. Non-goals (near term)

* Expanding to a large agent persona catalog before context routing works  
* Replacing deterministic risk rules with ML before rules prove useful  
* Embedding Engram as a customer feature of another product instead of dogfooding it as infrastructure  
* Marketing the full AI office as if it were already shipped  

---

## 12. Document history

Earlier drafts framed Engram primarily as a structured engineering memory layer. That remains the **foundation**. The product story is the **control plane** on top of that foundation. Prefer §0, README, and `website/product-direction.md` for external copy.
