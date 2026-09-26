# Architecture and Design Record

**Status:** Initial local synthetic slice implemented; production architecture remains provisional
**Last updated:** 2026-09-25

## 1. Purpose

Create a graph-backed memory package for agents working across projects and organizations. The system should connect project-management facts with their provenance and supporting documents, while allowing semantic search over document content. It should answer questions such as:

- What is the current state of Project Orion, which tasks are blocked, and who owns them?
- What have we agreed with Client A, which partner or person is responsible, and which source documents support that answer?
- Find the contract clause relevant to this task, then show all related projects, decisions, meetings, and owners.
- What changed about a task or relationship, when did the change become true, and what was the earlier state?

This is a memory and retrieval service, not a project-management system of record. It may mirror or enrich data from source systems, but must retain references to those sources and must not silently claim that its copy is authoritative.

## 2. Design principles

1. **Graph structure is first-class.** Projects, tasks, clients, people, partners, documents, and evidence are typed entities connected by explicit relationships.
2. **Embeddings complement the graph.** Vectors find semantically relevant content; they do not replace IDs, metadata filters, exact queries, or relationship traversal.
3. **Provenance accompanies claims.** Store source references, capture method, timestamps, and confidence or review state where appropriate. Answers should be traceable to the facts or passages that support them.
4. **Time and change are explicit.** Preserve event time and ingestion time. Avoid overwriting important historical states when a claim is superseded.
5. **Scope is enforced before retrieval.** Resolve tenant/workspace, project, and access constraints before any content is returned. Do not rely on the model to filter unauthorized results after retrieval.
6. **Agents use domain operations.** Prefer task- and project-aware tools with validated inputs over broad unrestricted Cypher as the normal interface.
7. **Sources remain authoritative.** Record whether a fact is imported, inferred, proposed, reviewed, or confirmed. A successful ingestion is not proof of correctness.
8. **Build in observable increments.** Begin with a vertical slice and measurable retrieval checks; add capabilities only when their behavior can be verified.
9. **Keep providers swappable.** Embedding, LLM-based extraction, and optional reranking should sit behind interfaces and configuration.

## 3. Proposed package boundaries

### A. Neo4j database layer

Stores typed graph entities, relationships, document chunks, provenance, and vector properties. Defines constraints and indexes. Provides migrations and a development seed dataset containing synthetic examples only.

### B. Domain and ingestion service

Validates domain records, performs idempotent upserts, resolves references, stores source provenance, tracks temporal changes, chunks documents, obtains embeddings, and writes document/entity links. Long-running ingestion is a job with status and retry metadata rather than an opaque MCP call.

### C. Retrieval service

Combines structured filters, vector or hybrid candidate retrieval, and bounded graph expansion. Produces a stable context bundle with source citations, relevant entities/relationships, timestamps, and explicit uncertainty or missing data.

### D. MCP server

Exposes typed, permission-aware operations to clients. It should be possible to run the server over the transports needed by the chosen client and deployment, but transport scope is a later decision. MCP tools call the service layer; they do not contain all database logic themselves.

### E. Agent skills

Provide concise operational instructions for when and how agents should call the tools. Skills should describe workflows and interpretation rules, not duplicate the full API schema or secrets/configuration.

### F. Plugin / distribution package

Bundles or references the MCP server and skills using the target host's supported packaging mechanism. Plugin packaging is an install/discovery layer; the server remains usable independently. Avoid hard-coupling the memory core to one agent client.

### G. Operator documentation

Explains installation, configuration, authorization, backups, migrations, observability, incident handling, retention, and source-system synchronization.

## 4. Logical graph model

The exact labels and properties must be checked against real workflows before the first schema migration. Initial candidate entities:

