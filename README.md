# Neo4j Agent Memory Package

**Documentation status:** Design and implementation in progress
**Implementation status:** Codex stdio MCP and local Ollama embedding path verified; 66 current Airtable pilot records indexed in `neo4j` / `airtable-pilot` with 66 cited chunks
**Last reviewed:** 2026-09-30

This directory is the durable project record for designing and building an agent-memory package around Neo4j. It is both a practical implementation plan and the place to record the decisions, evidence, and changes that explain how the delivered solution was built.

## Project objective

Build a reusable package that lets AI agents maintain and retrieve a shared, permission-aware memory of projects, tasks, clients, partners, people, and documents. The memory must represent explicit relationships between entities and support semantic/vector retrieval alongside full-text and graph traversal. An agent should be able to find relevant material and understand the surrounding project context, not merely retrieve an isolated fact or text chunk.

## Current recommendation

Use Neo4j as the graph and vector database. Treat the official Neo4j MCP and Neo4j Labs MCP repositories as implementation references, and the dpartin repository as a reference for its documented analytics and retrieval tools. Do not assume these projects can be merged unchanged or that their README claims establish production readiness. Implement a domain-specific MCP interface and retrieval service, then package reusable agent instructions as skills and the installable pieces as a plugin where the target client supports that distribution model.

The first implementation should favor a small, coherent core: domain schema, provenance-aware writes, tenant/project-scoped retrieval, hybrid vector/full-text search, graph expansion, and a handful of workflow-level MCP tools. Add analytics, ingestion automation, and additional provider integrations only after the core behavior is demonstrated.

## Document map

- [Current Airtable mapping](schema/airtable-mapping.md) — source labels, field IDs, compatibility migration, and preserved snapshot boundaries.

- [Codex skill](.agents/skills/neo4j-agent-memory/SKILL.md) — when and how to use the bundled memory tools, with source, authorization, and synthetic-data safeguards.
- [Real-data pilot readiness](real-data-pilot.md) — target database, observed state, unresolved handling decisions, and pre-ingestion gates.
- [Architecture and design](architecture.md) — goals, boundaries, proposed components, graph model, retrieval, tools, security, decisions, and open questions.
- [Step-by-step implementation plan](implementation-plan.md) — ordered phases, deliverables, acceptance criteria, dependencies, and verification gates.
- [Build record](build-record.md) — append-only evidence of what was implemented, changed, tested, and deferred. Planned work must not be reported as completed here.
- [Fresh-session handoff](handoff.md) — execution context and immediate next steps for continuing the plan in a new session.
- [Phase 0 scope and constraints](scope-and-constraints.md) — current safe working boundary, provisional assumptions, and decisions requiring user input.
- [Phase 1 reference capability matrix](reference-capability-matrix.md) — source-backed audit of upstream capabilities, tests, releases, licenses, and reuse risks.
- [Initial data dictionary](schema/data-dictionary.md) and [graph model](schema/graph-model.mmd) — current local synthetic schema contract and limits.

## Current implementation slice

The `src/neo4j_agent_memory/` package contains a local MCP server, scoped Neo4j store, typed entity/link operations (including project leadership and subtasks), plain text and Markdown ingestion, local Ollama and optional OpenAI embeddings behind a provider interface, indexed semantic chunk retrieval with a workspace prefilter, and structured task context lookup including project leads, members, and subtasks. The project-local Codex skill in `.agents/skills/neo4j-agent-memory/` guides agents using these tools. The server is configured for one local Codex user and one configured workspace. It does not yet provide multi-user authorization, document version history, retention/deletion workflows, source-system synchronization, or production operations.

The local embedding configuration uses `nomic-embed-text:latest` (768 dimensions) through Ollama. Document and query embeddings use `search_document:` and `search_query:` prefixes. The full model digest is checked on every embedding call and included in the stored model identity; a changed `latest` tag fails until reviewed. Ollama is not called during server startup or schema creation. OpenAI remains an optional hosted provider selected explicitly. Never put an API key in checked-in files. The synthetic demo uses a deterministic feature-hash vector solely to populate and exercise the local retrieval path; its ranking is not a semantic-quality measure and its vectors are tagged with a different model name.

## Local setup and synthetic verification

