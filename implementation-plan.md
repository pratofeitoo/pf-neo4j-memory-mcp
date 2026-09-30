# Step-by-Step Implementation Plan

**Status:** Initial local synthetic slice implemented through Phase 7; no phase is complete because client integration, acceptance gates, and broader readiness work remain open
**Last updated:** 2026-09-25

## How to use this plan

Each phase states its purpose, work, artifact, and exit criteria. Complete phases in order when their dependencies matter; later phases may be refined as evidence arrives. Record completed work in [build-record.md](build-record.md) and link evidence. A checked box without evidence is not completion. Do not put real client or partner documents into a prototype database before access, retention, and provider decisions are settled.

## Phase 0 — Establish scope and operating constraints

**Current status:** Initial-client, local-deployment, Neo4j/runtime, source intake, embedding permissibility, and initial-format decisions are recorded in [scope-and-constraints.md](scope-and-constraints.md). Retention/privacy and real-data handling are explicitly deferred; this phase remains open for broader/production scope.

### Work

- Confirm first supported agent client(s) and plugin distribution expectations.
- Decide local/single-user vs shared/multi-tenant deployment boundary.
- Identify intended Neo4j host, version, and available APOC/GDS capabilities.
- List candidate source systems and designate the source of truth for every entity and field.
- Define sensitivity classes, document access scopes, retention/deletion rules, audit needs, and embedding-provider restrictions.
- Select a first vertical slice that proves the hardest value: one project, associated tasks and people, multiple clients/partners if applicable, and documents linked to several entities.
- Establish what data may be synthetic and what is prohibited in development.

### Deliverable

`scope-and-constraints.md` or an agreed, dated section in the architecture document.

### Exit criteria

- The first users/clients and deployment boundary are explicit.
- Source-of-truth and permission assumptions are recorded.
- Data handling and embedding constraints are documented.
- The vertical slice and success measures are agreed.

## Phase 1 — Audit the reference implementations

**Current status:** In progress. The public-source evidence pass is recorded in [reference-capability-matrix.md](reference-capability-matrix.md). Source tree, manifests, licenses, selected implementations, release metadata, and test presence were reviewed; upstream projects were not executed locally.

### Work

- Review current source, licenses, dependency manifests, tests, release history, and documented security posture for `neo4j-contrib/mcp-neo4j`, `neo4j/mcp`, and `dpartin/neo4j-mcp`.
- For each candidate capability (Cypher access, memory, modeling, vector/hybrid search, graph analytics, deployment), record whether it is present in code, covered by tests, released, and compatible with the proposed runtime.
- Map any reusable code to its license obligations and attribution requirements. Do not treat README descriptions as validation.
- Run reference tests or focused local experiments only when safe and feasible; record database/version, config, exact command, and result.
- Decide which components to reuse, wrap, or reimplement. Keep the domain schema and policy in the new solution's ownership.

### Deliverable

Reference capability matrix and reuse decision record, linked from the architecture decisions.

### Exit criteria

- No unverified external capability is represented as implemented.
- License and maintenance risks are recorded.
- The implementation path for each must-have capability is selected.

## Phase 2 — Formalize domain vocabulary and graph schema

**Current status:** Initial local synthetic data dictionary and graph diagram created under `schema/`. Cardinalities, source-specific identities, temporal history, and real workflows remain provisional.

### Work

- Convert the candidate entities in [architecture.md](architecture.md) into a concrete data dictionary with required/optional properties, unique keys, lifecycle, and source references.
- Define relationship types, direction, cardinality expectations, roles, and temporal behavior.
- Resolve whether `Claim`/`Fact` is a first-class node in the first release or if selected facts can be represented by sourced, temporal relationships/properties.
- Define workspace isolation and whether every entity/document must belong to one or multiple workspaces.
- Define entity identity resolution: external IDs, aliases, normalization, duplicate detection, merge/unmerge, and ambiguous matches.
- Define document and chunk identity, locators, checksum behavior, and how re-ingestion handles changed source material.
- Produce example graphs for multi-project documents, people with changing roles, partner/client relationships, task history, and contradictory source assertions.
- Review schema with representative workflows; record rejected alternatives and rationale.