| Entity | Candidate key fields | Notes |
|---|---|---|
| `Workspace` | `id`, `name`, `created_at` | Top-level isolation and configuration boundary. Could represent a tenant or organization depending on deployment. |
| `Project` | `id`, `name`, `status`, `summary`, `source_ref` | A project can relate to multiple clients, partners, people, tasks, and documents. |
| `Task` | `id`, `title`, `status`, `priority`, `due_at`, `source_ref` | Status history and ownership should be represented explicitly where needed. |
| `Client` | `id`, `name`, `external_ref` | Client identity may need alias and duplicate-resolution rules. |
| `Partner` | `id`, `name`, `external_ref` | Keep distinct from clients and people; one organization may have multiple roles only if explicitly modeled. |
| `Person` | `id`, `display_name`, `external_ref` | Model roles through relationships or scoped role records instead of assuming one fixed role. |
| `Document` | `id`, `title`, `mime_type`, `source_uri`, `checksum`, `modified_at` | Store metadata and access scope; source file may stay in its system of record. |
| `DocumentChunk` | `id`, `ordinal`, `text`, `token_count`, `embedding`, `embedding_model` | Chunk granularity supports retrieval and citations; do not duplicate whole documents without a retention decision. |
| `Claim` / `Fact` | `id`, `predicate`, `value`, `valid_from`, `valid_to`, `recorded_at`, `confidence`, `review_state` | Optional explicit assertion layer for conflicting, temporal, or source-sensitive facts. Decide during modeling spike whether ordinary relationships suffice for the first release. |
| `Source` | `id`, `system`, `external_id`, `uri`, `captured_at` | May be represented as source properties/relationships initially. Preserve external IDs to support sync and audit. |

Candidate relationships include `(:Workspace)-[:CONTAINS]->(:Project)`, `(:Project)-[:HAS_TASK]->(:Task)`, `(:Project)-[:FOR_CLIENT]->(:Client)`, `(:Project)-[:WITH_PARTNER]->(:Partner)`, `(:Person)-[:OWNS|ASSIGNED_TO|PARTICIPATES_IN]->(:Task|Project)`, `(:Document)-[:RELATES_TO]->(:Project|Task|Client|Partner|Person)`, `(:Document)-[:HAS_CHUNK]->(:DocumentChunk)`, `(:DocumentChunk)-[:MENTIONS]->(:Entity)`, and provenance edges such as `(:Claim)-[:SUPPORTED_BY]->(:DocumentChunk|Source)`.

This is a candidate vocabulary, not an approved schema. Relationship direction, cardinality, uniqueness, temporal semantics, ownership, and authorization must be made explicit in the schema design phase. Avoid generic untyped `RELATED_TO` edges where a meaningful relationship type is known.

### Relationship and document semantics

- A document may relate to many projects, tasks, clients, partners, and people. The graph should support this naturally through multiple typed edges.
- A project may have several clients/partners or a single primary client plus many related parties; confirm cardinality and role semantics before encoding constraints.
- A person can participate in multiple contexts with different roles. A role should carry context and dates when it changes.
- Document-to-entity edges should include linking provenance such as extracted, user-linked, or imported, with confidence/review status for machine-inferred links.
- A chunk should point to its parent document and retain a locator (page, section, paragraph, timestamp, or source-specific offset) to make answers citable.

## 5. Embedding and retrieval design

### Ingestion pipeline

1. Receive a file, URL, source-system record, or user-provided note with workspace and access metadata.
2. Validate type, size, source, and authorization; compute a stable content checksum and external/source ID.
3. Upsert the document idempotently. A repeated source/checksum should not create duplicate document or chunk nodes.
4. Extract text with a format-aware parser and keep extraction metadata, errors, and page/section locators.
5. Chunk by semantic boundaries with configurable size/overlap; preserve stable chunk IDs so unchanged content does not churn graph identity.
6. Generate embeddings using a configured provider/model. Store model name, dimensions, version, and generation time with each vector.
7. Extract candidate entities/relationships if enabled. Normalize aliases, link to existing entities where confidence is adequate, and route ambiguous matches for review.
8. Create document-to-entity links with evidence and review state. Do not turn speculative extraction directly into trusted project truth.
9. Update vector/full-text indexes and mark the job complete with counts, warnings, and source references.

