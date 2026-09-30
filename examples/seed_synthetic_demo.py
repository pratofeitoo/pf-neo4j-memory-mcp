"""Seed a fictional, local-only graph. Demo embeddings are not production quality."""

from __future__ import annotations

import hashlib
import ipaddress
import math
import os
import re
from urllib.parse import urlsplit

from neo4j import GraphDatabase

from neo4j_agent_memory.models import DocumentInput, EntityInput, EntityRef, Scope
from neo4j_agent_memory.service import MemoryService
from neo4j_agent_memory.store import Neo4jStore


class SyntheticHashEmbeddings:
    model = "synthetic-hash-v1"
    dimensions = 1536

    def embed(self, text: str) -> list[float]:
        words = re.findall(r"[\w-]+", text.casefold())
        features = [(word, 1.0) for word in words]
        features.extend((f"{left} {right}", 0.5) for left, right in zip(words, words[1:]))
        vector = [0.0] * self.dimensions
        for feature, weight in features:
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    def embed_document(self, text: str) -> list[float]:
        return self.embed(text)

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text)


def main() -> None:
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("Set NEO4J_PASSWORD in the process environment")
    uri = os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687")
    hostname = urlsplit(uri).hostname
    is_loopback = hostname == "localhost"
    if hostname:
        try:
            is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            pass
    if not is_loopback:
        raise RuntimeError("The demo only supports a loopback Neo4j server")
    workspace_id = "local-development"
    scope = Scope(workspace_id)
    driver = GraphDatabase.driver(
        uri,
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), password),
    )
    store = Neo4jStore(driver, os.environ.get("NEO4J_DATABASE", "codex-mem-01"), 1536)
    service = MemoryService(store, SyntheticHashEmbeddings(), scope)
    try:
        store.initialize()
        entities = [
            EntityInput("Project", "demo-project-orion", "Orion Delivery", "synthetic-demo", "project-orion", {"status": "active", "summary": "Synthetic project for the first memory slice."}),
            EntityInput("Project", "demo-project-nova", "Nova Research", "synthetic-demo", "project-nova", {"status": "planning", "summary": "Second synthetic project for multi-project document links."}),
            EntityInput("Task", "demo-task-identity", "Identity mapping review", "synthetic-demo", "task-identity", {"status": "blocked", "priority": "high", "description": "Waiting for a fictional client review."}),
            EntityInput("Task", "demo-task-api", "API connector", "synthetic-demo", "task-api", {"status": "completed", "priority": "medium"}),
            EntityInput("Client", "demo-client-acme", "Acme Robotics (Synthetic)", "synthetic-demo", "client-acme"),
            EntityInput("Client", "demo-client-blue", "Blue Harbor Labs (Synthetic)", "synthetic-demo", "client-blue"),
            EntityInput("Partner", "demo-partner-northwind", "Northwind Analytics (Synthetic)", "synthetic-demo", "partner-northwind"),
            EntityInput("Person", "demo-person-avery", "Avery Example", "synthetic-demo", "person-avery"),
            EntityInput("Person", "demo-person-jordan", "Jordan Sample", "synthetic-demo", "person-jordan"),
        ]
        for entity in entities:
            service.upsert_entity(entity)

        links = [
            ("Project", "demo-project-orion", "HAS_TASK", "Task", "demo-task-identity"),
            ("Project", "demo-project-orion", "HAS_TASK", "Task", "demo-task-api"),
            ("Project", "demo-project-orion", "FOR_CLIENT", "Client", "demo-client-acme"),
            ("Project", "demo-project-orion", "WITH_PARTNER", "Partner", "demo-partner-northwind"),
            ("Project", "demo-project-nova", "FOR_CLIENT", "Client", "demo-client-blue"),
            ("Person", "demo-person-avery", "ASSIGNED_TO", "Task", "demo-task-identity"),
            ("Person", "demo-person-jordan", "ASSIGNED_TO", "Task", "demo-task-api"),
        ]
        for from_type, from_id, relation, to_type, to_id in links:
            store.link_entities(
                scope,
                EntityRef(from_type, from_id),
                EntityRef(to_type, to_id),
                relation,
                "IMPORTED",
                "IMPORTED",
            )

        doc = DocumentInput(
            source_system="synthetic-demo",
            source_id="orion-delivery-brief-v1",
            title="Orion Delivery Brief (Synthetic)",
            mime_type="text/markdown",
            text=(
                "# Orion delivery brief\n\n"
                "The API connector task is completed.\n\n"
                "Identity mapping is blocked while the Acme Robotics client reviews the access mapping. "
                "Avery Example owns the task. Northwind Analytics is the synthetic delivery partner.\n\n"
                "This fictional brief is also relevant to Nova Research because both projects use the same "
                "example identity review process."
            ),
            source_uri="synthetic://orion-delivery-brief-v1",
            linked_entities=(
                EntityRef("Project", "demo-project-orion"),
                EntityRef("Project", "demo-project-nova"),
                EntityRef("Task", "demo-task-identity"),
                EntityRef("Client", "demo-client-acme"),
                EntityRef("Partner", "demo-partner-northwind"),
                EntityRef("Person", "demo-person-avery"),
            ),
            link_provenance="IMPORTED",
            link_review_state="IMPORTED",
        )
        result = service.ingest_text_document(doc)
        hits = service.search_memory("identity mapping blocked client review", limit=3)
        task_context = service.get_task_context("demo-task-identity")
        print({"seed": result, "search_hits": hits, "task_context": task_context})
    finally:
        driver.close()


if __name__ == "__main__":
    main()