### Deliverables

- `schema/data-dictionary.md`
- `schema/graph-model.mmd` or an equivalent visualization
- Synthetic example fixture set
- Accepted schema decision record

### Exit criteria

- Every must-have retrieval question maps to graph patterns.
- Many-to-many document associations and access boundaries are represented.
- Key constraints and migration strategy are defined.
- Ambiguity and conflicting facts have a documented representation.

## Phase 3 — Build the local development foundation

**Current status:** Python package layout, dependency manifest, environment example, and local MCP entrypoint created. The provided Neo4j 2026.09.0 Enterprise instance is reachable; package constraints and indexes were initialized. The local Codex MCP entry is enabled and an initialize/tool-list handshake has succeeded.

### Work

- Select runtime and project layout based on client compatibility and skills/plugin packaging. Avoid choosing by familiarity alone.
- Set up a reproducible local Neo4j development environment with only needed plugins and a synthetic dataset.
- Add configuration validation, secret handling, structured logs, health checks, and database connection lifecycle management.
- Define environment-specific configuration and secret injection. Ensure sample files contain placeholders only.
- Add schema migrations/constraints/index creation and a rollback or recovery approach.
- Establish code formatting, type checks, dependency pinning, and baseline test commands.

### Deliverables

- Runnable dev environment and sample configuration
- Migration/bootstrap commands
- Project setup and operator runbook draft

### Exit criteria

- A fresh setup can start Neo4j and initialize the empty schema from documented steps.
- Synthetic fixtures load reproducibly and safely.
- No secret or real user content is committed.

## Phase 4 — Implement the domain persistence service

**Current status:** Typed persistence and workspace scoping are implemented. In addition to the synthetic fixture, the six-table Airtable pilot exercised current labels, mapped fields and links, and a transactional snapshot refresh in `neo4j` / `airtable-pilot`. Broader identity, authorization, retention, and audit behavior remain open.

### Work

- Implement typed create/read/update operations for workspace, project, task, client, partner, person, document, and relationship records required by the vertical slice.
- Validate fields and relationship types; enforce schema constraints and scoped ownership in service code.
- Add source-system IDs, provenance, recorded times, event/valid times where needed, and review state for inferred links.
- Make upsert/event operations idempotent; test retries and duplicate events.
- Implement explicit task/status history and role changes rather than silently overwriting history where required by scope.
- Add relationship linking, unlinking, and safe correction flows with audit metadata.
- Ensure deletes/retention follow the approved policy and preserve required audit records.

### Deliverables

- Domain service APIs
- Migrations and persistence tests
- Synthetic end-to-end graph fixture

### Exit criteria

- Vertical-slice entities and multi-target document links round-trip correctly.
- Retry and duplicate ingestion tests do not create duplicate records.
- Authorization checks deny out-of-scope writes and reads.
- Changes retain expected provenance and temporal metadata.

## Phase 5 — Implement document ingestion and embedding lifecycle

**Current status:** Initial plain text/Markdown chunking, stable IDs, checksums, locators, embedding metadata, and hosted provider adapter are implemented. A local synthetic feature-hash fixture was stored and retrieved. No hosted embedding request has been made. Changed-content history, robust jobs/retries, and deletion/retention remain open.

### Work

- Select first supported file formats and parsers, with explicit page/section locators and failure reporting.
- Define chunk size/overlap policy and stable chunk IDs; assess documents in supported languages and tables/scans as applicable.
- Integrate one embedding provider behind a provider interface; record model/version/dimensions per embedding.
- Create vector and full-text indexes with configuration compatible with the selected Neo4j version.
- Add ingestion job states, idempotency, retries, cancellation, and partial-failure reporting.
- Add document-to-entity linking from explicit user links and optional extraction. Keep extracted links provisional until policy permits automatic acceptance.
- Define re-embedding and re-chunking strategy when content, model, dimensions, or chunk policy changes.
- Add deletion and re-ingestion tests to ensure stale chunks/embeddings are removed or replaced correctly.

