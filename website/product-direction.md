# Engram product direction

> **Status:** Canonical product strategy (2026). Marketing, README, and implementation docs should follow this.  
> Related: [`../README.md`](../README.md) · [`../product-vision.md`](../product-vision.md) · [`../AGENTS.md`](../AGENTS.md) · Live Try: [https://engram-cjph.onrender.com/try](https://engram-cjph.onrender.com/try)

---

## Thesis

Earlier framing treated Engram primarily as structured engineering memory:

```text
Engineering knowledge → structured memory → better answers
```

The stronger product thesis is a control plane for AI-assisted engineering:

```text
Engineering intent
  → task-specific context
  → risk-aware routing
  → controlled agent execution
  → independent verification
  → organizational learning
```

The knowledge graph, Neo4j (or equivalent graph store), Qdrant, and provenance remain foundational. They are the **substrate**, not the whole product.

---

## 1. System model — six planes

| Plane | Question |
|---|---|
| **Context** | What does this organization know about this task? |
| **Routing** | Which context, agent, tools, and model should handle it? |
| **Execution** | How should the work be decomposed and performed? |
| **Verification** | Is the proposed change correct and safe? |
| **Governance** | Can this proceed automatically, or must a human approve? |
| **Learning** | What did the outcome teach Engram about future tasks? |

This is materially stronger than “RAG over engineering artifacts.”

---

## 2. Three routing problems

Engram addresses three related routing problems (distinct from model marketplaces that only route among LLMs):

### Context routing

For this task, which engineering knowledge enters the agent’s working context?

A database migration may need schema history and related incidents. A UI copy change may need almost none.

### Capability routing

Which agent, model, and tools fit the work—based on requirements, permissions, historical performance, cost, and latency?

### Risk routing

What verification and approval path is required?

Trivial documentation changes may use a cheap single agent. Auth, payments, and migrations require specialists, independent review, and often a human gate.

**Principle:** use the **minimum agent organization** necessary to complete the task safely. A manager agent may propose; Engram supplies constraints (incidents, ADRs, ownership, policy). The manager is not the final authority.

---

## 3. Execution plane — constrained agent organization

Example task:

> Increase the auth-service session TTL from 24 hours to 7 days.

A naïve coding agent sees a constant and changes it. Engram treats the request as organizationally constrained work:

```text
USER / ISSUE / TASK
        │
        ▼
  Task understanding
        │
 ┌──────┼──────────────┐
 ▼      ▼              ▼
Context  Risk         Capability
router   engine       router
 │       │             │
 ▼       ▼             ▼
Repo/PR/ADR   Blast radius   Agent / model fit
Incidents     Data sensitivity
Ownership     Policy
        │
        ▼
  Manager (proposes only)
        │
        ▼
  Task graph / role plan
        │
 ┌──────┼──────────┐
 ▼      ▼          ▼
Code   Tests    Security / review
        │
        ▼
 Candidate change (sandbox / worktree)
        │
 ┌──────┴──────┐
 ▼             ▼
Reviewer     Deterministic checks
(read-only)  tests / lint / policy
        │
        ▼
 Governance gate → Allow / Review / Block
```

Important corrections vs a naïve “AI office”:

1. **Titles are not reliability.** Role labels without separation of duties and evidence produce coordinated hallucination.
2. **Implementer ≠ sole verifier** on high-risk paths.
3. **Independent review** (agent and/or human) is required where blast radius demands it.
4. Candidates live in **isolated worktrees**; merge and push remain out of scope until governance explicitly allows them.

---

## 4. Moat

| Not the moat | The moat |
|---|---|
| Multi-agent orchestration alone | Risk-aware, outcome-learning **context and capability routing** |
| Knowledge graphs alone | Task-specific context + verification policy |
| Vector retrieval alone | Closed loop from intent → gate → outcome |

Frontier claim: organizations will need infrastructure that decides **what agents know**, **who acts**, **what must be verified**, and **what was learned**—with provenance.

---

## 5. Learning loop (long-term)

```text
Task → Context policy → Agent policy → Execution → Verification → Outcome
  → Was context sufficient?
  → Was the agent appropriate?
  → Was review necessary?
  → What was missing?
  → Update routing policy
```

Illustrative (not shipped metrics): migration tasks with schema history and related incidents may succeed more often than generic repository RAG; auth changes involving historical incidents may fail review more often unless incident context is included.

Near-term V3 ships an **outcome log** and **similar-task prior lookup**. Trained routing policies remain later-stage work.

---

## 6. Agent registry (vision)

Engram may maintain a registry of agent capabilities, permissions, forbidden actions, historical performance, preferred models, and cost. Example shape:

- **backend_engineer** — write access to repos/tests; no production DB or secrets  
- **security_reviewer** — read-only; required for auth/payment paths; cannot modify implementation  

The registry supports capability routing; it is not a substitute for policy or provenance.

---

## 7. Positioning

**Engram is not another coding agent.**

It is the **context, routing, and safety layer around coding agents**.

Coding agents perform work. Engram determines:

- What do they need to know?  
- Who should perform the task?  
- What are they allowed to do?  
- What could go wrong?  
- Who or what must verify it?  
- What did the organization learn from the result?  

Long-term goal: make increasingly autonomous software engineering possible **without** separating AI execution from organizational context, technical history, provenance, and human governance.

Docs and marketing must distinguish **implemented (alpha)** vs **vision**. Do not present the full control-plane story as shipped product.

---

## 8. Build sequence

Do not start with a full multi-agent “AI company.” Sequence:

| Stage | Focus | Intent |
|---|---|---|
| **V1** | Context Engine | Graph + vectors + provenance + real ingestion + preflight |
| **V1.5** | Context Router | Task-adaptive retrieval + evaluation harness |
| **V2** | Agent Router | Manager + Backend + Reviewer; isolated worktrees |
| **V2.5** | Risk Router | Blast radius → review configuration (rules first) |
| **V3** | Learning Layer | Outcome telemetry; later, learned routing policies |

This yields clear milestones and keeps the repository comprehensible.

---

## 9. Research themes

Aligned with the build sequence:

1. Task-adaptive context routing under fixed token budgets  
2. Does historical engineering context improve risk-sensitive agent changes?  
3. Capability-aware routing for heterogeneous SE agents  
4. Risk-adaptive verification for autonomous software changes  
5. Learning context and agent selection policies from outcomes  

---

## 10. Dogfood tenant policy

Engram remains **general infrastructure**. Product organizations (for example an internal or companion product) should be **dogfood tenants**, not Engram’s customer-facing feature surface.

Prefer: use Engram while building other systems, measure whether context and risk policies improve outcomes.  
Avoid: embedding “Engram” as a branded feature of another product before the control plane is proven.