### Retrieval pipeline

1. Authenticate the caller and resolve its workspace/tenant and allowed project/client scopes.
2. Parse intent into explicit filters when possible: project IDs, client IDs, status/time ranges, document types, entities, and recency.
3. Run exact structured lookup for IDs/status/ownership questions; use semantic or hybrid retrieval for meaning-based questions. Do not use vectors for exact state queries when a graph query is appropriate.
4. Apply access and metadata filters before material reaches the model. Verify the selected Neo4j version and vector index configuration for efficient in-index filtering; older paths may have different performance characteristics.
5. Retrieve top candidates and expand through bounded, allowlisted graph patterns (e.g. chunk → document → project/task/client/person). Set limits on depth, rows, text length, and time.
6. Deduplicate and rank evidence, favoring current/reviewed/source-backed claims where appropriate. Preserve conflicting evidence rather than choosing silently.
7. Return a compact context bundle with entity IDs, current status, relationships, citations/locators, source timestamps, provenance, and uncertainty. Include “no evidence found” distinctly from “entity does not exist.”
8. Log retrieval metadata without logging sensitive document text unnecessarily.

### Search strategy

- **Structured Cypher:** canonical for exact IDs, project/task status, ownership, and relationship queries.
- **Full-text search:** useful for names, identifiers, titles, and exact phrases.
- **Vector search:** useful for semantically similar chunks and paraphrased questions.
- **Hybrid search:** combine full-text and vector candidates when both lexical terms and semantic similarity matter.
- **Graph-augmented retrieval:** expand matching chunks/entities along allowlisted relationships to return relevant surrounding context.
- **Optional reranking:** evaluate only after the baseline retrieval test set reveals ranking errors that can be improved.

Neo4j GraphRAG for Python documents vector, hybrid, and Cypher-augmented retrievers. On Neo4j 2026.01+, compatible vector filters can use the `SEARCH` clause and in-index filtering when index filterable properties are configured. On earlier versions, some filtered queries may fall back to exact/brute-force behavior; benchmark realistic data and filters before selecting a version. See the official [GraphRAG user guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html).

## 6. Initial MCP tool contract

The names are proposals. Final JSON schemas should be precise, typed, bounded, and versioned.

### Read and retrieval tools

- `search_memory(query, workspace_id, project_ids?, client_ids?, entity_types?, time_range?, limit?)` — hybrid or vector search with scope filters; returns evidence and graph context.
- `get_project_context(project_id, include_tasks?, include_people?, include_documents?, as_of?)` — structured project context with related parties, tasks, and cited documents.
- `get_entity(entity_type, entity_id, expand?, as_of?)` — fetch an entity and explicitly bounded relationship neighborhoods.
- `get_task_context(task_id, include_related_docs?, include_project_context?)` — task state, owners, blockers, linked docs, and provenance.
- `find_related_documents(entity_refs, query?, limit?)` — retrieve documents related through explicit edges and optionally semantic similarity.
- `list_recent_changes(scope, since, entity_types?, limit?)` — summarize recorded changes with source/time metadata.

### Write tools

- `record_memory_event(event, source, scope, idempotency_key)` — append a sourced event or update; validate and preserve time/provenance.
- `upsert_project`, `upsert_task`, `upsert_party` — validated, source-aware operations with explicit external IDs and idempotency.
- `link_entities(from_ref, relationship_type, to_ref, evidence?, valid_from?, valid_to?)` — create typed and scoped relationship with provenance.
- `ingest_document(source_ref, metadata, scope, options?)` — enqueue or execute the document ingestion pipeline and return job state.
- `review_extracted_links(document_id, decisions)` — approve/reject proposed machine-created entity links.

### Administrative tools

