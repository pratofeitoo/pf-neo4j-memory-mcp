# Airtable schema mapping

Observed on 2026-09-30, base `Project Management` (`app18Kb5LQUkv8wy2`). The complete field IDs, names, types, link destinations, and select options are in `airtable-source-schema.json`. Field IDs are the mapping keys; display-name changes do not change entity identity.

| Table | Row label | Compatibility label | Scalar mapping |
|---|---|---|---|
| Setores | Setor | Project | Setor → name; Status → status; Project Lead → project_lead_text; External Record ID → legacy_external_record_id; Related Projects (inverse) → related_projects_text |
| Team | Team | Person | Name → name; Role → role; Bio → bio; Photo → attachment metadata (no URL or image bytes); Slack DM URL → slack_dm_url; confirmed prior names → aliases |
| Tasks | Task | Task | Name → name; Status → status; Due date (date) → due_at; Task Descrição → description; Task Atualizações → updates; Pasta no G-Drive → drive_folder_url; Arquivos → attachment metadata |
| Subtasks | Subtask | Task | Subtask → name; Status → status; Complete → complete; Data → date; Task Descrição → description; Task Updates → updates; Source Option ID → source_option_id |
| Meetings | Meeting | — | Title → name; Date → date; Notes → notes; Link → link; Status → status; Calendar Event ID → calendar_event_id; Calendar Status → calendar_status |
| Documents | Document | — | Name → name/title; Status → status; Notes → notes; Attachments → filename, size, and MIME metadata only |

Source properties available on each entity: `source_base_id`, `source_table_id`, `source_table_name`, `schema_version`, `source_snapshot_present`. `source_id` and entity `id` remain Airtable record IDs. The snapshot-presence flag describes the observed schema snapshot date, not a live deletion state. Status spelling/capitalization is preserved from the source.

| Airtable relationship | Graph edge |
|---|---|
| Setores.Tasks / Tasks.Setor | Setor HAS_TASK Task; Task BELONGS_TO Setor |
| Tasks.Subtasks / Subtasks.Parent Task | Task HAS_SUBTASK Subtask; optional Subtask BELONGS_TO Task |
| Setores.Subtasks / Subtasks.Setor | Setor HAS_SUBTASK Subtask; optional Subtask BELONGS_TO Setor |
| Setores.People / Team.Setor | Team PARTICIPATES_IN Setor |
| Tasks.Responsável (collaborators) | Team ASSIGNED_TO Task, using confirmed collaborator-to-Team aliases |
| Subtasks.Assigned / Team.Subtasks | Team ASSIGNED_TO Subtask, using linked Team record IDs |
| Setores.Documents / Documents.Projects | Setor HAS_DOCUMENT Document; Document BELONGS_TO Setor |
| Documents.Assignee (collaborators) | Team ASSIGNED_TO Document, using confirmed aliases |
| Setores.Lead (collaborators) | Team LEADS Setor by exact collaborator display-name match |
| Setores.Project Lead | Team LEADS Setor when its text exactly matches a Team name or confirmed alias; the field is text, not a record link |

Meetings has no linked-record fields in the observed schema. Lookup fields mirror existing links and are not separate edges. Airtable collaborator emails/profile URLs and signed attachment URLs are excluded. Attachments are represented only by filename, byte size, and MIME type; no file was downloaded or parsed.

## Migration applied

`examples/migrate_airtable_schema.py` adds current source labels and table provenance to the earlier pilot records. `Setor:Project`, `Team:Person`, and `Subtask:Task` retain compatibility with existing callers. New upserts using source labels reuse canonical keys, so aliases do not create duplicate nodes. Four additional uniqueness constraints support Setor, Team, Subtask, and Meeting.

`examples/import_airtable_snapshot.py` refreshes current record properties and Airtable-linked relationships transactionally. On 2026-09-30 it imported all 70 current rows: 4 Team, 9 Setores, 16 Tasks, 30 Subtasks, 9 Meetings, and 2 Documents, with 162 imported relationships. The graph has 71 source/current-or-retained entity nodes in `airtable-pilot`, plus the Workspace node, and 162 domain edges plus workspace containment. The earlier task `rec5OGWI2239twajF` remains, marked `source_snapshot_present=false`. Paulo/PF and Tamara/Tams aliases remain attached to their matched Team identities.

Task descriptions/updates, meeting notes, and document notes are stored as structured Neo4j properties. A separate, user-approved local Ollama run indexed names plus these selected text fields for 66 current Setor/Task/Subtask/Meeting/Document records, creating one derived `Document` and `DocumentChunk` per record with a source link and Airtable record locator. Team records and the older Task marked absent from the current snapshot were excluded. Attachment filenames, sizes, and types remain metadata only; no attachment binaries, signed attachment URLs, collaborator emails, or profile image URLs were imported or embedded. Each snapshot or index apply creates a private pre-write export under ignored `.migration-backups/`.

Dry run: `PYTHONPATH=src .venv/bin/python examples/migrate_airtable_schema.py`. Apply: append `--apply`. Apply creates a private snapshot under ignored `.migration-backups/` before modifying the graph. The script uses the existing Keychain credential or `NEO4J_PASSWORD` and is fixed to the selected local pilot database/workspace.
