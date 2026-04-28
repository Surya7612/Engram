# Engram — Product Vision

## Pre-change context and safety layer for AI-assisted engineering

---

## 1. The Problem

Software teams are adopting AI coding agents faster than their systems can safely support them.

AI tools can now write code, modify files, generate PRs, and assist with debugging. But they still lack one critical thing:

**structured engineering context.**

Before changing a system, an engineer or AI agent needs to know:

- What service is being changed?
- What has broken here before?
- Which PRs are historically related?
- What architectural decisions affect this area?
- Which dependencies could be impacted?
- Is this change risky?
- Does it require human approval?

Today, that context is fragmented across:

- GitHub PRs
- incidents
- ADRs
- documentation
- tickets
- Slack threads
- people’s memory

The result is that engineering teams move fast, but often without enough context.

This creates:

- risky code changes
- slower onboarding
- repeated mistakes
- fragile AI-agent workflows
- poor traceability between decisions, changes, and failures

As AI agents become more capable, this problem becomes more urgent.

The bottleneck is shifting from:

> Can AI write code?

to:

> Can AI understand what it might break?

---

## 2. What Engram Is

Engram is a **pre-change context and safety layer for AI-assisted engineering teams**.

It connects engineering artifacts such as PRs, incidents, services, and architectural decisions into a structured knowledge graph, then uses that context to help engineers and AI agents make safer changes.

Engram answers questions like:

- “What should I know before modifying this service?”
- “What incidents are related to this part of the system?”
- “What architectural decisions affect this change?”
- “What could break if this service changes?”
- “Should this agent be allowed to perform this action?”

Engram is not a coding assistant.

It is the context and safety layer that makes coding assistants more reliable.

---

## 3. Core Thesis

LLMs are becoming better at generating code, but software systems are not just code.

They are made of:

- decisions
- incidents
- dependencies
- ownership
- constraints
- historical failures
- undocumented assumptions

Most AI coding agents operate with limited local context. They may understand a file or repo, but they do not reliably understand the history, risk, and operational context around a system.

Engram’s thesis:

> The next layer of AI-assisted software engineering will not only be code generation.  
> It will be structured context, risk awareness, and controlled execution.

---

## 4. Product Wedge

The first wedge is:

## Pre-flight checks for AI coding agents and engineering teams

Before an engineer or AI agent changes code, Engram generates a structured context packet:

- affected services
- related incidents
- relevant PRs
- applicable decisions
- known risks
- dependency context
- recommended review areas
- whether human approval is required

This turns Engram into a pre-change safety layer.

Instead of asking an AI agent to blindly modify code, teams can first ask:

> “What context should this agent know before touching this system?”

---

## 5. Initial Product

The initial product focuses on engineering teams using GitHub and AI coding tools.

### Inputs

- Pull requests
- Incident reports
- Architecture Decision Records
- Service documentation
- Ownership metadata
- Dependency notes

### Core system

- knowledge graph for structured relationships
- vector retrieval for semantic search
- semantic layer for consistent meaning
- agentic orchestration for query flow
- API for context and risk summaries

### Output

A structured engineering context summary before code changes.

Example:

