from __future__ import annotations

import os
import ipaddress
from collections.abc import Mapping
from urllib.parse import urlsplit
from typing import Any

from neo4j import GraphDatabase
from mcp.server.fastmcp import FastMCP

from .embedding import OpenAIEmbeddingProvider
from .models import DocumentInput, EntityInput, EntityRef, Scope
from .service import MemoryService
from .store import Neo4jStore


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value.__class__.__module__.startswith("neo4j.time"):
        return value.iso_format() if hasattr(value, "iso_format") else str(value)
    return value


def create_service() -> tuple[MemoryService, Any]:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    username = os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE", "codex-mem-01")
    workspace_id = os.environ.get("MEMORY_WORKSPACE_ID")
    if not username or not password or not workspace_id:
        raise RuntimeError("Set NEO4J_USERNAME, NEO4J_PASSWORD, and MEMORY_WORKSPACE_ID")
    hostname = urlsplit(uri).hostname
    if not hostname or not (
        hostname.lower() == "localhost"
        or (ipaddress.ip_address(hostname).is_loopback if _is_ip_address(hostname) else False)
    ):
        raise RuntimeError("This initial server only supports a loopback Neo4j URI")

    dimensions = int(os.environ.get("MEMORY_EMBEDDING_DIMENSIONS", "1536"))
    if not 1 <= dimensions <= 4096:
        raise RuntimeError("MEMORY_EMBEDDING_DIMENSIONS must be between 1 and 4096")
    model = os.environ.get("MEMORY_EMBEDDING_MODEL", "text-embedding-3-small")
    driver = GraphDatabase.driver(uri, auth=(username, password))
    store = Neo4jStore(driver, database, dimensions)
    service = MemoryService(store, OpenAIEmbeddingProvider(model, dimensions), Scope(workspace_id))
    return service, driver


def _is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def build_mcp(service: MemoryService) -> FastMCP:
    mcp = FastMCP("neo4j-agent-memory")

    @mcp.tool()
    def initialize_memory_schema() -> str:
        """Create the package constraints and indexes in the configured local database."""
        service.store.initialize()
        return "Memory schema initialized."

    @mcp.tool()
    def upsert_memory_entity(
        entity_type: str,
        entity_id: str,
        name: str,
        source_system: str,
        source_id: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a Project, Task, Client, Partner, or Person in the configured workspace."""
        if entity_type not in {"Project", "Task", "Client", "Partner", "Person"}:
            raise ValueError("entity_type must be Project, Task, Client, Partner, or Person")
        return service.upsert_entity(
            EntityInput(entity_type, entity_id, name, source_system, source_id, properties or {})
        )

    @mcp.tool()
    def link_memory_entities(
        from_type: str,
        from_id: str,
        relationship_type: str,
        to_type: str,
        to_id: str,
        provenance: str = "USER_LINKED",
        review_state: str = "USER_LINKED",
    ) -> dict[str, str]:
        """Create an allowlisted typed relationship within the configured workspace."""
        service.store.link_entities(
            service.scope,
            EntityRef(from_type, from_id),
            EntityRef(to_type, to_id),
            relationship_type,
            provenance,
            review_state,
        )
        return {"status": "linked", "relationship_type": relationship_type}

    @mcp.tool()
    def ingest_text_document(
        source_system: str,
        source_id: str,
        title: str,
        text: str,
        mime_type: str = "text/plain",
        source_uri: str | None = None,
        linked_entities: list[dict[str, str]] | None = None,
        link_provenance: str = "USER_LINKED",
        link_review_state: str = "USER_LINKED",
    ) -> dict[str, Any]:
        """Ingest plain text or Markdown with stable IDs, locators, provenance, and embeddings."""
        refs = tuple(
            EntityRef(ref["entity_type"], ref["entity_id"])
            for ref in (linked_entities or [])
        )
        return service.ingest_text_document(
            DocumentInput(
                source_system=source_system,
                source_id=source_id,
                title=title,
                text=text,
                mime_type=mime_type,
                source_uri=source_uri,
                linked_entities=refs,
                link_provenance=link_provenance,
                link_review_state=link_review_state,
            )
        )

    @mcp.tool()
    def search_memory(query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search semantically in the configured workspace and return cited chunks with linked entities."""
        return service.search_memory(query, limit)

    @mcp.tool()
    def get_task_context(task_id: str) -> dict[str, Any] | None:
        """Return structured task state, project, assignees, and linked documents."""
        return _json_safe(service.get_task_context(task_id))

    return mcp


def main() -> None:
    service, driver = create_service()
    try:
        build_mcp(service).run()
    finally:
        driver.close()


if __name__ == "__main__":
    main()
