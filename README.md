# Neo4j Agent Memory Package

**Documentation status:** Design and implementation in progress
**Implementation status:** Codex stdio MCP enabled and handshake/tool lookup verified against local synthetic data; hosted embeddings not verified
**Last reviewed:** 2026-09-25

This directory is the durable project record for designing and building an agent-memory package around Neo4j. It is both a practical implementation plan and the place to record the decisions, evidence, and changes that explain how the delivered solution was built.

## Project objective

Build a reusable package that lets AI agents maintain and retrieve a shared, permission-aware memory of projects, tasks, clients, partners, people, and documents. The memory must represent explicit relationships between entities and support semantic/vector retrieval alongside full-text and graph traversal. An agent should be able to find relevant material and understand the surrounding project context, not merely retrieve an isolated fact or text chunk.

## Current recommendation

Use Neo4j as the graph and vector database. Treat the official Neo4j MCP and Neo4j Labs MCP repositories as implementation references, and the dpartin repository as a reference for its documented analytics and retrieval tools. Do not assume these projects can be merged unchanged or that their README claims establish production readiness. Implement a domain-specific MCP interface and retrieval service, then package reusable agent instructions as skills and the installable pieces as a plugin where the target client supports that distribution model.

The first implementation should favor a small, coherent core: domain schema, provenance-aware writes, tenant/project-scoped retrieval, hybrid vector/full-text search, graph expansion, and a handful of workflow-level MCP tools. Add analytics, ingestion automation, and additional provider integrations only after the core behavior is demonstrated.

## Document map

- [Codex skill](.agents/skills/neo4j-agent-memory/SKILL.md) — when and how to use the bundled memory tools, with source, authorization, and synthetic-data safeguards.
- [Architecture and design](architecture.md) — goals, boundaries, proposed components, graph model, retrieval, tools, security, decisions, and open questions.
- [Step-by-step implementation plan](implementation-plan.md) — ordered phases, deliverables, acceptance criteria, dependencies, and verification gates.
- [Build record](build-record.md) — append-only evidence of what was implemented, changed, tested, and deferred. Planned work must not be reported as completed here.
- [Fresh-session handoff](handoff.md) — execution context and immediate next steps for continuing the plan in a new session.
- [Phase 0 scope and constraints](scope-and-constraints.md) — current safe working boundary, provisional assumptions, and decisions requiring user input.
- [Phase 1 reference capability matrix](reference-capability-matrix.md) — source-backed audit of upstream capabilities, tests, releases, licenses, and reuse risks.
- [Initial data dictionary](schema/data-dictionary.md) and [graph model](schema/graph-model.mmd) — current local synthetic schema contract and limits.

## Current implementation slice

The `src/neo4j_agent_memory/` package contains a local MCP server, scoped Neo4j store, entity/link operations, plain text and Markdown ingestion, OpenAI embeddings behind a provider interface, indexed semantic chunk retrieval with a workspace prefilter, and structured task context lookup. The project-local Codex skill in `.agents/skills/neo4j-agent-memory/` guides agents using these tools. The server is configured for one local Codex user and one configured workspace. It does not yet provide multi-user authorization, document version history, retention/deletion workflows, source-system synchronization, or production operations.

The default embedding model is `text-embedding-3-small` (1536 dimensions). The client is only created when an embedding call is made; initialization and schema creation do not call the embedding provider. Never put an API key in checked-in files. The synthetic demo uses a deterministic feature-hash vector solely to populate and exercise the local retrieval path; its ranking is not a semantic-quality measure and its vectors are tagged with a different model name.

## Local setup (synthetic data only)

1. Start a local Neo4j instance with database `codex-mem-01` available. Set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, and `MEMORY_WORKSPACE_ID` in the process environment. The server and synthetic seed default to `codex-mem-01`; `.env.example` is a reference only and is not auto-loaded.
2. Create a Python virtual environment and install the package with `pip install -e .`.
3. Add `OPENAI_API_KEY` to the environment if semantic ingestion/search is needed. This sends the input text to the configured OpenAI embedding endpoint when those operations are called.
4. Register the local stdio process in Codex MCP configuration using the executable `neo4j-agent-memory`. Use a local-only connection; do not expose it to a network interface. See the official [Codex MCP setup guide](https://developers.openai.com/codex/mcp/) for client configuration syntax. Keep Neo4j credentials in the server process environment, never in checked-in MCP configuration.
5. Call `initialize_memory_schema` once, then create synthetic entities and links, ingest a synthetic `.txt` or `.md` passage, and use `search_memory` or `get_task_context`.

To load the repeatable fictional dataset into `local-development`, run `PYTHONPATH=src python examples/seed_synthetic_demo.py` after dependencies are installed. It uses a local-only deterministic fixture embedder and does not call OpenAI.

The configured Neo4j instance was inventoried read-only as Enterprise `2026.09.0`, with APOC and GDS present and zero graph nodes before setup. Package constraints and indexes were initialized in `codex-mem-01`, which now contains only the cloned fictional demo graph. The local stdio MCP server is enabled in Codex; its initialize/tool-list handshake and read-only synthetic task lookup succeeded. No embedding API request has been made. The local Docker daemon was unavailable during implementation. Retention/privacy policy is explicitly deferred; keep all data synthetic until that work is completed.

## Source repositories and technical references

These links were reviewed for the initial proposal. Their contents can change; verify current source and licensing before implementation or dependency adoption.

- [Neo4j Labs MCP servers](https://github.com/neo4j-contrib/mcp-neo4j) — Cypher, graph memory, Aura management, and data modeling server collection; project describes itself as experimental and without product-team support or compatibility guarantees.
- [Neo4j official MCP server](https://github.com/neo4j/mcp) — schema inspection, read/write Cypher, and GDS procedure discovery.
- [dpartin/neo4j-mcp](https://github.com/dpartin/neo4j-mcp) — documents direct CRUD, graph analytics, GDS projections, and vector/RAG operations. The repository's own production-ready claim is not independent verification.
- [Neo4j GraphRAG for Python](https://neo4j.com/docs/neo4j-graphrag-python/current/) — official vector, hybrid, and graph-augmented retrieval library documentation.
- [Neo4j GraphRAG retrieval guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html) — retriever patterns, filters, graph traversal, and version-specific vector filtering behavior.

## How to maintain these documents

1. Keep architecture choices and rationale in `architecture.md`; label undecided choices as open rather than silently assuming them.
2. Keep ordered work and acceptance checks in `implementation-plan.md`. Update phase status only when evidence exists.
3. Append dated entries to `build-record.md` as implementation proceeds. Link code, commands, test output, and decisions where available. Distinguish verified behavior from claims in documentation.
4. When implementation forces an architecture change, update the architecture decision record and the relevant implementation phase in the same change.
5. Record sensitive-data, access-control, deletion, and migration decisions before loading real client or project data.
