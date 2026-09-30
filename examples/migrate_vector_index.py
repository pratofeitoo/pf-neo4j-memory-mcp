"""Inspect or safely replace an empty document vector index for a new model dimension."""

from __future__ import annotations

import argparse
import os

from neo4j import GraphDatabase


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, help="Exact database to inspect")
    parser.add_argument("--dimensions", required=True, type=int)
    parser.add_argument("--apply", action="store_true", help="Replace the index only if no chunks exist")
    args = parser.parse_args()
    if args.database != os.environ.get("NEO4J_DATABASE"):
        raise RuntimeError("--database must match NEO4J_DATABASE")
    if not 1 <= args.dimensions <= 4096:
        raise ValueError("dimensions must be between 1 and 4096")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise RuntimeError("NEO4J_PASSWORD is required")
    driver = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687"),
        auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), password),
    )
    try:
        with driver.session(database=args.database) as session:
            count = session.run("MATCH (c:DocumentChunk) RETURN count(c) AS n").single()["n"]
            index = session.run(
                "SHOW VECTOR INDEXES YIELD name, options WHERE name = 'memory_chunk_embedding' "
                "RETURN options"
            ).single()
            previous = index["options"].get("indexConfig", {}).get("vector.dimensions") if index else None
            print(f"database={args.database} chunks={count} index_dimensions={previous} target_dimensions={args.dimensions}")
            if not args.apply or previous == args.dimensions:
                return
            if count:
                raise RuntimeError("DocumentChunk nodes exist; preserve their index and plan a parallel migration")
            if index:
                session.run("DROP INDEX memory_chunk_embedding").consume()
            session.run(
                "CYPHER 25 CREATE VECTOR INDEX memory_chunk_embedding "
                "FOR (c:DocumentChunk) ON c.embedding WITH [c.workspace_id] "
                "OPTIONS {indexConfig: {`vector.dimensions`: $dimensions, "
                "`vector.similarity_function`: 'cosine'}}",
                dimensions=args.dimensions,
            ).consume()
            actual = session.run(
                "SHOW VECTOR INDEXES YIELD name, options WHERE name = 'memory_chunk_embedding' "
                "RETURN options"
            ).single()["options"]["indexConfig"]["vector.dimensions"]
            if actual != args.dimensions:
                raise RuntimeError(f"Index migration verification failed: {actual}")
            print("Index dimension migration verified")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
