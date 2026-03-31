# Engram — Engineering Context Layer

### Agentic AI system for structured engineering memory and reasoning

---

## Overview

**Engram** is an agentic AI system that models engineering context as a **knowledge graph**, enabling **hybrid retrieval (graph + vector)** and **structured reasoning** over system relationships.

It is designed to solve a core problem in engineering teams:

> Critical knowledge about systems (PRs, incidents, decisions) is fragmented and implicit, making it hard to understand, debug, and evolve systems reliably.

---

## Problem

Engineering context is spread across:

* Pull Requests
* Incident reports
* Architecture Decision Records (ADRs)
* Documentation

This leads to:

* Slow onboarding
* Repeated mistakes
* Poor system understanding
* Risky changes

LLMs alone are insufficient because they:

* are stateless
* lack structured relationships
* may produce inconsistent answers

---

## Solution

Engram introduces a **structured memory layer** for engineering systems:

1. Extracts entities (services, PRs, incidents, decisions)
2. Builds explicit relationships between them
3. Stores them in a graph database
4. Combines graph traversal + semantic search
5. Uses an agentic workflow to generate grounded responses

---

## Architecture

```text
Data Sources → Ingestion → Extraction
        ↓
   Graph DB (Neo4j)
        +
   Vector DB (Qdrant)
        ↓
   Hybrid Query Engine
        ↓
   Agentic Reasoning (LangGraph)
        ↓
   API (FastAPI)
```

---

## Data Model

### Entities

* Service
* PR (Pull Request)
* Incident
* Decision (ADR)

### Relationships

* PR → AFFECTS → Service
* Incident → CAUSED_BY → Service
* Incident → RELATED_TO → PR
* Decision → APPLIES_TO → Service

---

## Example Query

**Query:**

```
What should I know before modifying auth service?
```

**Response (example):**

```
- Auth Service is owned by Platform Team
- Recent incident: Cache inconsistency (INC-45)
- Related PR: PR-123 (TTL fix)
- Decision: Redis caching strategy (ADR-12)
```

---

## Tech Stack

* Python + FastAPI
* Neo4j (graph database)
* Qdrant (vector database)
* LangGraph (agent orchestration)
* OpenAI / Anthropic (LLM)

---

## Design Decisions

* **Graph over relational DB** → efficient relationship traversal
* **Hybrid retrieval** → combines structure + semantics
* **LLM as reasoning layer** → not used for storage
* **Modular monolith** → simpler development, scalable later

---

## Scope

This is an MVP focused on:

* controlled data ingestion
* explicit relationship modeling
* queryable system context

Not included (yet):

* real-time ingestion
* multi-source enterprise integrations
* production-scale deployment

---

## 🚀 Running the Project (WIP)

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
