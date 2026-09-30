"""Add current Airtable labels/provenance to existing pilot records, preserving legacy labels.

Dry run by default. --apply exports a private pre-migration snapshot and updates one
transaction. It never creates source records or changes existing relationships.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

from neo4j import GraphDatabase
from neo4j_agent_memory.store import Neo4jStore
from neo4j_agent_memory.server import _json_safe

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    schema = json.loads((ROOT / "schema/airtable-source-schema.json").read_text())
    mapping = {}
    for table in schema["tables"]:
        for record_id in table["existing_pilot_record_ids"]:
            if record_id in mapping:
                raise ValueError("Source record appears in more than one table")
            mapping[record_id] = table
    password = os.environ.get("NEO4J_PASSWORD") or subprocess.check_output(
        ["security", "find-generic-password", "-s", "codex.neo4j-agent-memory", "-a", "neo4j", "-w"], text=True
    ).strip()
    with GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", password)) as driver:
        with driver.session(database="neo4j") as session:
            nodes = [dict(r) for r in session.run(
                "MATCH (n {workspace_id:$w}) RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties ORDER BY n.id",
                w="airtable-pilot")]
            edges = [dict(r) for r in session.run(
                "MATCH (a {workspace_id:$w})-[r]->(b {workspace_id:$w}) RETURN a.id AS source, b.id AS target, type(r) AS type, properties(r) AS properties ORDER BY source,type,target",
                w="airtable-pilot")]
            before = [dict(r) for r in session.run("MATCH (n) RETURN count(n) AS nodes")]
            total_edges = session.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]
            if not nodes:
                raise ValueError("Expected existing pilot records; empty workspace")
            updates = []
            for node in nodes:
                props = node["properties"]
                table = mapping.get(props["id"])
                if props.get("source_id") != props["id"]:
                    raise ValueError(f"Unmapped or unexpected source identity: {props['id']}")
                source_present = table is not None
                if table is None:
                    # Preserve prior snapshot records removed from the current source.
                    if "Project" in node["labels"]:
                        source_name = "Setores"
                    elif "Person" in node["labels"]:
                        source_name = "Team"
                    elif "Task" in node["labels"]:
                        is_subtask = any(e["type"]=="HAS_SUBTASK" and e["target"]==props["id"] for e in edges)
                        source_name = "Subtasks" if is_subtask else "Tasks"
                    else:
                        raise ValueError("Unknown legacy category")
                    table = next(t for t in schema["tables"] if t["name"]==source_name)
                expected = {"Setor":"Project", "Team":"Person", "Task":"Task", "Subtask":"Task"}[table["graph_label"]]
                if expected not in node["labels"]:
                    raise ValueError("Unexpected existing node label")
                updates.append({"id":props["id"], "label":table["graph_label"], "table_id":table["id"], "table_name":table["name"], "source_present":source_present})
            summary = {label:sum(u["label"] == label for u in updates) for label in {u["label"] for u in updates}}
            print(json.dumps({"mode":"apply" if args.apply else "dry-run", "existing_records":summary, "domain_relationships":len(edges), "source_records_not_imported":len(mapping)-sum(u["source_present"] for u in updates), "prior_records_absent_from_source":[u["id"] for u in updates if not u["source_present"]]}))
            if not args.apply:
                return
            backup_dir = ROOT / ".migration-backups"
            backup_dir.mkdir(mode=0o700, exist_ok=True)
            backup_path = backup_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-airtable-schema.json")
            with os.fdopen(os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as file:
                json.dump(_json_safe({"database":"neo4j", "workspace":"airtable-pilot", "nodes":nodes, "edges":edges}), file, indent=2)
            Neo4jStore(driver, "neo4j", 1536).initialize()
            def migrate(tx):
                for label in summary:
                    result = tx.run(
                        f"UNWIND $rows AS row MATCH (n {{workspace_id:$w,id:row.id}}) SET n:{label}, n.source_base_id=$base, n.source_table_id=row.table_id, n.source_table_name=row.table_name, n.source_snapshot_present=row.source_present, n.schema_version=$version RETURN count(n) AS n",
                        rows=[u for u in updates if u["label"]==label], w="airtable-pilot", base=schema["base_id"], version="airtable-2026-09-30").single()
                    if result["n"] != summary[label]:
                        raise ValueError("Migration endpoint count changed")
                for node in nodes:
                    current = tx.run("MATCH (n {workspace_id:$w,id:$id}) RETURN properties(n) AS p",w="airtable-pilot",id=node["properties"]["id"]).single()["p"]
                    if any(current.get(k)!=v for k,v in node["properties"].items() if k not in {"source_base_id","source_table_id","source_table_name","schema_version","source_snapshot_present"}):
                        raise ValueError("Existing properties changed")
                after_edges = [dict(r) for r in tx.run(
                    "MATCH (a {workspace_id:$w})-[r]->(b {workspace_id:$w}) RETURN a.id AS source, b.id AS target, type(r) AS type, properties(r) AS properties ORDER BY source,type,target",w="airtable-pilot")]
                if after_edges != edges or tx.run("MATCH (n) RETURN count(n) AS n").single()["n"]!=before[0]["nodes"] or tx.run("MATCH ()-[r]->() RETURN count(r) AS n").single()["n"]!=total_edges:
                    raise ValueError("Migration changed graph records or relationships")
            session.execute_write(migrate)
            print(json.dumps({"migrated":summary,"node_and_edge_counts_preserved":True,"backup":str(backup_path)}))


if __name__ == "__main__":
    main()