- `get_ingestion_job(job_id)` and `retry_ingestion_job(job_id)` with permission checks.
- Health/status and schema version should preferably be exposed through deployment health endpoints or resources, not noisy agent-facing tools unless there is a clear need.
- Free-form Cypher, if exposed at all, should be a separate explicitly privileged development/admin capability with read-only default, database-level restricted credentials, audit records, timeouts, and query limits.

## 7. Skills and plugin behavior

Candidate skills:

1. **Project context retrieval:** assemble project, task, people, client, partner, and document context with source citations.
2. **Task/milestone update:** verify target identity and source, record a change idempotently, preserve status history, and report what changed.
3. **Document memory ingestion:** check access scope, ingest, resolve candidate entities, and request review on ambiguous links.
4. **Client/partner briefing:** retrieve only authorized history, agreements, open work, risks, and supporting evidence.
5. **Memory quality review:** detect orphaned documents, duplicate entities, stale embeddings, unresolved links, and contradictory claims.

Skills instruct agents to cite retrieved sources, treat extracted links as provisional until confirmed where policy requires, avoid making up missing dates/owners/status, and ask for clarification when entity identity is ambiguous. Tool schemas and configuration remain in server docs to avoid drift.

The plugin should declare compatible client requirements, install/configure skills, and point to a versioned server command or service. Never include credentials in the plugin manifest or checked-in config. A registered plugin or MCP entry is not operational proof; deployment verification must confirm handshake, tool listing, authorized reads, denied cross-scope reads, and a representative query/write flow.

## 8. Security, privacy, and reliability

- Define whether workspaces are separate customers, internal teams, or both; enforce tenant boundaries in the service layer and preferably reinforce them through database/query design.
- Use least-privilege database users. Separate read and write credentials when practical; production agents should not receive broad database-admin privileges.
- Apply authorization filters in trusted server code. The LLM must not choose or override the caller's access scope.
- Validate tool inputs and allowlist relationship types and traversal patterns. Parameterize Cypher values; carefully validate any dynamic labels/property keys.
- Use read-only defaults for exploration and separate explicit write scopes. Require idempotency for repeatable ingestion and event writes.
- Treat uploaded documents, extracted entities, and external source responses as untrusted data, never as instructions for the agent or server.
- Encrypt secrets and connections, avoid logging credentials or document contents, and define retention, deletion, backups, and restore procedures before real-data launch.
- Design for retries, partial failures, embedding-provider outages, Neo4j outages, rate limits, and duplicate source events. Surface job state and actionable errors.
- Record audit metadata for who/what performed writes, through which tool, source reference, request correlation ID, and time. Minimize sensitive payload capture.
- Test prompt-injection documents, cross-tenant queries, ambiguous entity names, malformed embeddings, huge traversals, and write retries.

## 9. Evaluation criteria

Create a labeled, synthetic evaluation set before tuning. Include questions covering exact state, semantic document search, relationship expansion, temporal changes, ambiguous names, duplicates, missing facts, and access-denied cases.

Measure:

- Retrieval recall for relevant documents/entities and precision of returned evidence.
- Correctness of structured status/owner answers.
- Citation coverage: factual answer statements link to source document/chunk or source-system record.
- Scope leakage: must be zero in authorization tests.
- Temporal correctness: current and historical questions distinguish event time and ingestion time.
- Duplicate rate under repeated ingestion and retry scenarios.
- Latency and query cost on representative graph size and realistic metadata filters.
- Ingestion success, extraction/link review rates, embedding error/retry rates, and orphan rates.
- Agent behavior: tools called appropriately, unsafe generic Cypher avoided, uncertainty stated when evidence is insufficient.

Do not describe the system as “smooth” or production-ready based on a successful MCP handshake alone. Require repeatable retrieval and access-control evidence.

## 10. Decision record

### ADR-000 — First implementation scope

