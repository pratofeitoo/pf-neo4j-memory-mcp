# Phase 0 — Scope and Operating Constraints

**Status:** Initial local synthetic-slice scope accepted; production data policy deferred
**Recorded:** 2026-09-25
**Project:** Neo4j Agent Memory Package

This artifact records the current safe working boundary for the first vertical slice. It distinguishes decisions already established by the project record, provisional assumptions used to continue non-dependent work, and choices that require user input before they can become architecture or deployment decisions.

## Established direction

- Neo4j remains the proposed graph and vector persistence layer.
- The package will own a domain-aware persistence/retrieval service and typed, permission-aware MCP tools.
- Retrieval will combine structured graph queries with vector or hybrid search and bounded graph expansion.
- Provenance, source-of-truth distinctions, access scope, temporal information, uncertainty, and review state are required data properties.
- The demo remains synthetic. The user-authorized Airtable snapshot in database `neo4j`, workspace `airtable-pilot`, now covers Team, Setores, Tasks, Subtasks, Meetings, and Documents as recorded in [real-data-pilot.md](real-data-pilot.md). Attachments are metadata only; ongoing sync and embeddings are not enabled.
- External services will not be connected, installed, deployed, or published as part of this phase without explicit authorization.

## Initial slice operating boundary

The first slice is local, single-user, and Codex-only. The demo remains synthetic; the one-time Airtable snapshot in `neo4j` / `airtable-pilot` has the field limits recorded in [real-data-pilot.md](real-data-pilot.md). This does not authorize shared deployment or ongoing synchronization.

| Area | Accepted boundary | Why it is safe for the first slice |
|---|---|---|
| Deployment | Local/private development only; no shared or multi-tenant deployment | The configured server is constrained to a loopback database URI and one trusted workspace. |
| Agent client | Codex first, using local stdio MCP; plugin packaging deferred | Keeps the domain service independent of a Codex-specific runtime while exposing tools locally. |
| Data | Synthetic by default; user-authorized six-table Airtable snapshot in a separate workspace | Prevents the pilot snapshot from silently expanding to other sources or ongoing sync. |
| Dataset shape | Synthetic demo workspace, plus the separately authorized Airtable pilot workspace | Keeps the demo fixture intact in `codex-mem-01` while isolating the bounded pilot snapshot in `neo4j`. |
| Source of truth | User provides source context as needed; synthetic fixtures are authoritative only inside the demo | No automatic sync or write-back is active. |
| Embeddings | Provider boundary with optional OpenAI implementation; do not invoke without credentials and an explicit ingestion call | Keeps embedding selection configurable and makes each external text transfer visible at use time. |
| Access | Workspace scope comes from trusted server configuration; no workspace argument is accepted from the tool caller | Fits the selected local single-user boundary; it does not support shared access. |
| Retention | No general policy or automated deletion; the approved snapshot is limited to the local pilot | Any expansion or ongoing use remains gated on retention/deletion decisions. |
| Neo4j extensions | APOC/GDS are installed; neither is required by the initial core slice | Their availability is verified, while analytics use remains outside current scope. |

## User decisions recorded on 2026-09-25

| Area | User direction | Evidence/current implementation |
|---|---|---|
| First client | Codex only for the first slice | Local stdio MCP server package |
| Deployment | Local | Server rejects non-loopback Neo4j URIs and uses one configured workspace |
| Neo4j | Latest installed version; APOC and GDS are available | Read-only inventory observed Neo4j Enterprise `2026.09.0`; `SHOW PROCEDURES` found both `apoc` and `gds` procedure namespaces |
| Sources | User will provide source-system information as needed | Ingestion/upsert calls carry source system and source IDs; there is no automatic sync |
| Embeddings | Text may leave the machine | Optional OpenAI embedding adapter is implemented and called only when ingest/search runs |
| Documents | Mostly text files | Initial implementation accepts text and Markdown content only |
| Retention/privacy | Not defined; skip for now | Deferred. Keep all records synthetic until deletion, retention, and privacy rules are set. |

## Additional user decision recorded on 2026-09-26

| Area | User direction | Evidence/current implementation |
|---|---|---|
| Initial pilot source and scope (2026-09-26) | Airtable base `Project Management`; first import covered Tasks, Projects, and People. | This initial field boundary was expanded by the user's 2026-09-30 request; see the current six-table approval below. |

## Current pilot expansion recorded on 2026-09-30

The user asked to migrate current Airtable source content after schema alignment. The approved snapshot now includes Team, Setores, Tasks, Subtasks, Meetings, and Documents, with mapped structured text, status/date/link fields, Meeting/Document notes, and attachment metadata. Collaborator emails, profile image URLs, signed attachment URLs, attachment binaries, and embeddings are excluded. The import is a one-time snapshot, not synchronization. See [real-data-pilot.md](real-data-pilot.md).

This is a bounded pilot authorization, not a general production-data policy. Retention, deletion, complete actor audit, and backup/recovery requirements remain open for any expanded or continuing use.

The local Neo4j URI is `neo4j://127.0.0.1:7687`. Credentials are intentionally not stored in this project. The database graph was empty at first inspection; package indexes/constraints and a fictional `local-development` demo graph were subsequently created there.

## Deferred decisions

| Decision | Why it blocks a durable implementation choice | Current state |
|---|---|---|
| Shared deployment and user identity | Determines tenant authorization, database topology, and operational controls | Deferred; initial service is local single-user only |
| Sources of truth per entity/field | Needed before adding automatic source-system synchronization or write-back | Deferred until the user supplies those source workflows |
| Embedding provider/service | Determines where text is processed and what credentials/cost apply | Open; OpenAI adapter is present but no API call is configured or executed |
| Additional document formats, languages, and volume | Determines parsers, locators, and performance targets | Open beyond plain text and Markdown |
| Retention, deletion, audit, and LGPD/privacy requirements | Determines deletion semantics, audit preservation, backups, and access review | User asked to defer; remains a gate before real data |

## First-slice acceptance measures

The slice can be considered technically demonstrated only when synthetic tests show all of the following:

1. Typed workspace, project, task, client, partner, and person records can be created and linked.
2. A synthetic document is ingested idempotently into stable document/chunk records with source and locator metadata.
3. The document links to multiple projects/tasks/parties with link provenance and review state.
4. Embeddings store model and dimension metadata and can be regenerated without duplicate records.
5. Scoped semantic retrieval returns a passage, bounded graph context, and source citation.
6. Exact task/project state is answered through structured graph queries.
7. Repeated ingestion is idempotent, ambiguous links remain reviewable, and an unauthorized scope returns no protected result.
8. A small typed MCP surface exposes the demonstrated operations, with setup and limitations documented.

## What is intentionally not decided here

This artifact does not approve a production deployment, a Neo4j hosting plan, a specific embedding vendor/model, a source-system integration, automatic acceptance of extracted facts, arbitrary Cypher for ordinary agents, multi-tenant SaaS, or plugin publication. Those choices require evidence and, where they affect privacy, cost, security, or external state, explicit user direction.