```text
Change target: Auth Service

Relevant context:
- Auth Service owns login and session validation
- Redis caching strategy defined in ADR-12
- Incident INC-45 involved stale session data caused by TTL mismatch
- PR-123 modified cache invalidation logic
- Billing Service depends on Auth Service session validation

Risk assessment:
- Medium risk
- Review cache TTL behavior
- Validate session invalidation tests
- Human review recommended before merge
6. Why Now

AI coding agents are becoming more capable and more widely adopted.

Engineering teams want the speed of AI-assisted development, but they do not fully trust agents with production systems.

The current market is focused heavily on:

code generation
code review
autocomplete
autonomous coding
agent workflows

But the missing layer is:

system memory
historical context
risk awareness
approval boundaries
provenance

As agents gain more ability to act, teams will need systems that answer:

Should this agent be allowed to do this?

Engram is designed for that moment.

7. Why Existing Tools Are Not Enough
Coding assistants

Tools like Cursor, Copilot, Claude Code, and Codex help engineers write or modify code.

They are strong at:

local code understanding
code generation
refactoring assistance

But they are weaker at:

historical system memory
incident-aware reasoning
architectural decision traceability
pre-change risk analysis
cross-artifact context
Enterprise search

Enterprise search tools can find documents.

But search does not equal structured reasoning.

Engram is not trying to index everything.

It is trying to model the relationships that matter before software changes.

Generic RAG systems

RAG systems retrieve relevant text chunks.

Engram goes further by modeling:

entities
relationships
dependencies
decisions
historical failures

This allows the system to reason over structure, not only retrieve similar text.

8. Product Architecture

Engram has four core layers.

8.1 Engineering Knowledge Graph

The graph models the structure of engineering context.

Entities include:

Service
Pull Request
Incident
Decision
Owner
Dependency
Environment

Relationships include:

PR affects Service
Incident caused by Service
Incident related to PR
Decision applies to Service
Service depends on Service
Owner maintains Service
Action touches Environment

The graph becomes the structured memory of the engineering system.

8.2 Semantic Layer

The semantic layer defines what entities mean.

Instead of letting an LLM guess that “Auth” means authentication, the system can define:

Auth Service:
- handles login and session validation
- uses Redis for caching
- owned by Platform Team
- high-risk dependency for Billing and User Profile services

This improves:

consistency
explainability
trust
grounding

The semantic layer is inspired by the idea that AI systems need defined meaning, not just raw text.

8.3 Hybrid Retrieval Layer

Engram combines:

graph traversal
vector search
metadata filtering
semantic grounding

Graph retrieval answers:

What is connected?

Vector retrieval answers:

What is semantically relevant?

Together they create a stronger context layer than either one alone.

8.4 Agentic Orchestration Layer

Engram uses an agentic workflow to decide:

whether to search the graph
whether to run vector retrieval
whether to combine both
whether to classify risk
whether to require human approval

The LLM is not the memory.

The LLM is the reasoning interface over structured memory.

9. Long-Term Product Vision

Engram starts as an engineering context layer, but the long-term product is broader:

an AI control plane for safe engineering work

The full product can include the following capabilities.

9.1 Pre-change Risk Analysis

Before a PR, agent action, or infrastructure change, Engram evaluates:

affected services
related incidents
historical failures
dependency impact
environment sensitivity
ownership
approval requirements

This becomes the core workflow.

9.2 Context Packets for Coding Agents

Engram can generate structured context packets for tools like Cursor, Claude Code, Codex, or other coding agents.

A context packet may include:

relevant files
service ownership
recent incidents
architecture decisions
constraints
test expectations
allowed actions
blocked actions

This makes agents safer and more useful.

9.3 Agent Permission and Approval Layer

Engram can define boundaries around AI-agent actions.

Examples:

read-only allowed
code change allowed
database mutation blocked
production change requires approval
destructive action requires confirmation
infrastructure change requires reviewer

This helps teams safely adopt more autonomous AI workflows.

9.4 Interactive AI Interfaces

Engram can power screen-aware or voice-based assistants.

A Clicky-style interface could act as the user-facing layer:

sees what the engineer is working on
asks Engram for context
explains risk visually or verbally
points to relevant areas
guides onboarding or debugging

In this model:

interactive assistant = interface
Engram = context, memory, and safety layer
9.5 Code-Level Context Integration

Future versions can connect system-level context with code-level dependency graphs.

This would allow Engram to bridge:

architecture decisions
incidents
PR history
actual implementation dependencies

Example:

“This function is part of a code path that was involved in two previous incidents and depends on the cache invalidation strategy defined in ADR-12.”

9.6 Adaptive Retrieval

Engram can improve retrieval quality over time by learning from:

weak answers
missing context
user corrections
false positives
incomplete retrieval

This can move the system toward self-improving context quality.

9.7 Persistent Context Systems

Engram can continuously refine its understanding of engineering systems as they evolve.

Over time, the graph becomes more accurate and valuable as it captures:

new PRs
new incidents
changed ownership
superseded decisions
new dependencies
9.8 Domain Expansion

Although Engram starts with engineering systems, the same architecture can apply to other complex workflows:

support systems
operational workflows
healthcare workflows
product decision tracking
compliance and audit workflows

The common pattern is the same:

fragmented knowledge + important relationships + need for reliable reasoning

10. Moat

Engram’s moat is not the LLM.

The moat is not “graph + vector” alone.

The moat is the structured context layer around engineering work.

Potential moats include:

10.1 Domain-specific engineering schema

Engram models engineering reality directly:

services
incidents
PRs
decisions
dependencies
environments
owners
risky actions

This is more focused than generic enterprise search.

10.2 Accumulated context graph

As teams use Engram, the graph becomes more valuable.

It captures:

system history
recurring failures
decision evolution
ownership patterns
risk patterns

This creates compounding value.

10.3 Workflow placement

Engram is designed to sit before changes happen.

This is important.

It is not just a search tool engineers use when they remember to search.

It becomes part of the workflow:

before agent execution
before PR merge
before risky infrastructure change
during onboarding
during incident review
10.4 Provenance and trust

Every recommendation should point back to source artifacts.

Trust is critical because engineering teams will not rely on black-box AI for risky changes.

Engram should show:

where context came from
why something is considered risky
what evidence supports the answer
10.5 Safety layer for AI agents

As coding agents become more powerful, teams need safety boundaries.

Engram can become the layer that defines:

what agents can access
what they can change
when approval is required
what context they must read first

This becomes increasingly valuable as AI agents move from suggestions to actions.

11. Customers
Initial customers

Fast-moving engineering teams at startups using AI coding tools.

These teams:

move quickly
have growing codebases
often lack perfect documentation
rely on small teams with high context load
want to adopt AI agents without increasing production risk
Buyer

Possible buyers include:

CTO
VP Engineering
Head of Platform
Engineering Manager
AI tooling lead
Users

Daily users include:

software engineers
tech leads
SREs
platform engineers
AI coding agent operators
12. Business Model

Engram can start as a B2B SaaS product.

Possible pricing:

Team plan

For small engineering teams.

priced per seat or per repo
includes GitHub integration
context summaries
risk summaries
basic graph
Startup plan

For growing teams.

multiple repositories
incident and ADR ingestion
team ownership mapping
PR risk checks
Enterprise plan

For larger organizations.

self-hosting
SSO
audit logs
advanced permissions
compliance requirements
custom integrations

The first paid wedge should be simple:

GitHub integration + engineering context/risk summaries before code changes.

13. Go-To-Market

The first audience should be technical founders and engineering teams already using AI coding tools.

Initial channels:

X build-in-public posts
GitHub repository
demo videos
founder/engineering communities
direct outreach to startups
conversations with teams using Cursor, Claude Code, Codex, Devin, or similar tools

The first demo should not be abstract.

It should show:

a service
a proposed change
relevant incidents
related decisions
dependency risk
recommended approval or review path

The product should be immediately understandable in one sentence:

Engram tells AI coding agents what they might break before they change code.

14. MVP Strategy

The MVP should not try to build the full company.

It should prove the core workflow:

before modifying a service, generate relevant context and risk summary.

MVP inputs
sample PRs
sample incidents
sample ADRs
sample services
MVP outputs
service context
related incidents
relevant decisions
structured risk summary
MVP success criteria

The MVP is successful if a user can ask:

What should I know before modifying Auth Service?

And Engram returns a grounded answer using graph + vector retrieval.

15. What Engram Must Avoid

Engram should avoid becoming:

a generic chatbot
a generic enterprise search product
an unfocused knowledge graph platform
a vague AI memory product
a coding assistant competitor
an overbuilt infrastructure project with no clear workflow

The product must stay tied to a clear workflow:

safer engineering changes through structured context.

16. Final Positioning

Engram helps teams safely adopt AI coding agents by giving them structured engineering memory, risk context, and approval boundaries before they touch code or infrastructure.

Short version:

Engram is the pre-change context and safety layer for AI-assisted software engineering.

Even shorter:

Engram tells AI coding agents what they might break before they change code.