- **Status:** Accepted by user for the initial slice on 2026-09-25
- **Decision:** Support Codex first, run locally for one user, target the user's latest Neo4j with APOC and GDS available, receive source details directly from the user as needed, permit hosted embeddings, and begin with mostly text files. Retention/privacy policy is deferred by user direction.
- **Consequences:** The initial server reads its workspace from trusted process configuration and has no multi-user authentication. The first document parsers are plain text and Markdown. Hosted embedding code is present but is called only when the user configures credentials and invokes ingestion/search. Real data remains out of scope until retention, deletion, and access policy are defined.

### ADR-001 — Build a domain-aware memory layer on Neo4j

- **Status:** Proposed
- **Decision:** Use Neo4j as graph/vector storage; keep MCP as the agent-facing protocol boundary; build domain-aware service operations and retrieval rather than treating a general-purpose Cypher MCP as the full memory system.
- **Context:** The desired use includes many-to-many entities, cross-linked documents, project/task workflows, and vector retrieval. The reviewed repositories offer useful pieces but do not establish the entire integrated behavior.
- **Consequences:** More implementation than adopting one MCP unchanged; stronger control over schema, authorization, provenance, and retrieval behavior.

### ADR-002 — Prefer capability composition to direct repository merging

- **Status:** Proposed
- **Decision:** Reuse repository concepts and any suitable code only after source/license review and component-level assessment. Keep the new implementation's domain service independent of MCP transport.
- **Context:** The Labs project contains several focused servers and identifies experimental/support limitations; dpartin documents a wider tool set but its capability claims have not been independently verified.
- **Consequences:** Avoids inheriting unclear coupling; requires the plan to include parity checks before borrowing or replacing a feature.

### ADR-003 — Combine embeddings with typed relations and filters

- **Status:** Proposed
- **Decision:** Store embeddings on document chunks and use hybrid/vector retrieval followed by bounded graph expansion and metadata/access filtering.
- **Context:** Similarity alone cannot enforce project/client scope or reliably answer exact status and ownership questions.
- **Consequences:** Requires chunking, indexing, version metadata, relationship extraction/review, and evaluation fixtures.

### ADR-004 — Use the configured local workspace as the first access boundary

- **Status:** Accepted for local single-user development only
- **Decision:** MCP tools do not accept a workspace ID; trusted server configuration supplies one workspace ID, and every store query binds to it. This does not claim to solve authorization for multiple users or remote clients.
- **Consequences:** A network-facing/shared deployment must add authenticated identity, server-derived project permissions, negative authorization tests, and deployment hardening before use.

### ADR-005 — Use workspace-filtered indexed vector search

- **Status:** Implemented for the selected Neo4j release; result quality and performance not evaluated
- **Decision:** Use Cypher 25 `SEARCH` with `workspace_id` configured as an in-index filter property, then require the configured embedding model on returned candidates.
- **Consequences:** Workspace scope is applied by the vector index before candidate content is matched. Model filtering occurs after the index candidate limit, so the implementation oversamples. A multi-model production workload still needs evaluation.

## 11. Remaining decisions before broader or real-data use

1. Retention, deletion, backup, audit, and privacy/compliance requirements remain explicitly deferred. Do not ingest real client, partner, or personal data until these are defined.
2. The user will provide source systems and workflows as needed. Connector direction, source-of-truth rules, conflict handling, and write-back permissions remain unselected.
3. Hosted embeddings are permitted, but the provider/model choice is not confirmed as a product decision. The optional OpenAI adapter and `text-embedding-3-small` default are implementation defaults only; no hosted request has been made.
4. Initial content is mostly text files; only plain text and Markdown are implemented. Volumes, languages, update rates, and other formats remain open.
5. Local Codex is the first client and one configured workspace is the current boundary. Codex registration/handshake is not yet verified; shared access, authenticated multi-user identity, and project-level permissions are unsupported.
6. Document revision history, retention automation, source synchronization, and migration/backup operations are future design gates.

Continue synthetic-only implementation for reversible work. Do not treat these deferred items as approved for production or real-data use.