### Deliverables

- Ingestion service and job contract
- Embedding provider interface and initial provider
- Index/migration scripts and ingestion runbook

### Exit criteria

- Re-ingesting identical source material is idempotent.
- Changed source material updates chunks and embeddings without leaving stale searchable data.
- Every chunk result can be traced back to its document and locator.
- Failures are observable and safely retryable.

## Phase 6 — Build retrieval and context assembly

**Current status:** Cypher 25 `SEARCH` with the workspace as an in-index filter, citations/linked-entity metadata, and structured task context lookup were exercised with the synthetic fixture. Query plans and retrieval quality are not evaluated on representative data.

### Work

- Implement exact structured Cypher queries for entity/state questions.
- Implement lexical and vector retrieval, then hybrid retrieval if evaluation shows value or requirement dictates it.
- Implement scoped metadata filters and verify execution behavior on the chosen Neo4j version; benchmark filtered retrieval at realistic scale.
- Add allowlisted, bounded graph expansion patterns for project/task/client/partner/person/document context.
- Add evidence deduplication, citation formatting, status recency, contradictory-source handling, and explicit “unknown/no evidence” outputs.
- Define result size budgets and prevent unbounded traversal or excessive document text from entering the agent context.
- Build a fixed evaluation set of representative requests and expected evidence/context.
- Compare alternatives: vector-only, hybrid, graph-only, and hybrid-plus-graph expansion. Tune only against the evaluation set.

### Deliverables

- Retrieval API and context bundle schema
- Evaluation dataset and repeatable evaluation script/report
- Performance and query plan notes

### Exit criteria

- Exact state questions use structured data rather than vector similarity.
- Semantic questions return relevant chunks plus the correct related graph context.
- Responses carry source locators and provenance.
- Cross-scope retrieval tests show zero leakage.
- Latency and recall meet agreed thresholds on representative data.

## Phase 7 — Expose secure MCP tools

**Current status:** Local stdio MCP tools are implemented for initialization, entity upsert, typed links, text ingestion, semantic search, and task context. The stdio handshake, tool discovery, and one read-only task-context call succeeded through the Keychain-backed Codex launch configuration. No multi-user or network use is supported.

### Work

- Implement the read/retrieval tools from the approved contract first.
- Implement write tools with input validation, idempotency keys, provenance requirements, and clear confirmation boundaries for destructive or broad changes.
- Decide whether writes are available in all environments; keep safe read-only profile configurable and defaulted appropriately.
- Add a privileged/admin path for schema or arbitrary Cypher only if required. Isolate it from normal memory tools and restrict credentials, query type, duration, and audit.
- Return predictable machine-readable shapes, stable error codes, and actionable validation messages.
- Add authorization tests around every tool, including caller-supplied scope forgery and entity reference probing.
- Support only required MCP transports and client protocol versions; test handshake, tool discovery, pagination/large responses as relevant.

### Deliverables

- MCP server, tool schemas, and configuration examples
- Authorization and protocol verification record

### Exit criteria

- Tools expose the approved behavior and enforce scope in the server.
- Read-only mode exposes no write-capable operation.
- Retries are safe for idempotent tools.
- MCP integration tests pass for the first supported client.

## Phase 8 — Author agent skills and workflow guidance

### Work

- Draft skills for project context, task updates, document ingestion, client/partner briefings, and memory quality review, prioritizing skills needed for the initial vertical slice.
- Provide routing cues, tool invocation steps, required identifiers, and expected response/citation behavior.
- Include rules for uncertain identity, conflicting sources, stale facts, missing values, and permission-denied results.
- Keep full schemas/config/error details linked to operator/API docs rather than copying large drifting blocks into each skill.
- Test each skill with representative prompts and inspect tool traces and returned evidence.

### Deliverables

- Versioned skill files and examples
- Skill evaluation notes

### Exit criteria