1. Start the local Neo4j instance and select database `neo4j` / workspace `airtable-pilot` for the pilot. Set `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, and `MEMORY_WORKSPACE_ID` in the process environment. `.env.example` is a reference only and is not auto-loaded. The separate synthetic seed still defaults to `codex-mem-01` / `local-development`.
2. Create a Python virtual environment and install the package with `pip install -e .`.
3. Start Ollama locally and install `nomic-embed-text:latest`. Set `MEMORY_EMBEDDING_PROVIDER=ollama`, `MEMORY_EMBEDDING_MODEL=nomic-embed-text:latest`, `MEMORY_EMBEDDING_DIMENSIONS=768`, `MEMORY_OLLAMA_URL=http://127.0.0.1:11434`, and `MEMORY_OLLAMA_MODEL_DIGEST` to the full digest from `/api/tags`. This sends text only to the local Ollama process. The optional OpenAI provider requires `MEMORY_EMBEDDING_PROVIDER=openai`, its model/dimension settings, and `OPENAI_API_KEY`.
4. Register the local stdio process in Codex MCP configuration using the executable `neo4j-agent-memory`. Use a local-only connection; do not expose it to a network interface. See the official [Codex MCP setup guide](https://developers.openai.com/codex/mcp/) for client configuration syntax. Keep Neo4j credentials in the server process environment, never in checked-in MCP configuration.
5. Inspect the target database's `DocumentChunk` count and vector index. `examples/migrate_vector_index.py --database neo4j --dimensions 768` reports both without changes. After checking the target is empty of chunks, run it with `--apply` to replace the old 1536-dimensional index. The script refuses to replace an index when any chunks exist. Then call `initialize_memory_schema`, ingest a synthetic `.txt` or `.md` passage, and use `search_memory` or `get_task_context`.

To load the repeatable fictional dataset into `local-development`, run `PYTHONPATH=src python examples/seed_synthetic_demo.py` after dependencies are installed. It uses a local-only deterministic fixture embedder and does not call OpenAI.

For a live synthetic Ollama check against the configured database, run `PYTHONPATH=src python examples/verify_ollama_integration.py` with the Neo4j and Ollama environment values above. It creates a unique temporary workspace, checks cited semantic retrieval and scope isolation, and removes the test nodes. Check the database is reachable first. The script does not index the Airtable snapshot.

To index the current Airtable pilot snapshot, set the same local Neo4j and Ollama environment values, then run `PYTHONPATH=src python examples/index_airtable_pilot.py` for a dry run. Add `--apply` to create a private pre-write export and index current Setores, Tasks, Subtasks, Meetings, and Documents. Each indexed record becomes a derived `Document` with a source ID and `airtable://` locator, one `RELATES_TO` link to the original graph entity, and one or more cited chunks. The first apply indexed 9 Setores, 16 Tasks, 30 Subtasks, 9 Meetings, and 2 Documents (66 chunks). Team names, the retained task absent from the current snapshot, attachment bytes and metadata, URLs outside the selected text fields, and exact status/date fields are excluded from vector text. Structured graph records remain available for exact status and ownership questions. The importer is repeatable for current IDs and changed text; if an indexed source disappears from a later snapshot it stops for an explicit retention decision rather than leaving stale search results unnoticed.

If Ollama is stopped, `search_memory` and `ingest_text_document` fail at the embedding call; structured tools such as `get_task_context` remain available. If `nomic-embed-text:latest` changes digest, embedding calls fail until the new model is reviewed and `MEMORY_OLLAMA_MODEL_DIGEST` is updated. Existing vectors from the previous digest must be re-embedded before searching with the new digest. A change in vector dimensions also requires a reviewed index migration; the included migration script refuses replacement while any `DocumentChunk` nodes exist. The current package does not yet provide a general backfill or document-version retention workflow.

The configured Neo4j instance was inventoried as Enterprise `2026.09.0`, with APOC and GDS present. `codex-mem-01` contains the cloned fictional demo graph. The separate `neo4j` database contains the user-approved Airtable snapshot and 66 derived indexed documents in workspace `airtable-pilot`; details and limits are in [real-data-pilot.md](real-data-pilot.md). The global Codex stdio MCP entry is configured for `neo4j` / `airtable-pilot`, and the skill is installed in the local user's global Codex skills directory as well as this repository. This makes it available across local projects using this macOS account, not remote/cloud Codex environments. No attachment content was processed. Retention/privacy policy is not generally defined, so the pilot remains limited to approved structured fields and local use only.

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
