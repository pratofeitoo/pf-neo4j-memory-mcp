# Build Record

This is an append-only implementation record. Add dated entries as work is performed. Preserve earlier entries; correct mistakes with a clearly labeled follow-up. Link commits, artifacts, test output, decisions, and deployment evidence. Do not copy planned work into the completed section.

## 2026-09-25 — Initial plan authored

### Status

- **Design:** Proposed, not yet approved or implemented.
- **Runtime/deployment:** Undecided.
- **Schema:** Candidate vocabulary only; no migrations created.
- **MCP server/plugin/skills:** Not built.
- **Database or live integration:** Not configured or verified.

### User need captured

The target is persistent agent memory for complex project work: projects, tasks, multiple clients and partners, people, and documents associated with several entities at once, with vector embeddings and practical retrieval. The user requested an extensive step-by-step plan that will also document how the solution is eventually built.

### Initial technical review

- Reviewed [Neo4j Labs MCP collection](https://github.com/neo4j-contrib/mcp-neo4j), which documents separate Cypher, memory, Aura management, and data-modeling servers; collection documentation marks the Labs projects experimental and without product-team support/compatibility guarantees.
- Reviewed [dpartin/neo4j-mcp](https://github.com/dpartin/neo4j-mcp), whose README documents CRUD, graph analytics, GDS projections, and vector/RAG tools. Its production-ready language is treated as the repository's claim, not independent validation.
- Reviewed [Neo4j GraphRAG Python docs](https://neo4j.com/docs/neo4j-graphrag-python/current/) and [retrieval guide](https://neo4j.com/docs/neo4j-graphrag-python/current/user_guide_rag.html) for vector, hybrid, and graph-augmented retrieval and version-specific filtering notes.
- No repositories were cloned, code was not executed, no tests were run, and no implementation capability was independently verified in this planning stage.

### Decisions proposed

- Keep Neo4j as the graph/vector persistence layer and put a domain-aware service between it and the MCP tools.
- Use hybrid retrieval plus bounded graph expansion, with access filtering enforced before context reaches the agent.
- Package the MCP server, skills, and client plugin together where the supported host permits, while keeping the service usable outside the plugin.
- Record provenance, source IDs, review state, and time semantics so memory results remain auditable.

### Open work

Proceed with Phase 0 scope decisions and Phase 1 source/license/code audit in [implementation-plan.md](implementation-plan.md). Review the candidate model and open questions in [architecture.md](architecture.md) before freezing schema or selecting hosting, embedding provider, or client packaging.

## 2026-09-25 — Fresh-session execution handoff added

### Change

- Added [handoff.md](handoff.md) with the user goal, agreed working direction, current no-implementation state, first-read file order, Phase 0/1 next actions, safety and evidence requirements, a first-slice completion definition, and a reusable prompt for a new session.
- Updated [README.md](README.md) to include the handoff in the document map.

### Status and limits

- This is a documentation handoff only. It did not start Phase 0 or Phase 1, inspect new upstream source code, create a scope artifact, run tests, or implement the package.
- The next session should verify the current workspace and upstream state before acting.

## 2026-09-25 — Phase 0/1 execution started

### Workspace evidence

- Confirmed `/Users/paulorezende/Library/Mobile Documents/com~apple~CloudDocs/AI/Agentic /AI Agents/Codex/neo4j-agent-memory/` is a standalone documentation folder, not a Git checkout. `git status --short --branch` from the workspace root returned `fatal: not a git repository`; no project files were changed before this entry.
- Re-read `README.md`, `architecture.md`, `implementation-plan.md`, `build-record.md`, and `handoff.md` before editing.

### Phase 0 artifact

- Created [scope-and-constraints.md](scope-and-constraints.md).
- Recorded a synthetic-only, local/private, MCP-independent provisional boundary so non-dependent work can continue safely.
- Listed the material user decisions still open: first client/package, deployment boundary, Neo4j host/version/plugins, source systems, sensitivity/embedding policy, document formats/volume, and retention/deletion/audit requirements.
- Phase 0 is in progress, not complete; provisional assumptions are not user approval.

### Phase 1 evidence

- Created [reference-capability-matrix.md](reference-capability-matrix.md).
- Reviewed public repository metadata, main-branch commit IDs, release endpoints, manifests, licenses, security file, README/source excerpts, workflow/test trees, and official GraphRAG documentation for the three named repositories and the official GraphRAG reference.
- Current evidence: Labs main `1c7ad0793b5f06b42b9c44f855c23eb2064c3bb7`; official main `2630d620eb98029835eff65052cbd9a8da220af7`; dpartin main `7abe02c75610268904c8e16026423e7251c2cdef`. The matrix records current release/license/test/security evidence and links the public sources.
- No upstream repository was cloned, installed, copied, or executed. No upstream test result is claimed as locally verified.
- Initial reuse direction: official MCP and Labs MCP are references for protocol/packaging patterns; official GraphRAG is the leading retrieval-library candidate pending runtime/version/provider decisions; dpartin is reference-only pending security redesign.

### Commands and limitations

- Local inspection: `pwd`, `rg --files ...`, `git status --short --branch`, `sed`, and `wc` in the project folder. Expected result was a standalone documentation set; observed result matched.
- Upstream inspection: read-only GitHub API queries for repository metadata, tree contents, selected file contents, release endpoints, and branch commit IDs; official Neo4j GraphRAG documentation reviewed through the web source. Expected result was source evidence without local execution; observed result matched.
- First sandboxed GitHub API attempt failed with DNS resolution; the same read-only query was then rerun with explicit network authorization and completed. No repository state was changed.
- The audit remains incomplete for local reproduction, dependency-lock/license graph, and runtime compatibility because no checkout or installation has been authorized or performed.

## 2026-09-25 — Local synthetic vertical slice implemented

### Scope decisions recorded

- User selected Codex first and local deployment for the initial slice; specified latest Neo4j with APOC and GDS available; will provide source-system context directly as needed; permits hosted embeddings; described initial documents as mostly text files; deferred retention/privacy requirements.
- Updated [scope-and-constraints.md](scope-and-constraints.md) and [architecture.md](architecture.md) to reflect the accepted local single-user boundary. Retention remains deferred and real client/partner data must not be ingested until policy is defined.

### Implementation

- Added Python package manifest, local environment example, Neo4j store, typed domain models, text/Markdown chunker, embedding-provider interface with optional OpenAI implementation, service layer, and local stdio MCP server under `src/neo4j_agent_memory/`.
- Implemented workspace-bound entity upserts, allowlisted relationship combinations with provenance/review state, stable document/chunk identity, checksum-based re-ingestion behavior, line locators, embedding model/dimension metadata, workspace-scoped semantic retrieval, and structured task context lookup.
- Added [schema/data-dictionary.md](schema/data-dictionary.md) and [schema/graph-model.mmd](schema/graph-model.mmd); updated README and phase status notes.
- Initial vector retrieval uses scoped cosine ranking over the configured workspace. A vector index is created but indexed prefiltering is not yet used. This is intended for a small synthetic graph, not a performance claim.

### Verification limits

- Python runtime found: 3.14.6. Neo4j driver, MCP SDK, GraphRAG package are not installed in the active interpreter.
- Docker CLI exists, but `docker ps` could not connect because the local Docker daemon socket is absent. No Neo4j server was available for runtime confirmation.
- No database, embedding API, or MCP handshake was invoked. No tests were added or run in this turn. All implementation/runtime behavior remains unverified until dependencies are installed and a local Neo4j instance is available.
- Initial supported document content is plain text and Markdown; no filesystem crawling, PDF/Word parsing, extraction, source synchronization, document history, retention workflow, multi-user authorization, or production hardening is implemented.

## 2026-09-25 — Local Neo4j vertical slice exercised

### User decisions and database

- User confirmed Codex-only for the first client, local deployment, latest installed Neo4j with APOC/GDS, source details supplied as needed, hosted embeddings permitted, mostly text files, and retention/privacy deferred.
- User supplied the local Neo4j Desktop data-directory context and `neo4j://127.0.0.1:7687`. Credentials were used only for the live local connection and were not written to project files.
- Connected to Neo4j Enterprise `2026.09.0` (`neo4j` database); `SHOW PROCEDURES` included APOC and GDS namespaces. The graph had zero nodes before initialization.

### Implementation and observed behavior

- Completed a local Python package with workspace-bound typed persistence, allowlisted relationships, text/Markdown document ingestion, source and line locators, stable document/chunk IDs, an optional OpenAI embedding adapter, workspace-filtered vector retrieval, structured task context, and local stdio MCP tools.
- Created the package constraints and vector/full-text indexes, then ran `PYTHONPATH=src python examples/seed_synthetic_demo.py` against the local database. It created/reused fictional project/task/client/partner/person entities, one synthetic Markdown document/chunk, and typed links; repeatable IDs make the fixture re-runnable.
- Observed semantic-index retrieval for the synthetic query with citation `synthetic://orion-delivery-brief-v1`, locator `lines 1-7`, and a nonzero similarity score. Structured lookup returned synthetic task `demo-task-identity` with status `blocked`, priority `high`, and linked project/assignee/document context. The feature-hash vectors are fixture-only and do not demonstrate semantic relevance quality.
- Corrected schema initialization to rely on the uniqueness constraint's backing index instead of recreating a redundant ordinary source index. The demo setup previously hit a name conflict while migrating from that ordinary index; it was dropped and the uniqueness constraint was then created. No graph records were deleted during that schema correction.
- No hosted embedding request or Codex MCP handshake occurred. The local graph contains synthetic data only; retention/privacy remains deferred.

### Current limits and follow-up

- Codex stdio configuration is documented by OpenAI using `mcp_servers.<id>.command`, `args`, `env`, and `cwd`; project setup instructions point to the current official guide. No global Codex config was modified.
- No formal test suite was added or run. The synthetic seed/demo command above is implementation exercise evidence, not a claim of comprehensive correctness or release readiness.
- Docker daemon was unavailable; this work uses the user's already-running Neo4j Desktop instance. No backup/restore, deletion/retention, source synchronization, real-data authorization, multi-user access, or operational readiness evidence exists.

## 2026-09-25 — Initialize dedicated `codex-mem-01` database

- User requested that the new default database be initialized and receive the synthetic graph from the prior `neo4j` database.
- Read-only source inspection found only the known fixture: 12 nodes across Workspace, Project, Task, Client, Partner, Person, Document, and DocumentChunk labels; all sourced entities/documents were marked `synthetic-demo`, and the chunk used `synthetic-hash-v1`. No non-synthetic records were found. The target database was empty and online before initialization.
- Initialized package schema in `codex-mem-01` (9 constraints, 13 indexes), then copied the fixture's 12 nodes and 24 relationships, preserving properties and embedding vectors. The source database was not modified.
- Read-only comparison after copying confirmed matching per-label counts and per-relationship counts in source and target. A target lookup returned synthetic task `demo-task-identity` with status `blocked`.
- Project configuration defaults remain `codex-mem-01` in the MCP server, synthetic seed, and `.env.example`; environment variable `NEO4J_DATABASE` can override it. No real data, hosted embedding call, or Codex MCP handshake was involved.

## 2026-09-25 — Enable and connect the local Codex MCP server

- Added and enabled global Codex MCP server `neo4j-agent-memory` using the supported stdio configuration. It launches the project package against loopback Neo4j, database `codex-mem-01`, workspace `local-development`.
- Stored the supplied Neo4j credential in macOS login Keychain under service `codex.neo4j-agent-memory` / account `neo4j`; the Codex config invokes `security` to retrieve it at launch. No credential is stored in the repo or Codex TOML.
- Installed project dependencies into ignored `.venv`. The first launch exposed that the broad `mcp>=1.12` dependency resolved to incompatible MCP SDK 2.x; constrained the project to `mcp>=1.12,<2` and synced the environment.
- MCP initialize and list-tools handshake succeeded (six tools discovered). Read-only `get_task_context` reached `codex-mem-01` but first exposed Neo4j temporal serialization failures; MCP responses for task context now recursively convert Neo4j temporal values to JSON-safe strings.
- Repeated the handshake and tool call successfully: `get_task_context("demo-task-identity")` returned status `blocked`, one linked project, one assignee, and one document; no write tool or embedding endpoint was called.
- Current Codex configuration reports `enabled=true`. A new Codex task/session may be needed for the already-running desktop session to refresh its MCP inventory. Hosted embeddings and real-data use remain unverified/deferred.

## 2026-09-25 — Exercise MCP tool calls

- Through a local MCP stdio client, initialized the protocol session and called four tools against `codex-mem-01`: `initialize_memory_schema`, `upsert_memory_entity`, `link_memory_entities`, and `get_task_context`.
- All four returned successfully. Upsert/link used existing fictional Orion demo records and the already-existing `HAS_TASK` edge; this refreshed metadata timestamps but added no records or new relationships. Schema initialization reported existing constraints/indexes as no-ops.
- `get_task_context` returned the synthetic blocked task with one project, assignee, and linked document; Neo4j temporal values serialized as strings. No hosted embedding or real-data tool call was made.

## 2026-09-26 — Add the Codex memory-usage skill

- Added project-local `.agents/skills/neo4j-agent-memory/` with Codex skill metadata and operating guidance for choosing the six MCP tools, grounding answers in returned source metadata, and respecting explicit-write authorization, synthetic-only limits, and hosted-embedding disclosure.
- Linked the skill from the README document map and implementation-slice description. No MCP calls, database changes, global Codex configuration changes, or real-data ingestion were performed.
- Validation: `quick_validate.py .agents/skills/neo4j-agent-memory` reported `Skill is valid!`; `git diff --check` passed.

## 2026-09-26 — Scope a separate real-data pilot

- User selected database `neo4j` on the existing local Neo4j instance as the separate pilot database; `codex-mem-01` remains outside the pilot target.
- Read-only inspection confirmed `neo4j` is reachable and currently contains the synthetic fixture (12 nodes, 24 relationships; all 10 nodes with source metadata use `synthetic-demo`). No database records were changed or removed.
- Added [real-data-pilot.md](real-data-pilot.md) to record the selected database, observed synthetic state, proposed workspace isolation, and unresolved gates for data categories, access, retention/deletion, audit/provenance, source identity, embeddings, and recovery.
- No pilot workspace/configuration was created or changed, no real data was ingested, and no embedding request was made. A distinct server-configured workspace and an approved data sample remain prerequisites.

## 2026-09-26 — Clear the selected pilot database

- User explicitly requested clearing database `neo4j` on the existing local instance. A read-only preflight confirmed its only workspace was `local-development`, all 10 records with `source_system` were `synthetic-demo`, and the graph contained 12 nodes and 24 relationships; no other sourced records were present.
- Deleted all 12 nodes and 24 relationships from `neo4j`. Post-clear verification returned zero nodes and zero relationships. Preserved all nine constraints and all 11 package indexes (all online).
- Did not modify `codex-mem-01`, schema/index definitions, MCP configuration, or embedding settings. No real data was added and no embedding request was made.

## 2026-09-26 — Inventory Airtable pilot source (read-only)

- User selected the Airtable `Project Management` base and Tasks, Projects, and Users data. The corresponding Airtable tables are Tasks (13 records), Projects (8), and People (3; Airtable's table name for Users).
- Fetched a narrow read-only projection: task names/status/project and subtask links; project names/status/task, team, and lead links; person names/roles/project membership and leadership links. Omitted People email, bio, photo, and Slack URL fields. Did not fetch the Tasks collaborator field, which may expose collaborator identity details.
- No Airtable records were modified; no records were written to Neo4j, and no embedding request was made.
- Mapping review found that the existing Neo4j package can represent project-task membership and generic participation, but not a distinct project-lead relationship. That relationship and task collaborator mapping need a decision before import.

## 2026-09-26 — Implement and verify the bounded Airtable pilot

- User approved adding the required graph mappings and importing selected Airtable fields into database `neo4j`, workspace `airtable-pilot`, using Airtable record IDs for identity.
- Airtable schema was re-read before import because a previously observed field ID had changed. Project Lead was plain text in the current schema; only exact, unique matches against People names were linked. Two preflight attempts stopped before writes (stale field ID, then credential newline handling); both were corrected before the successful import.
- Added `Person.role`, typed `LEADS` and `HAS_SUBTASK` support, and expanded task-context results to include project leads, project members, and subtasks. Updated schema diagrams and data dictionary.
- Imported the approved snapshot in one transaction: 8 Projects, 40 Tasks (13 selected top-level Tasks plus 27 linked subtask items), and 3 People, plus one Workspace node. Relationship totals: 22 `HAS_TASK`, 27 `HAS_SUBTASK`, 7 `PARTICIPATES_IN`, 8 `LEADS`, and 51 workspace `CONTAINS` edges (115 total relationships).
- Read-only verification confirmed all imported records are workspace-scoped, Airtable IDs are preserved, no email properties or Documents were imported, reciprocal project/task and team links match, and indexes are online. Task-context checks returned project, lead, member, and subtask context. All 9 constraints and 11 online indexes were retained.
- `codex-mem-01` remained unchanged at 12 nodes and 24 relationships. No embeddings were created and no hosted embedding request was made. Global Codex MCP configuration remains on `codex-mem-01` / `local-development`; it was not redirected to the pilot.
- This is a one-time local pilot only. Retention/deletion, actor-level audit, and backup/recovery are unresolved; ongoing sync or broader real-data ingestion is not authorized by this import.

## 2026-09-26 — Add Airtable collaborator aliases and inverse task-project links

- User requested explicit People→Task and Task→Project links, then confirmed that Airtable collaborator names Paulo Rezende and Tamara Braga are aliases for existing People records. Added `Person.aliases` support; mapped Paulo Rezende to PF and Tamara Braga to Tams without creating duplicate people. No collaborator emails or profile URLs were stored.
- The package already supported `Person -[:ASSIGNED_TO]-> Task`; preserved that direction. Added `Task -[:BELONGS_TO]-> Project` as the explicit inverse of existing `Project -[:HAS_TASK]-> Task`; task-context project lookup now recognizes either orientation.
- Imported 20 `ASSIGNED_TO` edges, storing the source Airtable collaborator user ID on each edge, and added `BELONGS_TO` for the 22 existing project/task pairs. Read-only verification confirmed the 22 inverse edges exactly match `HAS_TASK`, 20 assignment edges link two existing People to existing Tasks, and two People have aliases.
- Smoke-tested `get_task_context` against `airtable-pilot`; it returned the task, its two linked projects, and assignees PF and Tams. `git diff --check` and Python byte-compilation passed. No commit or push was requested.

## 2026-09-26 — Make the bundle available across local Codex projects

- User asked to make the Neo4j memory bundle available globally. Installed a user-level symlink at `~/.codex/skills/neo4j-agent-memory` pointing to the repository skill, so its instructions stay in sync with the bundle.
- Updated the global user-level Codex MCP environment to database `neo4j` / workspace `airtable-pilot` (from the demo target `codex-mem-01` / `local-development`). `codex mcp list` reports the entry enabled. Restart/new Codex session may be required to reload its MCP process and global skill index.
- This is global only across projects using this local macOS Codex user. Neo4j remains bound to loopback; other computers/cloud environments require a separately secured remote deployment and per-host setup. No network exposure was made.

## 2026-09-30 — Align graph labels and schema with current Airtable

- Refreshed the live six-table Airtable schema; saved field IDs/types/link configurations/select options in `schema/airtable-source-schema.json` and an explicit field/relationship crosswalk in `schema/airtable-mapping.md`. Source record counts for the existing pilot categories are now Team 4, Setores 9, Tasks 16, Subtasks 30.
- Added Setor, Team, Subtask, Meeting, and Document metadata entity support. Setor/Team/Subtask share legacy Project/Person/Task identity, constraints, and labels. Allowed properties cover current descriptions, updates, Drive links, subtask state/date, and source table provenance. Typed relationships accept new labels while preserving legacy calls; context includes parent tasks and current-vocabulary aliases.
- Applied `examples/migrate_airtable_schema.py --apply` to `neo4j` / `airtable-pilot`: 8 Setor:Project, 3 Team:Person, 27 Subtask:Task, 13 top-level Tasks. Original properties, aliases, IDs, and all edges were preserved. Four additional constraints were initialized. The graph remains 52 nodes and 157 relationships, with 106 domain relationships. A private pre-migration export was saved under ignored `.migration-backups/`.
- Preserved the previous task `rec5OGWI2239twajF`, absent from the current source, with source_snapshot_present=false. Nine current source rows were not imported. No content refresh, Meetings/Documents record import, attachment download, or embedding call was performed.
- Live verification exercised source/legacy upserts, six supported entity categories, duplicate prevention, typed links, and parent/subtask retrieval in a temporary synthetic workspace; cleanup restored the original graph count. The configured MCP launcher initially failed to import its editable package; reinstalling the local package corrected it, then six-tool discovery and a read-only pilot task-context call succeeded.

## 2026-09-30 — Refresh current Airtable source content

- User requested the source content be migrated after the schema alignment. Refetched the full current Airtable snapshot from Team, Setores, Tasks, Subtasks, Meetings, and Documents (70 rows total) and applied it to `neo4j` / `airtable-pilot` in one transaction using `examples/import_airtable_snapshot.py`.
- Refreshed record properties and source relationships; imported 162 links. Read-only verification confirmed 4 Team, 9 Setores, 16 Tasks, 30 Subtasks, 9 Meetings, and 2 Documents, with the prior absent task retained and flagged false. `codex-mem-01` was not modified.
- Stored mapped Task/Subtask text, Meeting/Document notes, and structured status/date/link values locally. Attachment metadata includes filenames, sizes, and MIME types only. No attachment bytes, signed attachment URLs, collaborator emails, or profile image URLs were stored; no embeddings or external embedding calls were made.
- Added a repeatable dry-run-by-default snapshot importer. Before each apply it saves a private pre-write export in ignored `.migration-backups/`. The transient sanitized Airtable input snapshot is removed after verification.
- The final global MCP handshake exposed an intermittent editable-package import failure from the iCloud checkout. Added the bundle `src` path to the configured server environment as `PYTHONPATH`; the configured launcher then passed six-tool discovery and refreshed task-context retrieval.
- Corrected the export routine to include the Workspace node and `CONTAINS` edges, and wrote a complete private post-refresh graph export. Restore has not been exercised.

## 2026-09-30 — Local Ollama embeddings integrated and verified

- Added a local Ollama provider behind the existing embedding interface, with `search_document:` and `search_query:` inputs, loopback-only URL validation, 768-dimension checks, and a full model-digest check before each embedding call. The stored model identity includes `nomic-embed-text:latest` and its digest. OpenAI remains selectable explicitly.
- The installed local model `nomic-embed-text:latest` had digest `0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f`; a synthetic document and query each returned 768 values. The global local-user Codex MCP environment now selects Ollama and this digest for database `neo4j` / workspace `airtable-pilot`.
- Read-only preflight found zero `DocumentChunk` nodes in `neo4j` and the existing `memory_chunk_embedding` index online at 1536 dimensions. The scoped migration script replaced that empty index with a 768-dimensional index; read-back showed it `ONLINE`. Schema initialization now rejects a mismatched existing index instead of silently accepting `IF NOT EXISTS`.
- A synthetic end-to-end run in a disposable workspace verified ingestion, English and Portuguese semantic retrieval, citation, linked task, and workspace isolation. The first cleanup left one orphan test chunk; it was identified by exact ID and removed. The verification script was corrected and rerun. Final read-back found zero `ollama-check-` nodes, 71 `airtable-pilot` entity nodes, and zero pilot `DocumentChunk` nodes.
- The globally configured stdio MCP process initialized, listed all six tools, and called `search_memory` with `isError=false`. It returned no results because the pilot has no embedded document chunks. No Airtable source content or attachments were stored as vectors. Broader retrieval evaluation, recurring ingestion, retention/deletion, and model-change backfill remain open.
- A bounded read-only quality check embedded six already-imported Task name/description pairs in local Ollama memory only; no vectors were written to Neo4j. The expected task ranked first for one Portuguese query about Airtable workstream divisions (cosine 0.802) and one English query about first drafts (cosine 0.678). This is an encouraging two-query smoke check, not a measured retrieval benchmark; broader quality evaluation remains open.

## 2026-09-30 — Index the current Airtable pilot text locally

- User explicitly requested ingestion and indexing after the local Ollama integration. A read-only source inventory found 70 current Airtable rows plus the retained source-absent Task. Selected 66 current non-Team records: 9 Setores, 16 Tasks, 30 Subtasks, 9 Meetings, and 2 Documents. Indexed each name plus nonempty description, update, summary, or note fields. Excluded Team records, the retained source-absent Task, exact status/date fields, and all attachment metadata/bytes. Source fields already resided in the local `neo4j` pilot database; no Airtable API mutation or external embedding provider was used.
- Added `examples/index_airtable_pilot.py`, dry-run by default, fixed to `neo4j` / `airtable-pilot` and the local Ollama provider. It validates source counts/IDs, refuses stale previously indexed IDs on rerun, saves a private pre-write graph export, ingests derived documents with stable Airtable source IDs and `airtable://` locators, and verifies checksums, model/dimensions, chunks, and imported source links. Fixed the document store to reuse an existing document identity on same-content re-ingestion; a synthetic repeat-ingestion test passed.
- Dry run reported 66 records and 66 expected chunks. Apply saved `.migration-backups/20260930T212517297884Z-airtable-content.json` (mode 0600) and verified 66 derived `Document` nodes, 66 `DocumentChunk` nodes, 66 `HAS_CHUNK` edges, and 66 `RELATES_TO` source edges, using model `ollama:nomic-embed-text:latest@0a109f422b47e3a30ba2b10eca18548e944e8a23073ee3f3e947efcf3c45e59f` at 768 dimensions. Final read-back found 70 current source rows, 71 total original sourced entities including the retained source-absent Task, no synthetic test nodes, the vector index online, and 12 untouched nodes in `codex-mem-01`.
- The configured Codex MCP server returned real `search_memory` hits with source locators and original entity IDs. The expected Airtable architecture Task ranked first for a Portuguese query, and the expected drafts Subtask ranked first for an English query. `get_task_context` returned the linked derived document for the Task. The first verification harness misread the MCP response shape; the tool call itself succeeded and the corrected harness passed. These are smoke checks; broader relevance evaluation, ongoing source synchronization, stale-record deletion policy, and backup restore remain open.
