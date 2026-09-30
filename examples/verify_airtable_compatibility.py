"""Exercise source/legacy label compatibility with temporary synthetic records."""
import subprocess
import uuid
from neo4j import GraphDatabase
from neo4j_agent_memory.models import EntityInput, EntityRef, Scope
from neo4j_agent_memory.store import Neo4jStore


def main():
    password = subprocess.check_output(["security", "find-generic-password", "-s", "codex.neo4j-agent-memory", "-a", "neo4j", "-w"], text=True).strip()
    workspace = "schema-verification-" + uuid.uuid4().hex
    with GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", password)) as driver:
        store = Neo4jStore(driver, "neo4j", 1536)
        scope = Scope(workspace)
        with driver.session(database="neo4j") as session:
            baseline = session.run("MATCH (n) RETURN count(n) AS n").single()["n"]
        try:
            for label, props in [("Setor",{}),("Team",{"aliases":["Example Alias"]}),("Task",{"updates":"Synthetic update"}),("Subtask",{"complete":False,"date":"2026-09-30"}),("Meeting",{"calendar_status":"confirmed"}),("Document",{"status":"Todo"})]:
                store.upsert_entity(scope, EntityInput(label,label,"Synthetic "+label,"synthetic-verification",label,props))
            # Legacy calls must reuse the same nodes created through source labels.
            store.upsert_entity(scope, EntityInput("Project","Setor","Synthetic Setor","synthetic-verification","Setor"))
            store.upsert_entity(scope, EntityInput("Person","Team","Synthetic Team","synthetic-verification","Team"))
            store.upsert_entity(scope, EntityInput("Task","Subtask","Synthetic Subtask","synthetic-verification","Subtask"))
            for source, rel, target in [("Setor","HAS_TASK","Task"),("Task","HAS_SUBTASK","Subtask"),("Setor","HAS_SUBTASK","Subtask"),("Team","ASSIGNED_TO","Task"),("Team","ASSIGNED_TO","Subtask"),("Document","BELONGS_TO","Setor")]:
                store.link_entities(scope,EntityRef(source,source),EntityRef(target,target),rel,"USER_LINKED","USER_LINKED")
            context = store.get_task_context(scope,"Task")
            child = store.get_task_context(scope,"Subtask")
            assert len(context["projects"])==1 and len(context["assignees"])==1 and len(context["subtasks"])==1
            assert len(child["parent_tasks"])==1 and len(child["projects"])==1 and "Subtask" in child["task"]["labels"]
            with driver.session(database="neo4j") as session:
                count=session.run("MATCH (n {workspace_id:$w}) RETURN count(n) AS n",w=workspace).single()["n"]
                assert count==6, "Alias upserts created duplicate entities"
            print("Source/legacy upserts, typed links, parent context, and duplicate prevention passed")
        finally:
            with driver.session(database="neo4j") as session:
                session.run("MATCH (n {workspace_id:$w}) DETACH DELETE n",w=workspace).consume()
                session.run("MATCH (w:Workspace {id:$w}) DETACH DELETE w",w=workspace).consume()
                assert session.run("MATCH (n) RETURN count(n) AS n").single()["n"]==baseline
            print("Temporary synthetic verification workspace removed; original node count restored")


if __name__ == "__main__":
    main()
