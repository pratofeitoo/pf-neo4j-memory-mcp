"""Refresh the approved Airtable snapshot in neo4j/airtable-pilot.

Consumes one JSON snapshot on stdin, as returned by the Airtable connector and
keyed by the six current table IDs. Dry-run by default. --apply writes a private
pre-import export, then refreshes current rows and their linked-record edges in a
single Neo4j transaction. Attachment metadata is kept; attachments are not fetched
and no embeddings are generated.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

from neo4j import GraphDatabase
from neo4j_agent_memory.server import _json_safe

ROOT = Path(__file__).resolve().parents[1]
BASE_ID = "app18Kb5LQUkv8wy2"
WORKSPACE = "airtable-pilot"
SOURCE_SYSTEM = "airtable"
SCHEMA_VERSION = "airtable-2026-09-30"

TABLES = {
    "tbl518pubSWkoEl3i": ("Team", "Team"),
    "tbllwAsdO3INbWG2l": ("Setores", "Setor"),
    "tblBrMmI0QdkDj67m": ("Tasks", "Task"),
    "tblddT9IPVKdUkVQq": ("Subtasks", "Subtask"),
    "tblIoJIcbLBQ4DLxO": ("Meetings", "Meeting"),
    "tbl9HKSo59e6nRC2r": ("Documents", "Document"),
}
EXPECTED_COUNTS = dict(zip(TABLES, (4, 9, 16, 30, 9, 2)))
FIELDS = {
    "Team": {"name":"fldRMDPyE7QHmjWo9", "role":"fldjX2huPVbZ2oRvI", "bio":"fldCCCpIQNzvgTzqt", "photo":"fldl0YMgIT5cRFKH9", "slack":"fldTJU7bSJxQuVZAH", "setors":"fldiG9aCJ7lsxp5QR", "subtasks":"fldCwWmXtV6aWoJbT"},
    "Setores": {"name":"fldbjvqzfZI05RnuQ", "status":"fldeCz4wJ2SNMdS55", "lead_people":"fldv3outpZj1KcKVH", "tasks":"fldHGbPRjJsY4eyj1", "legacy_id":"fldC9a5wRWjkq4BkO", "related_projects":"fldH8jE5li90U1SJE", "people":"fld7EZHQ8pJSmvMNz", "project_lead":"fldcMT3FILo2gmUHQ", "documents":"fldIdHRKJtwsVsRgE", "subtasks":"fldfZPQj6wksnLtUJ"},
    "Tasks": {"name":"fldZzUbbaqffvyGRw", "status":"fldfOSgvD8A58U4tU", "assignees":"fldVPzpAVGtg4xZ0q", "setors":"flduHsdJeK0DWcCjI", "subtasks":"fldPTPrcUoe7h6wbP", "attachments":"fldCGKA9gIj5Dro0B", "due":"fldcu0Nq8cRNVGfs9", "description":"fld5vVb8ZdNtsL4kX", "updates":"fldhTipkbkAF3zCos", "drive":"fldzEz2EeLKKLMZQr"},
    "Subtasks": {"name":"fldLBDfSCHcY6nQNO", "parent":"flduRj7kXA3hfiHyV", "setors":"fldPvqHqTla3Mi36z", "status":"fldpt96OEEnOJXRlL", "assignees":"fldZ3gZuRCH4SJwp5", "date":"fldQ5LrehJiEoxFka", "complete":"fldSHQcPsWoPDX26V", "description":"fldxAWwC6uEqAsCwX", "updates":"fldh6ItuXeVPo4kGy", "option_id":"fldj8Iu3pBG8mqpGq"},
    "Meetings": {"name":"fldBivGZcG4gapSYT", "date":"fldg2L69SxTO53W3p", "notes":"fldKspMZUEiDdYl5t", "attachments":"fldUD54hxO7PAbUjr", "link":"fldZ6COXoamnstRqR", "status":"fldflaH7xsZoauhAM", "calendar_id":"fld0v9ctvubf7Kn96", "calendar_status":"fldHJIyPqLh24Swf7"},
    "Documents": {"name":"fldHkjnZy60RogG3b", "projects":"fldstXvYGuaqaBLlz", "notes":"fldryUCEyax4CqMfj", "attachments":"fldMNQsDIvJTvrQgG", "assignees":"fldVUWSICMJlgN78M", "status":"fldHnCHPVbnaw4ED5"},
}


def scalar(record, key):
    value = record.get("cellValuesByFieldId", {}).get(key)
    if isinstance(value, dict):
        return value.get("name")
    return value


def linked(record, key):
    value = record.get("cellValuesByFieldId", {}).get(key) or []
    return [item["id"] for item in value if isinstance(item, dict) and item.get("id")]


def collaborators(record, key):
    value = record.get("cellValuesByFieldId", {}).get(key) or []
    return [item.get("name") for item in value if isinstance(item, dict) and item.get("name")]


def attachment_metadata(record, key):
    value = record.get("cellValuesByFieldId", {}).get(key) or []
    return json.dumps([
        {k: item[k] for k in ("filename", "size", "type") if k in item}
        for item in value if isinstance(item, dict)
    ], ensure_ascii=False)


def build_snapshot(snapshot):
    if set(snapshot) != set(TABLES):
        raise ValueError("Snapshot must contain exactly the six current Airtable tables")
    entities, record_table, edges, unresolved = [], {}, set(), set()
    rows_by_table = {}
    for table_id, (table_name, label) in TABLES.items():
        records = snapshot[table_id].get("records", [])
        expected = EXPECTED_COUNTS[table_id]
        if len(records) != expected:
            raise ValueError(f"{table_name}: expected {expected} complete rows, received {len(records)}")
        rows_by_table[table_name] = records
        for record in records:
            if record["id"] in record_table:
                raise ValueError("Airtable record ID appears in more than one table")
            record_table[record["id"]] = label

    teams = rows_by_table["Team"]
    names_to_id = {}
    for rec in teams:
        name = scalar(rec, FIELDS["Team"]["name"])
        if not name:
            raise ValueError("Team record is missing its primary name")
        names_to_id[name.casefold()] = rec["id"]
    # These aliases were explicitly confirmed by the user in this pilot.
    for alias, canonical in {"PF":"Paulo Rezende", "Tams":"Tamara Braga"}.items():
        if canonical.casefold() in names_to_id:
            names_to_id[alias.casefold()] = names_to_id[canonical.casefold()]

    def add_edge(source, rel, target):
        if source not in record_table or target not in record_table:
            raise ValueError(f"Airtable link points outside the imported tables: {source} -> {target}")
        edges.add((source, rel, target))

    for table_id, (table_name, label) in TABLES.items():
        for rec in rows_by_table[table_name]:
            f = FIELDS[table_name]
            name = scalar(rec, f["name"])
            if not name:
                raise ValueError(f"{table_name} record {rec['id']} is missing its primary name")
            props = {}
            if table_name == "Team":
                props = {"role":scalar(rec,f["role"]), "bio":scalar(rec,f["bio"]), "photo_metadata":attachment_metadata(rec,f["photo"]), "slack_dm_url":scalar(rec,f["slack"])}
                for setor in linked(rec,f["setors"]): add_edge(rec["id"],"PARTICIPATES_IN",setor)
                for subtask in linked(rec,f["subtasks"]): add_edge(rec["id"],"ASSIGNED_TO",subtask)
            elif table_name == "Setores":
                props = {"status":scalar(rec,f["status"]), "project_lead_text":scalar(rec,f["project_lead"]), "legacy_external_record_id":scalar(rec,f["legacy_id"]), "related_projects_text":scalar(rec,f["related_projects"])}
                for task in linked(rec,f["tasks"]): add_edge(rec["id"],"HAS_TASK",task)
                for subtask in linked(rec,f["subtasks"]): add_edge(rec["id"],"HAS_SUBTASK",subtask)
                for team in linked(rec,f["people"]): add_edge(team,"PARTICIPATES_IN",rec["id"])
                for document in linked(rec,f["documents"]): add_edge(rec["id"],"HAS_DOCUMENT",document)
                for person_name in collaborators(rec,f["lead_people"]):
                    target = names_to_id.get(person_name.casefold())
                    if target: add_edge(target,"LEADS",rec["id"])
                    else: unresolved.add(person_name)
                project_lead = scalar(rec,f["project_lead"])
                target = names_to_id.get(project_lead.casefold()) if project_lead else None
                if target: add_edge(target,"LEADS",rec["id"])
            elif table_name == "Tasks":
                props = {"status":scalar(rec,f["status"]), "description":scalar(rec,f["description"]), "updates":scalar(rec,f["updates"]), "due_at":scalar(rec,f["due"]), "drive_folder_url":scalar(rec,f["drive"]), "attachment_metadata":attachment_metadata(rec,f["attachments"])}
                for setor in linked(rec,f["setors"]): add_edge(rec["id"],"BELONGS_TO",setor)
                for subtask in linked(rec,f["subtasks"]): add_edge(rec["id"],"HAS_SUBTASK",subtask)
                for person_name in collaborators(rec,f["assignees"]):
                    target = names_to_id.get(person_name.casefold())
                    if target: add_edge(target,"ASSIGNED_TO",rec["id"])
                    else: unresolved.add(person_name)
            elif table_name == "Subtasks":
                props = {"status":scalar(rec,f["status"]), "complete":scalar(rec,f["complete"]), "date":scalar(rec,f["date"]), "description":scalar(rec,f["description"]), "updates":scalar(rec,f["updates"]), "source_option_id":scalar(rec,f["option_id"])}
                for parent in linked(rec,f["parent"]): add_edge(parent,"HAS_SUBTASK",rec["id"])
                for setor in linked(rec,f["setors"]):
                    add_edge(setor,"HAS_SUBTASK",rec["id"])
                    add_edge(rec["id"],"BELONGS_TO",setor)
                for team in linked(rec,f["assignees"]): add_edge(team,"ASSIGNED_TO",rec["id"])
            elif table_name == "Meetings":
                props = {"date":scalar(rec,f["date"]), "notes":scalar(rec,f["notes"]), "link":scalar(rec,f["link"]), "status":scalar(rec,f["status"]), "calendar_event_id":scalar(rec,f["calendar_id"]), "calendar_status":scalar(rec,f["calendar_status"]), "attachment_metadata":attachment_metadata(rec,f["attachments"])}
            elif table_name == "Documents":
                props = {"title":name, "notes":scalar(rec,f["notes"]), "status":scalar(rec,f["status"]), "attachment_metadata":attachment_metadata(rec,f["attachments"])}
                for project in linked(rec,f["projects"]):
                    add_edge(project,"HAS_DOCUMENT",rec["id"])
                    add_edge(rec["id"],"BELONGS_TO",project)
                for person_name in collaborators(rec,f["assignees"]):
                    target = names_to_id.get(person_name.casefold())
                    if target: add_edge(target,"ASSIGNED_TO",rec["id"])
                    else: unresolved.add(person_name)
            props.update({"source_base_id":BASE_ID,"source_table_id":table_id,"source_table_name":table_name,"schema_version":SCHEMA_VERSION,"source_snapshot_present":True})
            entities.append({"id":rec["id"],"label":label,"name":name,"source_system":SOURCE_SYSTEM,"source_id":rec["id"],"properties":props})
    if unresolved:
        raise ValueError("Unmatched Airtable collaborator names: " + ", ".join(sorted(unresolved)))
    allowed = {"HAS_TASK","BELONGS_TO","HAS_SUBTASK","PARTICIPATES_IN","ASSIGNED_TO","LEADS","HAS_DOCUMENT"}
    if any(rel not in allowed for _,rel,_ in edges):
        raise ValueError("Unsupported Airtable edge in generated snapshot")
    return entities, sorted(edges), record_table


def export_backup(session):
    nodes = [dict(r) for r in session.run(
        "MATCH (n) WHERE n.id=$w OR n.workspace_id=$w "
        "RETURN elementId(n) AS element_id, labels(n) AS labels, properties(n) AS properties ORDER BY n.id", w=WORKSPACE)]
    edges = [dict(r) for r in session.run(
        "MATCH (a)-[r]->(b) WHERE (a.id=$w OR a.workspace_id=$w) AND (b.id=$w OR b.workspace_id=$w) "
        "RETURN a.id AS source,b.id AS target,type(r) AS type,properties(r) AS properties ORDER BY source,type,target", w=WORKSPACE)]
    backup_dir = ROOT / ".migration-backups"
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    path = backup_dir / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-airtable-content.json")
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(_json_safe({"database":"neo4j","workspace":WORKSPACE,"nodes":nodes,"edges":edges}),f,ensure_ascii=False)
    return str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--input", type=Path, help="JSON snapshot path; defaults to one JSON line on stdin")
    args = parser.parse_args()
    snapshot = json.loads(args.input.read_text() if args.input else sys.stdin.readline())
    entities, edges, record_table = build_snapshot(snapshot)
    counts = {label:sum(e["label"]==label for e in entities) for _,label in TABLES.values()}
    print(json.dumps({"mode":"apply" if args.apply else "dry-run","entities":counts,"relationships":len(edges),"workspace":WORKSPACE},ensure_ascii=False))
    if not args.apply:
        return
    password = os.environ.get("NEO4J_PASSWORD") or subprocess.check_output(
        ["security","find-generic-password","-s","codex.neo4j-agent-memory","-a","neo4j","-w"],text=True).strip()
    with GraphDatabase.driver("neo4j://127.0.0.1:7687",auth=("neo4j",password)) as driver:
        with driver.session(database="neo4j") as session:
            backup = export_backup(session)
            previous_nodes = session.run("MATCH (n {workspace_id:$w}) RETURN count(n) AS n",w=WORKSPACE).single()["n"]
            previous_edges = session.run("MATCH (a {workspace_id:$w})-[r]->(b {workspace_id:$w}) RETURN count(r) AS n",w=WORKSPACE).single()["n"]
            existing_ids = {r["id"] for r in session.run("MATCH (n {workspace_id:$w}) RETURN n.id AS id",w=WORKSPACE)}
            alias_rows = [dict(r) for r in session.run("MATCH (n:Team {workspace_id:$w}) RETURN n.id AS id,n.name AS name,n.aliases AS aliases",w=WORKSPACE)]
            team_names = {e["id"]:e["name"] for e in entities if e["label"]=="Team"}
            aliases = {}
            for row in alias_rows:
                new_name=team_names.get(row["id"])
                kept=[a for a in (row["aliases"] or []) if a.casefold()!=new_name.casefold()] if new_name else list(row["aliases"] or [])
                if row["name"] and new_name and row["name"].casefold()!=new_name.casefold(): kept.append(row["name"])
                aliases[row["id"]]=kept
            for alias, canonical in {"PF":"Paulo Rezende","Tams":"Tamara Braga"}.items():
                target = next((e["id"] for e in entities if e["label"]=="Team" and e["name"].casefold()==canonical.casefold()),None)
                if target: aliases.setdefault(target,[]).append(alias)
            for entity in entities:
                if entity["label"]=="Team":
                    entity["properties"]["aliases"] = list(dict.fromkeys(aliases.get(entity["id"],[])))

            def write(tx):
                for label in dict.fromkeys(e["label"] for e in entities):
                    canonical = {"Setor":"Project","Team":"Person","Subtask":"Task"}.get(label,label)
                    rows = [e for e in entities if e["label"]==label]
                    result = tx.run(
                        f"UNWIND $rows AS row MERGE (n:{canonical} {{workspace_id:$w,id:row.id}}) SET n:{label}, n.name=row.name,n.source_system=row.source_system,n.source_id=row.source_id,n += row.properties MERGE (workspace:Workspace {{id:$w}}) MERGE (workspace)-[:CONTAINS]->(n) RETURN count(n) AS count",
                        rows=rows,w=WORKSPACE).single()
                    if result["count"]!=len(rows): raise ValueError("Entity count mismatch during import")
                active_ids=[e["id"] for e in entities]
                tx.run("MATCH (n {workspace_id:$w}) WHERE n.source_base_id=$base SET n.source_snapshot_present=n.id IN $ids",w=WORKSPACE,base=BASE_ID,ids=active_ids).consume()
                tx.run("MATCH (a {workspace_id:$w})-[r]->(b {workspace_id:$w}) WHERE r.provenance='IMPORTED' AND type(r) IN $types AND (a.id IN $ids OR b.id IN $ids) DELETE r",w=WORKSPACE,types=["HAS_TASK","BELONGS_TO","HAS_SUBTASK","PARTICIPATES_IN","ASSIGNED_TO","LEADS","HAS_DOCUMENT"],ids=active_ids).consume()
                rel_rows=[{"source":s,"target":t,"type":r} for s,r,t in edges]
                for rel in dict.fromkeys(e["type"] for e in rel_rows):
                    rows=[e for e in rel_rows if e["type"]==rel]
                    tx.run(f"UNWIND $rows AS row MATCH (a {{workspace_id:$w,id:row.source}}) MATCH (b {{workspace_id:$w,id:row.target}}) MERGE (a)-[r:{rel}]->(b) SET r.provenance='IMPORTED',r.review_state='IMPORTED',r.source_system=$source,r.source_base_id=$base,r.updated_at=datetime()",rows=rows,w=WORKSPACE,source=SOURCE_SYSTEM,base=BASE_ID).consume()
                current_nodes=tx.run("MATCH (n {workspace_id:$w}) RETURN count(n) AS n",w=WORKSPACE).single()["n"]
                current_edges=tx.run("MATCH (a {workspace_id:$w})-[r]->(b {workspace_id:$w}) RETURN count(r) AS n",w=WORKSPACE).single()["n"]
                if current_nodes != previous_nodes + sum(e["id"] not in existing_ids for e in entities):
                    raise ValueError("Unexpected node-count change during import")
                return current_nodes,current_edges
            node_count,edge_count=session.execute_write(write)
            print(json.dumps({"imported":counts,"current_source_records":len(entities),"source_relationships":len(edges),"workspace_nodes":node_count,"workspace_edges":edge_count,"previous_workspace_nodes":previous_nodes,"previous_workspace_edges":previous_edges,"backup":backup},ensure_ascii=False))


if __name__ == "__main__":
    main()
