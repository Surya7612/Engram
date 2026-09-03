# Before you build Engram (canonical direction)

> **Status:** Authoritative strategic note (2026). Product/docs/site should follow this.  
> Summaries: [`../README.md`](../README.md) · [`../product-vision.md`](../product-vision.md) · [`../AGENTS.md`](../AGENTS.md)

---


Your old thesis was essentially:

Engineering knowledge → structured memory → better answers.

The stronger 2026 thesis is:

Engineering intent → task-specific context → risk-aware routing → controlled agent execution → independent verification → organizational learning.

The knowledge graph survives. Neo4j survives. Qdrant survives. Provenance becomes even more important. But they become the substrate, not the product.

1. The new mental model for Engram

I would describe Engram internally as having six planes:

Plane	Question it answers
Context Plane	What does this organization/system know about this task?
Routing Plane	Which context, agent, tools and model should handle it?
Execution Plane	How should the work be decomposed and performed?
Verification Plane	Is the proposed change actually correct and safe?
Governance Plane	Can this action happen automatically, or does a human need to approve it?
Learning Plane	What did the outcome teach Engram about future tasks?

That is substantially more interesting than "RAG over engineering artifacts."

And this is where your OpenRouter analogy becomes useful.

OpenRouter currently classifies tasks and routes them among models according to task characteristics, cost/quality preferences and fallbacks.

Engram could perform three different kinds of routing:

Context routing

For this task, what information does the agent need?

Capability routing

Which agent/model/tool combination is best suited for this task?

Risk routing

What verification/approval path does this task require?

That is much more defensible than "OpenRouter, but for coding agents."

2. Your AI office fits in the Execution Plane

Imagine this request enters Engram:

"Increase the auth-service session TTL from 24 hours to 7 days."

A naïve coding agent sees a constant and changes it.

Engram sees something different.

                    USER / ISSUE / LINEAR TASK
                              │
                              ▼
                      ┌───────────────┐
                      │ TASK ANALYZER │
                      └───────┬───────┘
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       Context Router     Risk Engine     Capability Router
             │                │                │
             ▼                ▼                ▼
       Repo / PR / ADR    Security risk    Agent expertise
       Incidents / docs   Blast radius     Model capability
       Ownership / tests  Data sensitivity Cost / latency
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                      ┌───────────────┐
                      │ MANAGER AGENT │
                      └───────┬───────┘
                              │
                     creates Task Graph
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       Code Agent        Test Agent      Security Agent
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                     Candidate Change
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             Reviewer Agent       Deterministic Evals
             architecture         tests / lint / policy
             semantics            static analysis
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       GOVERNANCE GATE
                              │
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
                ALLOW        REVIEW       BLOCK
                  │
                  ▼
            RESULT + TELEMETRY
                  │
                  ▼
             Learning Layer

Now we're getting somewhere.

But there's an important correction to your idea:

The manager should not be king.

If the manager agent decides:

what context matters,
who executes,
whether execution succeeded,
and whether the change is safe,

you've built one hallucinating LLM with an organizational chart around it.

That's bad architecture.

Engram itself should provide the manager with constraints.

The manager might propose:

"Implementation Agent handles this."

But Engram says:

"This touches Authentication + Session Management. Historical INC-45 involved session invalidation. Security review mandatory. ADR-12 requires max TTL of 48 hours. Human approval required to override."

Now the manager can't simply talk its way around reality.

That's the safety layer.

3. And your reviewer idea is extremely important

But don't think of it as:

Junior AI → Senior AI → Manager AI.

LLMs don't magically become reliable because we give them corporate titles.

Think separation of duties.

The implementation agent should not determine whether its own implementation is correct.

The reviewer should ideally have:

different instructions, different context emphasis, possibly a different model, independent tool access and no incentive to preserve the implementer's solution.

For particularly important tasks you could even have:

Implementation
       ↓
Correctness Reviewer
       ↓
Security Reviewer
       ↓
Architecture Reviewer
       ↓
Automated Tests
       ↓
Human Approval

But not for every change.

Anthropic found multi-agent systems can consume roughly 15× the tokens of ordinary chat interactions and specifically warns that multi-agent systems aren't ideal when work is tightly coupled or not meaningfully parallelizable.

Therefore Engram should determine how much "company" to instantiate.

That actually creates a compelling feature.

Risk	Execution
Trivial documentation change	One cheap agent
Localized low-risk bug	Coder + deterministic tests
Normal backend change	Coder + reviewer
Auth/payment/data migration	Manager + specialists + reviewers
Production-critical irreversible action	Agents advise; human authorizes
Policy violation	Block

That's Engram.

Not "use lots of agents."

Use the minimum agent organization necessary to safely complete the task.

That's a much better principle.

4. There is already serious competition

We should not lie to ourselves about this.

OpenAI now explicitly supports multi-agent coding and has published Symphony, an orchestration system that turns project-management work into coding-agent work. Anthropic is experimenting with parallel agent teams. YC companies are already attacking adjacent territory: Runtime focuses on guardrails/sandboxes/observability for coding agents; Driver is explicitly a codebase context layer; Graphify builds continuously updated knowledge graphs and verifies changes; Linzumi coordinates fleets of coding agents.