- Agents choose the intended tools for each evaluated workflow.
- Answers distinguish sourced facts, extracted candidates, and missing evidence.
- Skills do not instruct agents to bypass access or source-of-truth rules.

## Phase 9 — Package as a plugin and document operations

### Work

- Confirm plugin manifest and packaging conventions for each selected client from current official documentation.
- Bundle skills and define how the MCP server is installed, launched, or reached. Keep package files free of credentials.
- Pin or constrain server release versions and declare runtime requirements.
- Document local development, production deployment, secrets, migrations, backup/restore, upgrades, logging, monitoring, and failure recovery.
- Add a setup validator that checks required configuration without exposing secrets.
- Verify installation from a clean environment and ensure the persistent plugin source/distribution path is stable.

### Deliverables

- Installable plugin/package or client-specific packages
- User setup guide and operator runbook
- Versioning and release process

### Exit criteria

- Fresh installation registers expected skills and connects to the intended MCP server.
- The package can be upgraded and rolled back using documented steps.
- No credentials or private sample data are bundled.

## Phase 10 — End-to-end hardening and release readiness

### Work

- Run end-to-end tests for ingest → entity linking → embedding → retrieval → cited answer → update event.
- Conduct security review of tenant isolation, credentials, tool schemas, query construction, prompt-injection handling, logs, deletion, and backups.
- Run load/performance tests at agreed graph/document volume, including filtered vector retrieval and bounded traversal.
- Test outages and recovery: Neo4j unavailable, embedding provider unavailable, partial parse, retries, duplicate callbacks, migration failure, and invalid source IDs.
- Verify backup restore and schema migration on a disposable database.
- Resolve release blockers and label deferred features and limitations explicitly.

### Deliverables

- Release candidate and evidence report
- Threat model and operational readiness checklist
- Versioned documentation and change log

### Exit criteria

- Required evaluation and security checks pass with recorded evidence.
- No known critical data-isolation or destructive-write issue remains.
- Installation, operations, upgrade, backup, and recovery are documented and exercised.
- User approves the scope and limitations of the first release.

## Phase 11 — Operate, evaluate, and evolve

### Work

- Observe retrieval misses, false positives, ambiguous entity links, orphan chunks, stale embeddings, and permission denials using privacy-aware metrics.
- Review extraction/link candidates with humans where confidence is insufficient.
- Re-run evaluation before changing prompts, embedding models, chunk strategy, indexes, schema, or retrieval ranking.
- Add integrations only with explicit source-of-truth and conflict-resolution rules.
- Version migrations and provide re-embedding/reprocessing plans before changing vector dimensions or model families.
- Maintain architecture decisions and append build/operation evidence as the system evolves.

### Exit criteria

- Operational quality measures are reviewed on an agreed cadence.
- Changes to schema, embeddings, and permissions have tested migration paths.
- Deferred work is prioritized based on observed evidence rather than assumed needs.

## Cross-phase quality gates

- **Traceability:** every material memory item can identify its origin and capture/update time.
- **Identity:** duplicate and ambiguous entity resolution behavior is defined and tested.
- **Isolation:** scope filters are enforced in trusted code and covered by negative tests.
- **Temporal integrity:** current and historical views behave as specified.
- **Retrieval:** evaluation uses expected evidence, not subjective sample answers alone.
- **Reliability:** ingestion and writes survive retries without duplication or silent loss.
- **Operations:** secrets, backups, migrations, monitoring, and restore are addressed before production use.
- **Documentation:** user-facing claims match implemented and verified behavior.

## Deferred until evidence justifies them

- Broad free-form Cypher access for general agents.
- Automatic acceptance of extracted relationships or facts.
- Multiple embedding providers or automatic model routing.
- Complex reranking, graph algorithms, or autonomous agent orchestration.
- Bidirectional write-back to project-management source systems.
- Multi-tenant SaaS deployment if an initial local/private workflow meets the need.

Deferral does not mean the feature can never be added; it means the first slice should prove the memory graph and retrieval contract before taking on the extra operational and security cost.
