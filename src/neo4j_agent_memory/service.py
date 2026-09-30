from __future__ import annotations

import hashlib
import uuid
from typing import Any

from .chunking import checksum, chunk_text
from .embedding import EmbeddingProvider
from .models import DocumentInput, EntityInput, Scope
from .store import Neo4jStore, ALLOWED_LINK_TYPES

_NAMESPACE = uuid.UUID("3a21dd3c-bf20-4bbb-91cf-1096a41baf0e")
_ALLOWED_MIME_TYPES = {"text/plain", "text/markdown"}
_ALLOWED_LINK_PROVENANCE = {"USER_LINKED", "IMPORTED", "EXTRACTED"}
_ALLOWED_LINK_REVIEW_STATES = {"USER_LINKED", "IMPORTED", "PROPOSED", "REVIEWED"}
_MAX_DOCUMENT_CHARACTERS = 2_000_000


class MemoryService:
    def __init__(self, store: Neo4jStore, embedding_provider: EmbeddingProvider, scope: Scope):
        self.store = store
        self.embedding_provider = embedding_provider
        self.scope = scope

    def upsert_entity(self, item: EntityInput) -> dict[str, Any]:
        return self.store.upsert_entity(self.scope, item)

    def ingest_text_document(self, item: DocumentInput) -> dict[str, Any]:
        if item.mime_type not in _ALLOWED_MIME_TYPES:
            raise ValueError("Only plain text and Markdown documents are supported in this slice")
        if not item.source_system.strip() or not item.source_id.strip() or not item.title.strip():
            raise ValueError("source_system, source_id, and title are required")
        if not item.text.strip():
            raise ValueError("Document text must not be empty")
        if len(item.text) > _MAX_DOCUMENT_CHARACTERS:
            raise ValueError("Document exceeds the 2,000,000 character limit")
        if item.link_provenance not in _ALLOWED_LINK_PROVENANCE:
            raise ValueError("Unsupported link provenance")
        if item.link_review_state not in _ALLOWED_LINK_REVIEW_STATES:
            raise ValueError("Unsupported link review state")
        if any(ref.entity_type not in ALLOWED_LINK_TYPES for ref in item.linked_entities):
            raise ValueError("Unsupported linked entity type")

        source_key = f"{self.scope.workspace_id}:{item.source_system}:{item.source_id}"
        document_id = str(uuid.uuid5(_NAMESPACE, source_key))
        text_checksum = checksum(item.text)
        pieces = chunk_text(item.text)
        chunks: list[dict[str, Any]] = []
        for ordinal, (text, locator) in enumerate(pieces):
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            chunk_id = str(uuid.uuid5(_NAMESPACE, f"{document_id}:{ordinal}:{digest}"))
            chunks.append(
                {
                    "id": chunk_id,
                    "ordinal": ordinal,
                    "text": text,
                    "locator": locator,
                    "embedding": self.embedding_provider.embed(text),
                    "embedding_model": self.embedding_provider.model,
                    "embedding_dimensions": self.embedding_provider.dimensions,
                }
            )
        return self.store.ingest_document(
            self.scope, item, document_id, text_checksum, chunks
        )

    def search_memory(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        vector = self.embedding_provider.embed(query)
        return self.store.search_chunks(
            self.scope, vector, self.embedding_provider.model, limit
        )

    def get_task_context(self, task_id: str) -> dict[str, Any] | None:
        if not task_id.strip():
            raise ValueError("task_id must not be empty")
        return self.store.get_task_context(self.scope, task_id)