Therefore:

Multi-agent orchestration is not your moat.

Knowledge graphs are not your moat.

Vector retrieval is definitely not your moat.

Potential Engram moat:

Risk-aware, outcome-learning context and capability routing for engineering agents.

That's considerably narrower—and considerably stronger.

YC's current RFS makes the timing interesting. Its Summer 2026 "Company Brain" thesis explicitly describes structured organizational knowledge becoming executable context for AI, while its "AI Operating System for Companies" request describes turning company artifacts into a closed-loop intelligence layer.

So you're pointing toward a genuine frontier problem.

But that also means everyone else sees it.

Execution/evidence matters enormously.

5. The really interesting closed loop

This is the part I would push hardest.

Today:

Task
 ↓
Engram chooses context
 ↓
Agent performs task
 ↓
Reviewer evaluates
 ↓
Done

Eventually:

Task
 ↓
Context Policy
 ↓
Agent Policy
 ↓
Execution
 ↓
Verification
 ↓
Outcome
 ↓
Was the context sufficient?
Was the agent appropriate?
Was review necessary?
What information was missing?
What caused failure?
 ↓
Update routing policy
 ↓
Better next task

Now imagine Engram observes:

PostgreSQL migration tasks handled by Agent A using Claude X succeed 96% of the time when schema history + related incidents + migration docs are supplied.

But:

Migration tasks using generic repository RAG succeed 72%.

Or:

Auth changes involving historical incidents have a 3× higher review-failure rate unless incident context is included.

That becomes extraordinarily interesting.

You're no longer building a chatbot.

You're building an empirical engineering-management system for AI workers.

And now your "AI office" concept actually has substance.

6. Engram can maintain an Agent Registry

Something like:

Agent: backend_engineer
Skills:
  Python
  FastAPI
  PostgreSQL
  distributed_systems


Allowed Tools:
  repo_read
  repo_write
  unit_tests
  staging_db


Forbidden:
  production_db
  secrets


Historical Performance:
  API bugfix .............. 94%
  database migration ...... 88%
  frontend ................ 41%


Preferred Models:
  Model X → complex architecture
  Model Y → routine implementation


Average Cost:
  $1.72 / task

Another:

Agent: security_reviewer


Skills:
  authentication
  authorization
  secrets
  OWASP
  dependency analysis


Permissions:
  READ ONLY


Cannot:
  modify implementation


