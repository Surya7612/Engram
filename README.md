# Engram — Engineering Context Layer

### Agentic AI system for structured engineering memory, semantic grounding, and reliable reasoning

---

## Overview

**Engram** is an agentic AI system that models engineering context as a **knowledge graph with semantic grounding**, enabling **hybrid retrieval (graph + vector)** and **structured reasoning** over system relationships.

It is designed to solve a core problem in engineering teams:

> Critical knowledge about systems (PRs, incidents, decisions, and docs) is fragmented and implicit, making it hard to understand, debug, and evolve systems reliably.

Instead of relying on an LLM to guess meaning from raw text, Engram structures engineering knowledge into explicit entities, relationships, and definitions so responses are more consistent, traceable, and useful.

---

## Problem

Engineering context is spread across:

- Pull Requests
- Incident reports
- Architecture Decision Records (ADRs)
- Documentation

This leads to:

- Slow onboarding
- Repeated mistakes
- Poor system understanding
- Risky changes
- Loss of historical context across teams

LLMs alone are insufficient because they:

- are stateless
- lack structured relationships
- may produce inconsistent answers
- do not preserve system evolution over time

---

## Solution

Engram introduces a **structured memory layer** for engineering systems:

1. Extracts entities such as services, PRs, incidents, and decisions
2. Builds explicit relationships between them
3. Stores structured relationships in a graph database
4. Stores semantic representations for flexible retrieval
5. Uses an agentic workflow to retrieve, combine, and reason over grounded context
6. Applies a semantic layer so the system reasons over defined meaning, not just text similarity

---

## Core Idea

The system is built on a simple principle:

> LLMs should not be the source of truth for engineering knowledge.  
> They should reason over structured context that the system already understands.

Engram’s value comes from combining:

- **Graph structure** for explicit relationships
- **Vector retrieval** for semantic recall
- **Semantic grounding** for consistency
- **Agent orchestration** for reliable query flow

---

## Architecture

### Data flow

```text
Data Sources → Ingestion → Extraction
        ↓
   Graph DB (Neo4j)
        +
   Vector DB (Qdrant)
        ↓
   Semantic Layer
        ↓
   Hybrid Query Engine
        ↓
   Agentic Reasoning (LangGraph)
        ↓
   API (FastAPI)
```

### Data model

**Entities**

- Service
- PR (Pull Request)
- Incident
- Decision (ADR)

**Relationships**

```text
PR → AFFECTS → Service
Incident → CAUSED_BY → Service
Incident → RELATED_TO → PR
Decision → APPLIES_TO → Service
```

### Semantic Layer

A semantic layer sits between storage and reasoning to reduce ambiguity and improve consistency.

Instead of letting the LLM infer meanings from scattered text, Engram can define canonical meanings for engineering entities.

**Example**

- **Service:** Auth Service  
  **Definition:**
  - Handles authentication and session validation
  - Uses Redis for caching
  - Owned by Platform Team

This allows the system to reason over defined engineering meaning, not just approximate language patterns.

**Note:** The current implementation uses lightweight semantic definitions for core entities. A dedicated semantic module with richer schema management and validation is planned in future iterations.

### Example Query

**Query**

> What should I know before modifying auth service?

**Response (example)**

- Auth Service is owned by Platform Team
- Recent incident: Cache inconsistency (INC-45)
- Related PR: PR-123 (TTL fix)
- Decision: Redis caching strategy (ADR-12)

---

## Tech Stack

- Python + FastAPI
- Neo4j (graph database)
- Qdrant (vector database)
- LangGraph (agent orchestration)
- OpenAI / Anthropic (LLM)

---

## Design Decisions

- Graph over relational DB → better fit for relationship-heavy system context
- Hybrid retrieval → combines explicit structure with semantic recall
- Semantic layer → improves consistency and reduces model guessing
- LLM as reasoning layer → not used as long-term memory
- Modular monolith → simpler development now, cleaner path to future decomposition

---

## Scope

This repository represents the MVP layer of Engram.

### MVP focus

- Controlled data ingestion
- Explicit entity and relationship modeling
- Graph + vector retrieval
- Basic semantic grounding
- Queryable engineering context through an agentic workflow

### Not included yet

- Real-time ingestion
- Multi-source enterprise integrations
- Advanced UI
- Production-scale deployment
- Full plug-and-play automation

---

## Use Cases & Positioning

Engram is designed for engineering teams to improve system understanding and reduce context fragmentation.

### Primary use cases

- Understanding service dependencies
- Debugging incidents using historical context
- Tracing architectural decisions
- Accelerating onboarding
- Connecting system changes to operational failures

### Target users

- Software engineers
- Tech leads
- SRE teams
- Platform / infrastructure teams

Engram is not a plug-and-play system in its current form.

It requires structured or semi-structured inputs (PRs, incidents, decisions, docs) to build a reliable knowledge graph. This is intentional: the system prioritizes structured correctness and explainability over full automation in the early phase.

### Plug-and-Play Evolution

Engram is designed with a path toward increasing automation.

**Current state**

- Structured or semi-structured inputs
- Controlled entity definitions
- Explicit relationship modeling
- Manual or predefined ingestion

**Future direction**

Over time, Engram can evolve toward:

- GitHub-native ingestion
- Document parsing across repositories and ADRs
- Broader multi-source connectors
- Reduced setup overhead
- More automated semantic extraction

The goal is to move from a configurable engineering memory system toward a more seamless context layer, without sacrificing reliability.

---

## Future Directions

Engram’s long-term vision goes beyond the MVP.

### Interactive AI interfaces

Engram can act as a context layer for screen-aware or voice-based assistants, enabling real-time context-aware help while engineers work.

### Code-level context integration

Future versions can connect system-level context with code-level dependency graphs to bridge architectural and implementation understanding.

### Adaptive retrieval

The retrieval layer can evolve to improve from weak or incomplete responses over time, enabling more reliable query results.

### Persistent context systems

Engram can support longer-lived memory refinement so engineering context becomes more accurate and useful as systems evolve.

### Domain expansion

Although initially focused on engineering systems, the same architecture can extend to:

- operational workflows
- support systems
- healthcare workflows
- product decision tracking

---

## Running the Project (WIP)

```bash
pip install -r requirements.txt
python main.py
```

---

## Project Structure

```text
engram/
├── ingestion/
├── extraction/
├── graph/
├── vector/
├── query/
├── agent/
├── api/
├── data/
├── docs/
└── main.py
```

---

## Positioning

Engram is a structured engineering memory layer that models systems as a knowledge graph, enabling AI to reason over relationships between services, decisions, and incidents. It transforms fragmented engineering data into consistent, queryable context for reliable system understanding.
