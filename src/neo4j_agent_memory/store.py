from __future__ import annotations

from typing import Any

from neo4j import Driver

from .models import DocumentInput, EntityInput, EntityRef, Scope

COMPATIBILITY_LABELS = {"Setor": "Project", "Team": "Person", "Subtask": "Task"}
ALLOWED_LABELS = {"Project", "Setor", "Task", "Subtask", "Client", "Partner", "Person", "Team", "Meeting", "Document"}
ALLOWED_LINK_TYPES = ALLOWED_LABELS
ALLOWED_PROPERTIES = {
    "Project": {"status", "summary", "start_at", "due_at"},
    "Task": {"status", "priority", "description", "updates", "drive_folder_url", "due_at", "completed_at", "complete", "date", "source_option_id", "attachment_metadata"},
    "Client": {"external_ref", "website"},
    "Partner": {"external_ref", "website"},
    "Person": {"external_ref", "email", "role", "aliases", "photo_metadata", "slack_dm_url"},
    "Meeting": {"date", "notes", "link", "status", "calendar_event_id", "calendar_status", "attachment_urls", "attachment_metadata"},
    "Document": {"title", "status", "notes", "attachment_urls", "attachment_metadata", "source_uri", "mime_type"},
}
ALLOWED_PROPERTIES["Project"] |= {"project_lead_text", "legacy_external_record_id", "related_projects_text"}
ALLOWED_PROPERTIES["Person"] |= {"bio", "photo_urls", "slack_dm_url"}
for alias, canonical in COMPATIBILITY_LABELS.items():
    ALLOWED_PROPERTIES[alias] = ALLOWED_PROPERTIES[canonical]
SOURCE_PROPERTIES = {"source_base_id", "source_table_id", "source_table_name", "schema_version", "source_snapshot_present"}
for properties in ALLOWED_PROPERTIES.values():
    properties.update(SOURCE_PROPERTIES)
ALLOWED_LINKS = {
    ("Project", "HAS_TASK", "Task"),
    ("Task", "BELONGS_TO", "Project"),
    ("Task", "HAS_SUBTASK", "Task"),
    ("Project", "FOR_CLIENT", "Client"),
    ("Project", "WITH_PARTNER", "Partner"),
    ("Person", "ASSIGNED_TO", "Task"),
    ("Person", "PARTICIPATES_IN", "Project"),
    ("Person", "LEADS", "Project"),
    ("Project", "HAS_SUBTASK", "Task"),
    ("Task", "BELONGS_TO", "Task"),
    ("Project", "HAS_DOCUMENT", "Document"),
    ("Document", "BELONGS_TO", "Project"),
    ("Person", "ASSIGNED_TO", "Document"),
}
ALLOWED_LINKS |= {
    (source, relation, target)
    for source in ALLOWED_LABELS for target in ALLOWED_LABELS
    for canonical_source, relation, canonical_target in tuple(ALLOWED_LINKS)
    if COMPATIBILITY_LABELS.get(source, source) == canonical_source
    and COMPATIBILITY_LABELS.get(target, target) == canonical_target
}
ALLOWED_PROVENANCE = {"USER_LINKED", "IMPORTED", "EXTRACTED"}
ALLOWED_REVIEW_STATES = {"USER_LINKED", "IMPORTED", "PROPOSED", "REVIEWED"}


