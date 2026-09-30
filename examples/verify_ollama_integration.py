"""End-to-end synthetic Ollama/Neo4j check in an isolated disposable workspace."""

from __future__ import annotations

import os
import uuid

from neo4j import GraphDatabase

from neo4j_agent_memory.embedding import OllamaEmbeddingProvider
from neo4j_agent_memory.models import DocumentInput, EntityInput, EntityRef, Scope
from neo4j_agent_memory.service import MemoryService
from neo4j_agent_memory.store import Neo4jStore


def main() -> None:
    database = os.environ.get("NEO4J_DATABASE", "neo4j")
    workspace_id = f"ollama-check-{uuid.uuid4()}"
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687"),
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ["NEO4J_PASSWORD"]),
    )
    provider = OllamaEmbeddingProvider(
        os.environ.get("MEMORY_EMBEDDING_MODEL", "nomic-embed-text:latest"),
        768,
        os.environ.get("MEMORY_OLLAMA_URL", "http://127.0.0.1:11434"),
        os.environ["MEMORY_OLLAMA_MODEL_DIGEST"],
    )
    store = Neo4jStore(driver, database, 768)
    service = MemoryService(store, provider, Scope(workspace_id))
    try:
        store.initialize()
        service.upsert_entity(EntityInput("Task", "test-task", "Synthetic delivery review", "synthetic-test", "test-task"))
        result = service.ingest_text_document(DocumentInput(
            source_system="synthetic-test",
            source_id="test-note",
            title="Synthetic delivery note",
            text="The synthetic delivery review task covers a fictional API milestone and its handoff.",
            source_uri="synthetic://ollama-test-note",
            linked_entities=(EntityRef("Task", "test-task"),),
        ))
        repeated = service.ingest_text_document(DocumentInput(
            source_system="synthetic-test",
            source_id="test-note",
            title="Synthetic delivery note",
            text="The synthetic delivery review task covers a fictional API milestone and its handoff.",
            source_uri="synthetic://ollama-test-note",
            linked_entities=(EntityRef("Task", "test-task"),),
        ))
        assert repeated["document_id"] == result["document_id"]
        portuguese = service.ingest_text_document(DocumentInput(
            source_system="synthetic-test",
            source_id="test-note-pt",
            title="Nota sintética de cronograma",
            text="O cronograma fictício de implantação do Projeto Aurora prevê uma revisão de orçamento em outubro.",
            source_uri="synthetic://ollama-test-note-pt",
        ))
        hits = service.search_memory("Which fictional task covers the API milestone?")
        assert result["chunk_count"] == 1
        assert portuguese["chunk_count"] == 1
        assert hits and hits[0]["source_uri"] == "synthetic://ollama-test-note"
        assert any(entity["id"] == "test-task" for entity in hits[0]["entities"])
        portuguese_hits = service.search_memory("Qual é o cronograma de implantação do Projeto Aurora?")
        assert portuguese_hits and portuguese_hits[0]["source_uri"] == "synthetic://ollama-test-note-pt"
        other_scope = MemoryService(store, provider, Scope("airtable-pilot"))
        assert all(hit["document_id"] != result["document_id"] for hit in other_scope.search_memory("fictional API milestone"))
        print(f"verified English and Portuguese synthetic retrieval, citation, entity link, and workspace isolation in {database}")
    finally:
        with driver.session(database=database) as session:
            session.run("MATCH (n {workspace_id:$workspace_id}) DETACH DELETE n", workspace_id=workspace_id).consume()
            session.run("MATCH (w:Workspace {id:$workspace_id}) DETACH DELETE w", workspace_id=workspace_id).consume()
        driver.close()


if __name__ == "__main__":
    main()