Required for:
  auth/*
  payment/*
  secrets/*

Now the "manager" is not simply saying:

Go Bob, fix this.

It is effectively doing resource scheduling across artificial expertise.

That's a serious computer-science problem.

Scheduling.

Optimization.

Cost.

Reliability.

Dependency graphs.

Capability matching.

Context-window allocation.

Fault tolerance.

Concurrency.

Permission systems.

Observability.

This is precisely why Engram can become useful for your systems/backend learning too.

7. One more architectural addition: Task Graph

You already have an Engineering Context Graph.

Add another concept:

Work Graph / Task Graph

The Context Graph describes reality:

Service ─DEPENDS_ON→ Redis
Incident ─AFFECTED→ AuthService
ADR ─GOVERNS→ SessionCaching
PR ─MODIFIED→ AuthService

The Work Graph describes intended execution:

TASK-42
 ├── analyze session architecture
 ├── modify TTL
 ├── update tests
 ├── run integration tests
 └── perform security review

Dependencies:

analyze
   ↓
implementation
   ↓
tests
   ↓
security review
   ↓
approval

Now Engram connects:

CONTEXT GRAPH
      ↕
   TASK GRAPH
      ↕
 AGENT GRAPH

That's powerful.

Eventually you effectively have three graphs:

What the system is.

What needs to be done.

Who/what can do it.

That is much more compelling intellectually than our original Engram design.

8. I'd change your positioning now

Your existing README isn't wrong. About 60% of it remains useful.

But this:

"structured engineering memory layer"

is now too weak.

I would move toward this:

Engram — Engineering Context, Routing & Safety Layer
Context-aware control plane for AI-assisted software engineering
Overview

Engram is an engineering context and safety system for AI-assisted software development.

It builds a structured model of a software organization across source code, services, pull requests, incidents, architectural decisions, documentation, ownership and operational history, then uses that model to determine what context an AI agent needs, which agent or model should perform the work, and what verification is required before a change can proceed.

Engram is based on a simple principle:

AI engineering agents should not operate only on the code they can see. They should operate within the technical history, constraints, ownership boundaries and risk model of the system they are changing.

Rather than treating engineering knowledge as passive documentation or retrieving the same context for every request, Engram constructs task-specific context and execution policies.

A request can therefore move through a controlled pipeline:

Engineering Task
      ↓
Task Understanding
      ↓
Context Routing
      ↓
Risk Analysis
      ↓
Capability / Agent Routing
      ↓
Task Decomposition
      ↓
Agent Execution
      ↓
Independent Verification
      ↓
Governance Gate
      ↓
Outcome + Learning
Core System

Engram maintains three connected representations.

ENGINEERING CONTEXT GRAPH
What does the system know?

Services
Code
PRs
Incidents
ADRs
Documentation
Ownership
Dependencies
Operational history


TASK GRAPH
What needs to happen?

Objectives
Subtasks
Dependencies
Constraints
Required evidence
Risk level


AGENT / CAPABILITY GRAPH
Who or what should perform it?

Agent capabilities
Models
Tools
Permissions
Cost
Latency
Historical reliability
Specialization

Together these allow Engram to reason not only about what information is relevant, but also about how engineering work should be performed safely.

Routing

Engram introduces three routing problems.

Context Routing

Determine which pieces of engineering knowledge should enter an agent's working context for a particular task.

A database migration may require schema history, related incidents and previous migrations, while a UI copy change may require almost none of this information.

Capability Routing

Determine which agent, model and tools are appropriate for the work based on task requirements, permissions, historical performance, cost and latency.

Risk Routing

Determine the verification path required before execution or deployment.

Low-risk work may require only automated tests. Higher-risk work may require independent code review, security review, architectural checks or explicit human approval.

Agentic Execution

For complex work, Engram can coordinate specialized engineering agents.

                    Manager / Planner
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Backend Agent  Test Agent  Security Agent
              │            │            │
              └────────────┼────────────┘
                           ▼
                    Candidate Change
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Reviewer      Automated     Policy
           Agent          Evals       Engine
              └────────────┼────────────┘
                           ▼
                    Allow / Review / Block

Agents are not treated as unrestricted autonomous workers. Engram supplies task-specific context, permissions and policy constraints before execution and requires appropriate evidence afterward.

Closed-Loop Engineering Memory

Engram's long-term objective is not only to remember engineering history but to learn from engineering outcomes.

For each task the system can record:

Task
Context selected
Agent/model selected
Actions performed
Tests executed
Review findings
Human corrections
Final outcome
Cost
Latency

Over time this creates an empirical record of which context, models, agents and review strategies work best for different classes of engineering tasks.

This enables Engram to evolve from static retrieval toward adaptive engineering context and execution policies.

Positioning

Engram is not another coding agent.

It is the context, routing and safety layer around coding agents.

Coding agents perform work.

Engram determines:

What do they need to know?
Who should perform the task?
What are they allowed to do?
What could go wrong?
Who or what must verify it?
What did the organization learn from the result?

The long-term goal is to make increasingly autonomous software engineering possible without separating AI execution from organizational context, technical history, provenance and human governance.

That is where I would take the README.

Not all of the future architecture needs to exist today. The README should clearly distinguish implemented / experimental / vision, because otherwise sophisticated interviewers will immediately realize you're describing a system much larger than the repository.

9. What I would actually build next

Here is where I contradict the temptation you're probably going to have.

Do not start building the entire AI company tomorrow.

That would murder both Engram and your interview preparation.

I would sequence it:

Engram V1 — Context Engine. Finish your existing Neo4j + Qdrant + provenance architecture. Real GitHub repository ingestion. Real queries. Preflight packet. This proves the foundation.
Engram V1.5 — Context Router. Given a task, dynamically determine which context sources and traversal depths are needed. Build the evaluation harness immediately. Compare static vector, graph retrieval, huge-context baseline and adaptive Engram retrieval.
Engram V2 — Agent Router. Start extremely small: Manager + Backend Agent + Reviewer. Isolated worktrees/sandboxes. Don't build fifteen fake personas.
Engram V2.5 — Risk Router. Different agent/review configurations according to predicted blast radius. Start with deterministic rules; don't unnecessarily ML-ify everything.
Engram V3 — Learning Layer. Capture outcomes and begin learning which context/agent configurations actually correlate with task success.

That progression gives you five separate portfolio milestones instead of disappearing for six months and emerging with an incomprehensible 40,000-line "agent operating system."

10. It also gives you a very good research program

Your first paper can stay narrow:

Task-Adaptive Context Routing for Repository-Level Software Engineering Agents Under Fixed Token Budgets

Second:

Does Historical Engineering Context Improve Agent Performance on Risk-Sensitive Software Changes?

Third:

Capability-Aware Routing for Heterogeneous Software Engineering Agents

Fourth:

Risk-Adaptive Verification for Autonomous Software Changes

Fifth, eventually:

Learning Context and Agent Selection Policies from Software Engineering Outcomes

Notice what happened.

The startup research, DCS research, portfolio project, backend practice, system-design practice and agentic-AI specialization are starting to overlap.

That's exactly what we wanted.

11. Havenly should become your dogfood environment

Don't put "Engram" into Havenly's customer product simply because you own both.

Instead:

Build Havenly using Engram.

Imagine saying eventually:

"We used Engram to coordinate 1,800 agentic engineering tasks while developing Havenly. It selected task context, routed work among coding agents, enforced review requirements and recorded whether each context policy produced successful changes."

That is much more powerful than:

"Engram is a Havenly feature."

Havenly becomes one real test organization.

Engram remains general infrastructure.

If the internal workflow becomes genuinely valuable, then you have startup evidence.