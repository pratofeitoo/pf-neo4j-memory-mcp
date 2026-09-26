from __future__ import annotations

from typing import Any

from neo4j import Driver

from .models import DocumentInput, EntityInput, EntityRef, Scope

ALLOWED_LABELS = {"Project", "Task", "Client", "Partner", "Person"}
ALLOWED_LINK_TYPES = {"Project", "Task", "Client", "Partner", "Person"}
ALLOWED_PROPERTIES = {
    "Project": {"status", "summary", "start_at", "due_at"},
    "Task": {"status", "priority", "description", "due_at", "completed_at"},
    "Client": {"external_ref", "website"},
    "Partner": {"external_ref", "website"},
    "Person": {"external_ref", "email"},
}
ALLOWED_LINKS = {
    ("Project", "HAS_TASK", "Task"),
    ("Project", "FOR_CLIENT", "Client"),
    ("Project", "WITH_PARTNER", "Partner"),
    ("Person", "ASSIGNED_TO", "Task"),
    ("Person", "PARTICIPATES_IN", "Project"),
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
        # The dimension is validated numeric configuration, embedded as a Cypher literal.
        vector_statement = (
            "CYPHER 25 CREATE VECTOR INDEX memory_chunk_embedding IF NOT EXISTS "
            "FOR (c:DocumentChunk) ON c.embedding WITH [c.workspace_id] "
            "OPTIONS {indexConfig: {"
            f"`vector.dimensions`: {int(self.embedding_dimensions)}, "
            "`vector.similarity_function`: 'cosine'}}"
        )
        with self.driver.session(database=self.database) as session:
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
        query = f"""
        MERGE (w:Workspace {{id: $workspace_id}})
        ON CREATE SET w.created_at = datetime()
        MERGE (n:{entity.entity_type} {{workspace_id: $workspace_id, id: $entity_id}})
        ON CREATE SET n.created_at = datetime()
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
            if existing and existing["properties"].get("checksum") != content_checksum:
                tx.run(
                    "MATCH (d:Document {workspace_id:$workspace_id, id:$document_id}) "
                    "OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:DocumentChunk) DETACH DELETE c",
                    workspace_id=scope.workspace_id,
                    document_id=existing["id"],
                ).consume()
                document_id = existing["id"]
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
               collect(DISTINCT {type: labels(e)[0], id:e.id, name:e.name,
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
        OPTIONAL MATCH (p:Project {workspace_id:$workspace_id})-[:HAS_TASK]->(t)
        OPTIONAL MATCH (person:Person {workspace_id:$workspace_id})-[:ASSIGNED_TO]->(t)
        OPTIONAL MATCH (d:Document {workspace_id:$workspace_id})-[:RELATES_TO]->(t)
        RETURN t {.*, labels: labels(t)} AS task,
               collect(DISTINCT p {.*, labels: labels(p)}) AS projects,
               collect(DISTINCT person {.*, labels: labels(person)}) AS assignees,
               collect(DISTINCT d {.*, labels: labels(d)}) AS documents
        """
        with self.driver.session(database=self.database) as session:
            record = session.run(
                query, workspace_id=scope.workspace_id, task_id=task_id
            ).single()
        return dict(record) if record else None