class Neo4jStore:
    def __init__(self, driver: Driver, database: str, embedding_dimensions: int):
        self.driver = driver
        self.database = database
        self.embedding_dimensions = embedding_dimensions

    def initialize(self) -> None:
        statements = [
            "CREATE CONSTRAINT workspace_id IF NOT EXISTS FOR (n:Workspace) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (n:Project) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
            "CREATE CONSTRAINT task_id IF NOT EXISTS FOR (n:Task) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
            "CREATE CONSTRAINT client_id IF NOT EXISTS FOR (n:Client) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
            "CREATE CONSTRAINT partner_id IF NOT EXISTS FOR (n:Partner) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
            "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
            "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
            "CREATE CONSTRAINT document_source_key IF NOT EXISTS FOR (n:Document) REQUIRE (n.workspace_id, n.source_system, n.source_id) IS UNIQUE",
            "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (n:DocumentChunk) REQUIRE (n.workspace_id, n.id) IS UNIQUE",
        ]
        for label in ("Setor", "Team", "Subtask", "Meeting"):
            statements.append(f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS FOR (n:{label}) REQUIRE (n.workspace_id, n.id) IS UNIQUE")
        # The dimension is validated numeric configuration, embedded as a Cypher literal.
        vector_statement = (
            "CYPHER 25 CREATE VECTOR INDEX memory_chunk_embedding IF NOT EXISTS "
            "FOR (c:DocumentChunk) ON c.embedding WITH [c.workspace_id] "
            "OPTIONS {indexConfig: {"
            f"`vector.dimensions`: {int(self.embedding_dimensions)}, "
            "`vector.similarity_function`: 'cosine'}}"
        )
        with self.driver.session(database=self.database) as session:
            existing = session.run(
                "SHOW VECTOR INDEXES YIELD name, options WHERE name = 'memory_chunk_embedding' "
                "RETURN options"
            ).single()
            if existing:
                configured = existing["options"].get("indexConfig", {}).get("vector.dimensions")
                if configured != self.embedding_dimensions:
                    raise RuntimeError(
                        f"memory_chunk_embedding has {configured} dimensions, but the configured "
                        f"provider requires {self.embedding_dimensions}; run the reviewed index migration"
                    )
            for statement in statements:
                session.run(statement).consume()
            session.run(vector_statement).consume()
            session.run(
                "CREATE FULLTEXT INDEX memory_chunk_text IF NOT EXISTS "
                "FOR (c:DocumentChunk) ON EACH [c.text]"
            ).consume()

    def upsert_entity(self, scope: Scope, entity: EntityInput) -> dict[str, Any]:
        if entity.entity_type not in ALLOWED_LABELS:
            raise ValueError("Unsupported entity type")
        if not entity.entity_id.strip() or not entity.name.strip():
            raise ValueError("Entity ID and name are required")
        if not entity.source_system.strip() or not entity.source_id.strip():
            raise ValueError("source_system and source_id are required")
        invalid_properties = set(entity.properties) - ALLOWED_PROPERTIES[entity.entity_type]
        if invalid_properties:
            raise ValueError(f"Unsupported {entity.entity_type} properties: {sorted(invalid_properties)}")
        canonical_label = COMPATIBILITY_LABELS.get(entity.entity_type, entity.entity_type)
        query = f"""
        MERGE (w:Workspace {{id: $workspace_id}})
        ON CREATE SET w.created_at = datetime()
        MERGE (n:{canonical_label} {{workspace_id: $workspace_id, id: $entity_id}})
        ON CREATE SET n.created_at = datetime()
        SET n:{entity.entity_type}
        SET n.name = $name, n.source_system = $source_system,
            n.source_id = $source_id, n.updated_at = datetime(),
            n += $properties
        MERGE (w)-[:CONTAINS]->(n)
        RETURN n.id AS id, labels(n) AS labels, n.name AS name
        """
        with self.driver.session(database=self.database) as session:
            record = session.run(
                query,
                workspace_id=scope.workspace_id,
                entity_id=entity.entity_id,
                name=entity.name.strip(),
                source_system=entity.source_system,
                source_id=entity.source_id,
                properties=entity.properties,
            ).single()
        return dict(record)

    def link_entities(
        self,
        scope: Scope,
        source: EntityRef,
        target: EntityRef,
        relationship_type: str,
        provenance: str,
        review_state: str,
    ) -> None:
        if source.entity_type not in ALLOWED_LABELS or target.entity_type not in ALLOWED_LABELS:
            raise ValueError("Unsupported entity type")
        if (source.entity_type, relationship_type, target.entity_type) not in ALLOWED_LINKS:
            raise ValueError("Unsupported source, relationship, and target combination")
        if provenance not in ALLOWED_PROVENANCE or review_state not in ALLOWED_REVIEW_STATES:
            raise ValueError("Unsupported provenance or review state")
        if not source.entity_id.strip() or not target.entity_id.strip():
            raise ValueError("Both entity IDs are required")
        query = f"""
        MATCH (a:{source.entity_type} {{workspace_id: $workspace_id, id: $source_id}})
        MATCH (b:{target.entity_type} {{workspace_id: $workspace_id, id: $target_id}})
        MERGE (a)-[r:{relationship_type}]->(b)
        SET r.provenance = $provenance, r.review_state = $review_state,
            r.updated_at = datetime()
        RETURN count(r) AS linked
        """
        with self.driver.session(database=self.database) as session:
            record = session.run(
                query,
                workspace_id=scope.workspace_id,
                source_id=source.entity_id,
                target_id=target.entity_id,
                provenance=provenance,
                review_state=review_state,
            ).single()
        if not record or record["linked"] != 1:
            raise ValueError("Entity link target was not found in this workspace")

    def ingest_document(
        self,
        scope: Scope,
        document: DocumentInput,
        document_id: str,
        content_checksum: str,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:
        def write_document(tx: Any) -> None:
            nonlocal document_id
            existing = tx.run(
                "MATCH (d:Document {workspace_id:$workspace_id, source_system:$source_system, source_id:$source_id}) "
                "RETURN d.id AS id, properties(d) AS properties",
                workspace_id=scope.workspace_id,
                source_system=document.source_system,
                source_id=document.source_id,
            ).single()
            if existing:
                document_id = existing["id"]
                if existing["properties"].get("checksum") != content_checksum:
                    tx.run(
                        "MATCH (d:Document {workspace_id:$workspace_id, id:$document_id}) "
                        "OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk) DETACH DELETE c",
                        workspace_id=scope.workspace_id,
                        document_id=document_id,
                    ).consume()
            tx.run(
                "MERGE (w:Workspace {id:$workspace_id}) ON CREATE SET w.created_at=datetime() "
                "MERGE (d:Document {workspace_id:$workspace_id, id:$document_id}) "
                "SET d.title=$title, d.mime_type=$mime_type, d.source_system=$source_system, "
                "d.source_id=$source_id, d.source_uri=$source_uri, d.checksum=$checksum, "
                "d.updated_at=datetime() MERGE (w)-[:CONTAINS]->(d)",
                workspace_id=scope.workspace_id,
                document_id=document_id,
                title=document.title,
                mime_type=document.mime_type,
                source_system=document.source_system,
                source_id=document.source_id,
                source_uri=document.source_uri,
                checksum=content_checksum,
            ).consume()
            tx.run(
                "MATCH (d:Document {workspace_id:$workspace_id,id:$document_id}) "
                "OPTIONAL MATCH (d)-[r:RELATES_TO]->() DELETE r",
                workspace_id=scope.workspace_id,
                document_id=document_id,
            ).consume()
            for linked in document.linked_entities:
                if linked.entity_type not in ALLOWED_LINK_TYPES:
                    raise ValueError("Unsupported linked entity type")
                result = tx.run(
                    f"MATCH (d:Document {{workspace_id:$workspace_id,id:$document_id}}) "
                    f"MATCH (e:{linked.entity_type} {{workspace_id:$workspace_id,id:$entity_id}}) "
                    "MERGE (d)-[r:RELATES_TO]->(e) "
                    "SET r.provenance=$provenance, r.review_state=$review_state, r.updated_at=datetime() "
                    "RETURN count(r) AS linked",
                    workspace_id=scope.workspace_id,
                    document_id=document_id,
                    entity_id=linked.entity_id,
                    provenance=document.link_provenance,
                    review_state=document.link_review_state,
                ).single()
                if not result or result["linked"] != 1:
                    raise ValueError(f"Linked entity {linked.entity_id} is not in this workspace")
            for chunk in chunks:
                tx.run(
                    "MATCH (d:Document {workspace_id:$workspace_id,id:$document_id}) "
                    "MERGE (c:DocumentChunk {workspace_id:$workspace_id,id:$chunk_id}) "
                    "SET c.ordinal=$ordinal, c.text=$text, c.locator=$locator, "
                    "c.embedding=$embedding, c.embedding_model=$embedding_model, "
                    "c.embedding_dimensions=$embedding_dimensions, c.updated_at=datetime() "
                    "MERGE (d)-[:HAS_CHUNK]->(c)",
                    workspace_id=scope.workspace_id,
                    document_id=document_id,
                    chunk_id=chunk["id"],
                    ordinal=chunk["ordinal"],
                    text=chunk["text"],
                    locator=chunk["locator"],
                    embedding=chunk["embedding"],
                    embedding_model=chunk["embedding_model"],
                    embedding_dimensions=chunk["embedding_dimensions"],
                ).consume()
        with self.driver.session(database=self.database) as session:
            session.execute_write(write_document)
        return {"document_id": document_id, "chunk_count": len(chunks), "checksum": content_checksum}

    def search_chunks(
        self,
        scope: Scope,
        vector: list[float],
        model: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        query = """
        CYPHER 25
        MATCH (c:DocumentChunk)
        SEARCH c IN (
            VECTOR INDEX memory_chunk_embedding
            FOR $vector
            WHERE c.workspace_id = $workspace_id
            LIMIT $candidate_limit
        ) SCORE AS score
        WHERE c.embedding_model = $embedding_model
        MATCH (d:Document {workspace_id:$workspace_id})-[:HAS_CHUNK]->(c)
        OPTIONAL MATCH (d)-[r:RELATES_TO]->(e)
        RETURN score, c.id AS chunk_id, c.text AS text, c.locator AS locator,
               d.id AS document_id, d.title AS title, d.source_uri AS source_uri,
               collect(DISTINCT {type: CASE WHEN e:Setor THEN 'Setor' WHEN e:Team THEN 'Team' WHEN e:Subtask THEN 'Subtask' ELSE labels(e)[0] END, id:e.id, name:e.name,
                                 provenance:r.provenance, review_state:r.review_state}) AS entities
        ORDER BY score DESC LIMIT $limit
        """
        with self.driver.session(database=self.database) as session:
            return [dict(record) for record in session.run(
                query,
                limit=limit,
                vector=vector,
                candidate_limit=limit * 5,
                workspace_id=scope.workspace_id,
                embedding_model=model,
            )]

    def get_task_context(self, scope: Scope, task_id: str) -> dict[str, Any] | None:
        query = """
        MATCH (t:Task {workspace_id:$workspace_id,id:$task_id})
        OPTIONAL MATCH (p:Project {workspace_id:$workspace_id})
        WHERE EXISTS { MATCH (p)-[:HAS_TASK]->(t) }
           OR EXISTS { MATCH (t)-[:BELONGS_TO]->(p) }
           OR EXISTS { MATCH (p)-[:HAS_SUBTASK]->(t) }
        OPTIONAL MATCH (person:Person {workspace_id:$workspace_id})-[:ASSIGNED_TO]->(t)
        OPTIONAL MATCH (project_lead:Person {workspace_id:$workspace_id})-[:LEADS]->(p)
        OPTIONAL MATCH (project_member:Person {workspace_id:$workspace_id})-[:PARTICIPATES_IN]->(p)
        OPTIONAL MATCH (t)-[:HAS_SUBTASK]->(subtask:Task {workspace_id:$workspace_id})
        OPTIONAL MATCH (parent:Task {workspace_id:$workspace_id})-[:HAS_SUBTASK]->(t)
        OPTIONAL MATCH (d:Document {workspace_id:$workspace_id})-[:RELATES_TO]->(t)
        RETURN t {.*, labels: labels(t)} AS task,
               collect(DISTINCT p {.*, labels: labels(p)}) AS projects,
               collect(DISTINCT person {.*, labels: labels(person)}) AS assignees,
               collect(DISTINCT project_lead {.*, labels: labels(project_lead)}) AS project_leads,
               collect(DISTINCT project_member {.*, labels: labels(project_member)}) AS project_members,
               collect(DISTINCT subtask {.*, labels: labels(subtask)}) AS subtasks,
               collect(DISTINCT parent {.*, labels: labels(parent)}) AS parent_tasks,
               collect(DISTINCT d {.*, labels: labels(d)}) AS documents
        """
        with self.driver.session(database=self.database) as session:
            record = session.run(
                query, workspace_id=scope.workspace_id, task_id=task_id
            ).single()
        if not record:
            return None
        result = dict(record)
        result["setores"] = [p for p in result["projects"] if "Setor" in p["labels"]]
        result["team_assignees"] = [p for p in result["assignees"] if "Team" in p["labels"]]
        return result
