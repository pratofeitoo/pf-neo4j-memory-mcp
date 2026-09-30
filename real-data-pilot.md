# Real-Data Pilot Readiness

**Status:** Current six-table Airtable snapshot refreshed in `neo4j` / `airtable-pilot`
**Updated:** 2026-09-30

On 2026-09-30 the pilot was refreshed from the current six-table Airtable snapshot. All 70 current records and 162 source-linked relationships were imported; the old task absent from Airtable is retained and marked `source_snapshot_present=false`. See [schema/airtable-mapping.md](schema/airtable-mapping.md) for field and relationship mappings.

This document tracks a local, single-user pilot. The user authorized importing the current structured record content from Team, Setores, Tasks, Subtasks, Meetings, and Documents. This is a one-time refresh; it does not establish ongoing synchronization or production/shared access.

## Confirmed pilot target and observed state

- Neo4j instance: the existing local loopback instance at `neo4j://127.0.0.1:7687`.
- Target database: `neo4j`, selected by the user as the separate pilot database rather than `codex-mem-01`.
- Before clearing, read-only inspection found only the known synthetic demo graph: 12 nodes, 24 relationships, one `local-development` workspace, and 10 sourced entities/documents, all with `source_system = synthetic-demo`.
- At the user's request, the synthetic graph data was cleared from `neo4j`; the nine constraints and all 11 package indexes were retained.
- Refreshed `airtable-pilot` with 4 Team, 9 Setores, 16 Tasks, 30 Subtasks, 9 Meetings, and 2 Documents. The graph has 71 source/current-or-retained entity nodes, plus Workspace; 162 domain relationships, plus containment. One older Task absent from the current Airtable source remains marked `source_snapshot_present=false`.
- Task descriptions/updates and meeting/document notes are stored as graph properties. Attachment filenames, sizes, and MIME types are stored as metadata only. Attachments were not downloaded or parsed; embeddings were not generated.
- Airtable collaborator emails, profile image URLs, and signed attachment URLs were not imported. Confirmed Paulo/PF and Tamara/Tams aliases remain mapped to their Team records.
- The separate `codex-mem-01` database remains unchanged at 12 nodes and 24 relationships.
- The global Codex MCP entry targets `neo4j` / `airtable-pilot`; its six-tool handshake and task-context call were reverified on 2026-09-30.
- Client/deployment remain Codex local stdio and single-user for the pilot. This is not multi-user authorization.

## Ongoing-use gates

| Topic | Current evidence or prior direction | Decision needed before ongoing use |
|---|---|---|
| Source and purpose | User selected Airtable base `Project Management`; current snapshot covers Team, Setores, Tasks, Subtasks, Meetings, and Documents. Intended context includes project status, tasks, due dates, team/lead links, meeting notes, and document metadata/notes. | No additional source is in scope. |
| Data scope and sensitivity | User authorized the current structured rows in six tables. Imported mapped task/subtask text and state, Team fields, Setor fields, meeting notes, document notes and attachment metadata. | This records a snapshot, not a continuing source-of-truth sync. |
| Access boundary | Local, single-user Codex was selected; pilot records are workspace-scoped | No shared or multi-user use is authorized. Check any additional readers/backups before expansion. |
| Embedding processing | No embedding was generated or sent to an embedding provider. Text remains in the local Neo4j instance. | Keep embedding requests separate from this structured snapshot. |
| Retention and deletion | A prior task missing from the latest source is retained and flagged. Private pre-write exports and a complete post-refresh graph export exist; restore and deletion have not been exercised. | Define retention, deletion, and export handling before ongoing use. |
| Audit and provenance | Entities retain Airtable `source_system` and record IDs; relationships are marked `IMPORTED`; no complete actor-level audit trail exists | Decide what must be recorded for each write (actor, timestamp, source, action, review state) before recurring ingestion or expansion. |
| Identity and source of truth | Airtable record IDs are stable graph/source IDs. Source presence records whether a row appeared in the 2026-09-30 snapshot. | No automatic refresh or deletion policy exists. |
| Graph mapping | Current labels are Setor, Team, Task, Subtask, Meeting, and Document, with legacy compatibility labels for Project/Person/Task. Links are mapped from source linked-record and collaborator fields. Paulo/PF and Tamara/Tams are confirmed aliases. | Other collaborator names must match a Team record; unmatched names cause the importer to stop. |
| Source lifecycle | Airtable record IDs are stable source keys; this is a one-time snapshot, not an automated sync. | Refreshes/conflict policy and deletion workflows are not implemented. |
| Format and volume | Six tables, 70 rows, structured fields and relationship links. Attachments are metadata only. | Downloading or extracting attachment contents is a separate step. |
| Recovery and operations | Private pre-write graph exports were created for schema and content changes. Restore has not been demonstrated. | Exercise backup restore before relying on this as the sole source of durable project memory. |

## Safe sequence

1. Keep `codex-mem-01` unchanged; the pilot is stored in the separate `airtable-pilot` workspace in database `neo4j`.
2. Preserve Airtable record IDs in entity IDs/source IDs. For Airtable collaborator users, retain their collaborator IDs on `ASSIGNED_TO` edges and display-name aliases on the matched `Person`; mark imported edges `IMPORTED`.
3. Fetch the six current Airtable tables and use `examples/import_airtable_snapshot.py` for a dry run and transactional one-time refresh. The 2026-09-30 refresh is complete.
4. Read-only verification confirmed 70 current rows, 162 imported relationships, the prior missing task retained with its false source-presence flag, and the confirmed Team aliases.
5. Ongoing synchronization, attachment download/extraction, embedding generation, retention/deletion policy, and recovery testing remain separate decisions.

## Exit gate

The bounded one-time snapshot has been imported and verified. Remaining unresolved retention/deletion, actor-level audit, and backup/recovery questions limit approval to this local pilot only; this is not production or legal-compliance approval.
