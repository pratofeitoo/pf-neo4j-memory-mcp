from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EntityType = Literal["Project", "Setor", "Task", "Subtask", "Client", "Partner", "Person", "Team", "Meeting", "Document"]
LinkReviewState = Literal["USER_LINKED", "IMPORTED", "PROPOSED", "REVIEWED"]


@dataclass(frozen=True)
class EntityRef:
    entity_type: EntityType
    entity_id: str


@dataclass(frozen=True)
class EntityInput:
    entity_type: EntityType
    entity_id: str
    name: str
    source_system: str
    source_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentInput:
    source_system: str
    source_id: str
    title: str
    text: str
    mime_type: str = "text/plain"
    source_uri: str | None = None
    linked_entities: tuple[EntityRef, ...] = ()
    link_provenance: str = "USER_LINKED"
    link_review_state: str = "USER_LINKED"


@dataclass(frozen=True)
class Scope:
    """Trusted server scope. Never construct this from tool arguments."""

    workspace_id: str


@dataclass(frozen=True)
class Citation:
    document_id: str
    title: str
    source_uri: str | None
    chunk_id: str
    locator: str
    excerpt: str


@dataclass(frozen=True)
class SearchHit:
    score: float
    citation: Citation
    related_entities: tuple[dict[str, Any], ...]
