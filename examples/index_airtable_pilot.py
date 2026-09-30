"""Index the approved local Airtable snapshot with Ollama. Dry run by default."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import os
import subprocess

from neo4j_agent_memory.chunking import chunk_text
from neo4j_agent_memory.models import DocumentInput, EntityRef
from neo4j_agent_memory.server import create_service

from import_airtable_snapshot import BASE_ID, EXPECTED_COUNTS, TABLES, export_backup

DATABASE = "neo4j"
WORKSPACE = "airtable-pilot"
INDEX_SOURCE = "airtable-text-index-v1"
INDEX_COUNTS = {label: EXPECTED_COUNTS[table_id] for table_id, (_, label) in TABLES.items() if label != "Team"}
INDEX_FIELDS = ("description", "updates", "summary", "notes")


@dataclass(frozen=True)
class IndexItem:
    label: str
    record_id: str
    document: DocumentInput
    checksum: str
    chunk_count: int


def build_items(records: list[dict]) -> list[IndexItem]:
    items = []
    for record in records:
        labels = record["labels"]
        label = next((kind for kind in ("Subtask", "Task", "Setor", "Meeting", "Document") if kind in labels), None)
        if label is None:
            raise RuntimeError(f"Unexpected indexed source labels: {labels}")
        props = record["properties"]
        record_id = props["id"]
        if record_id != props.get("source_id") or not props.get("name"):
            raise RuntimeError(f"Invalid source identity or name: {record_id}")
        table_id = props.get("source_table_id")
        if table_id not in TABLES or TABLES[table_id][1] != label:
            raise RuntimeError(f"Source table/label mismatch: {record_id}")
        lines = [f"{label}: {props['name'].strip()}"]
        for field in INDEX_FIELDS:
            value = props.get(field)
            if value is not None and str(value).strip():
                lines.append(f"{field.capitalize()}: {str(value).strip()}")
        text = "\n\n".join(lines)
        document = DocumentInput(
            source_system=INDEX_SOURCE,
            source_id=record_id,
            title=f"{label}: {props['name'].strip()}",
            text=text,
            mime_type="text/markdown",
            source_uri=f"airtable://{BASE_ID}/{table_id}/{record_id}",
            linked_entities=(EntityRef(label, record_id),),
            link_provenance="IMPORTED",
            link_review_state="IMPORTED",
        )
        items.append(IndexItem(label, record_id, document, sha256(text.encode("utf-8")).hexdigest(), len(chunk_text(text))))
    if Counter(item.label for item in items) != Counter(INDEX_COUNTS):
        raise RuntimeError(f"Unexpected current-source counts: {dict(Counter(item.label for item in items))}")
    if len({item.record_id for item in items}) != len(items):
        raise RuntimeError("Duplicate source record ID")
    return sorted(items, key=lambda item: (item.label, item.record_id))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Write vectors after preflight and backup")
    args = parser.parse_args()
    if os.environ.get("NEO4J_DATABASE") != DATABASE or os.environ.get("MEMORY_WORKSPACE_ID") != WORKSPACE:
        raise RuntimeError("Target must be neo4j / airtable-pilot")
    if os.environ.get("MEMORY_EMBEDDING_PROVIDER") != "ollama":
        raise RuntimeError("This importer requires the local Ollama provider")
    if "NEO4J_PASSWORD" not in os.environ:
        os.environ["NEO4J_PASSWORD"] = subprocess.check_output(
            ["/usr/bin/security", "find-generic-password", "-a", "neo4j", "-s", "codex.neo4j-agent-memory", "-w"],
            text=True,
        ).strip()
    service, driver = create_service()
    try:
        with driver.session(database=DATABASE) as session:
            index = session.run(
                "SHOW VECTOR INDEXES YIELD name, state, options WHERE name = $name "
                "RETURN state, options", name="memory_chunk_embedding"
            ).single()
            if not index or index["state"] != "ONLINE" or index["options"]["indexConfig"].get("vector.dimensions") != 768:
                raise RuntimeError("The 768-dimensional pilot vector index is not online")
            records = [dict(row) for row in session.run(
                "MATCH (n {workspace_id:$workspace}) "
                "WHERE n.source_system = 'airtable' AND n.source_base_id = $base "
                "AND n.source_snapshot_present = true AND NOT n:Team "
                "RETURN labels(n) AS labels, properties(n) AS properties",
                workspace=WORKSPACE, base=BASE_ID,
            )]
            items = build_items(records)
            existing_ids = {row["source_id"] for row in session.run(
                "MATCH (d:Document {workspace_id:$workspace, source_system:$source}) "
                "RETURN d.source_id AS source_id", workspace=WORKSPACE, source=INDEX_SOURCE,
            )}
            stale_ids = existing_ids - {item.record_id for item in items}
            if stale_ids:
                raise RuntimeError(f"Previously indexed records are absent from the current snapshot: {sorted(stale_ids)}")
            print(f"database={DATABASE} workspace={WORKSPACE} source_records={len(items)} "
                  f"by_label={dict(Counter(item.label for item in items))} "
                  f"expected_chunks={sum(item.chunk_count for item in items)} existing_index_documents={len(existing_ids)}")
            if not args.apply:
                return
            backup = export_backup(session)
            print(f"prewrite_backup={backup}", flush=True)
        for number, item in enumerate(items, start=1):
            result = service.ingest_text_document(item.document)
            if result["checksum"] != item.checksum or result["chunk_count"] != item.chunk_count:
                raise RuntimeError(f"Write verification failed for source record {item.record_id}")
            if number % 10 == 0 or number == len(items):
                print(f"indexed={number}/{len(items)}", flush=True)
        with driver.session(database=DATABASE) as session:
            rows = [dict(row) for row in session.run(
                "MATCH (d:Document {workspace_id:$workspace, source_system:$source}) "
                "OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk) "
                "OPTIONAL MATCH (d)-[r:RELATES_TO]->(n) "
                "RETURN d.source_id AS source_id, d.checksum AS checksum, "
                "count(DISTINCT c) AS chunks, "
                "collect(DISTINCT {id:n.id, provenance:r.provenance, review_state:r.review_state}) AS links, "
                "collect(DISTINCT c.embedding_dimensions) AS dimensions, "
                "collect(DISTINCT c.embedding_model) AS models",
                workspace=WORKSPACE, source=INDEX_SOURCE,
            )]
            by_id = {item.record_id: item for item in items}
            expected_model = service.embedding_provider.model
            if len(rows) != len(items):
                raise RuntimeError(f"Expected {len(items)} indexed documents, found {len(rows)}")
            for row in rows:
                item = by_id.get(row["source_id"])
                if (item is None or row["checksum"] != item.checksum or row["chunks"] != item.chunk_count
                        or row["dimensions"] != [768] or row["models"] != [expected_model]
                        or not any(link["id"] == item.record_id and link["provenance"] == "IMPORTED"
                                   and link["review_state"] == "IMPORTED" for link in row["links"])):
                    raise RuntimeError(f"Indexed document verification failed: {row['source_id']}")
            print(f"verified_documents={len(rows)} verified_chunks={sum(row['chunks'] for row in rows)} "
                  f"model={expected_model}")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
