# Phase 1 — Reference Capability and Evidence Matrix

**Status:** In progress; public-source audit started, no upstream code executed locally
**Reviewed:** 2026-09-25

This matrix separates repository claims from source/tree evidence, tests, release state, licensing, and project fit. The audit used public GitHub repository metadata and selected files at the recorded `main` commits. No repository was cloned, installed, or copied into this workspace, and no upstream test result is represented as locally verified.

## Snapshot evidence

| Reference | Main commit reviewed | Release evidence | License evidence | Source/tree evidence |
|---|---|---|---|---|
| [neo4j-contrib/mcp-neo4j](https://github.com/neo4j-contrib/mcp-neo4j) | `1c7ad0793b5f06b42b9c44f855c23eb2064c3bb7` | Repository latest release endpoint returned `mcp-neo4j-cypher-v0.6.0` (2026-04-10); packages are versioned separately, including memory `0.4.5` in its `pyproject.toml` | Root `LICENSE.txt` is MIT; `SECURITY.md` points to Neo4j responsible disclosure | Root README identifies Cypher, memory, Aura API, and data-modeling servers; tree contains package manifests and unit/integration tests for each major server |
| [neo4j/mcp](https://github.com/neo4j/mcp) | `2630d620eb98029835eff65052cbd9a8da220af7` | Latest release `v1.6.0` (2026-09-10); changelog records current configuration changes | `LICENSE.txt` contains GPLv3; `NOTICE.txt` records Neo4j and commercial/Aura terms | Go module (`go 1.25.5`), Dockerfile, PyPI/MCP packaging files, CI workflows, extensive internal/e2e/integration tests |
| [dpartin/neo4j-mcp](https://github.com/dpartin/neo4j-mcp) | `7abe02c75610268904c8e16026423e7251c2cdef` | No GitHub release; repository last push metadata is 2025-08-14 | Root `LICENSE` is MIT | Python/FastMCP server, `pyproject.toml`, `requirements.txt`, test directory, and project status document are present |
| [Neo4j GraphRAG for Python](https://neo4j.com/docs/neo4j-graphrag-python/current/) and [Cypher Manual](https://neo4j.com/docs/cypher-manual/current/indexes/semantic-indexes/vector-indexes/) | Official current docs reviewed 2026-09-25 | GraphRAG package release pin remains open | License/reuse terms were not established in this pass; do not copy source until checked | Official docs expose vector, hybrid, VectorCypher, and HybridCypher patterns. The current implementation uses Neo4j 2026.01+ Cypher 25 `SEARCH` with workspace as an indexed filter property. |

## Capability matrix

| Capability | Labs MCP collection | Official Neo4j MCP | dpartin/neo4j-mcp | GraphRAG implication for this project |
|---|---|---|---|---|
| Graph read/write access | Cypher server documents generated read/write Cypher; memory server provides typed entity/relation/observation tools | `read-cypher` and `write-cypher`; read-only mode is configurable | CRUD and arbitrary `execute_query` are implemented in `server.py` | Do not expose generic access as the domain contract; wrap persistence with typed policy-aware operations |
| Domain memory model | Memory server has generic `Memory` entities, observations, and relations; README documents `read_graph`, `search_nodes`, entity/relation/observation management | No project/task/client memory model; schema inspection and Cypher are general-purpose | No domain-specific project/task/client model; generic nodes and relationships | Reuse concepts only as references; own the domain schema and provenance model |
| Vector/hybrid retrieval | Root collection README does not establish a domain-aware vector retrieval capability for the memory server | MCP server is not a RAG domain service; it exposes graph access and GDS discovery | README/status claim vector and hybrid/RAG tools; source claims are not independently verified here | Use the official GraphRAG library behind the project retrieval service if version/provider constraints permit |
| Graph-augmented retrieval | Generic graph exploration is present; no evidence of this project's bounded, permission-aware expansion contract | General Cypher can traverse graphs but does not implement this project's allowlist or scope policy | Generic query and analytics operations are present; no trusted project-scope policy | Implement bounded expansion in the project service, not by relying on an agent-generated query |
| Transport/distribution | README documents STDIO, SSE, HTTP and package/container distribution; package versions are fragmented | Official repo has Go, Docker, CI, release, and PyPI/MCP packaging surfaces | FastMCP server and `mcp.json`; no release artifact was found | Defer packaging until the first client and runtime are chosen; keep service independently runnable |
| Tests | Tree evidence shows unit and integration tests for Cypher, memory, modeling, and Aura packages; not run locally | Tree evidence shows unit, integration, e2e, lifecycle, and tool-handler tests; CI workflow present; not run locally | Test files are present; repository status says four basic tests pass and MCP-client tests may have connection issues; not run locally | Treat all upstream test claims as claims until independently reproduced; create project-specific authorization/idempotency tests |
| Security controls | Root security reporting exists; memory README documents secure HTTP defaults such as localhost/127.0.0.1 trusted hosts | Read-only mode and `EXPLAIN`/query-type checks are documented; README warns custom procedures/functions may bypass classification | Source uses a hard-coded fallback password, returns query errors as data, and builds labels/relationship fragments from tool inputs; arbitrary Cypher is exposed | No upstream server is accepted as the policy boundary; require least privilege, typed inputs, scope checks, and audit behavior in trusted code |
| Maintenance/support | Explicitly Neo4j Labs, experimental, no SLA or backward-compatibility/deprecation guarantees | Official Neo4j project with current release and changelog; support/terms still need review for deployment use | Small repository with no release and stale project-status timestamp relative to this audit | Official server is the strongest operational reference, but not a replacement for the domain layer |

## Reuse decision record

### Adopt as a reference, not as the domain implementation

- Use the official Neo4j MCP repository to study MCP lifecycle, read-only configuration, packaging, health checks, and test organization.
- Use the Labs memory server to study minimal graph-memory tool ergonomics and its package/transport patterns, while rejecting its generic schema as sufficient for projects, tasks, source provenance, and access policy.
- Use the official GraphRAG package as the leading retrieval-library candidate after Neo4j/Python/provider decisions are made. Its retriever patterns align with vector/hybrid search plus Cypher-based context expansion.

### Do not adopt unchanged

- Do not merge any upstream MCP server directly into the domain service.
- Do not use arbitrary Cypher, generic CRUD, or generic entity names as the ordinary agent-facing contract.
- Do not use dpartin's `production-ready` status as evidence of production readiness. Its source and status file require a security redesign before any code reuse decision.
- Do not copy upstream source or add dependencies until the exact license, dependency, and distribution obligations for the selected component are reviewed.

## Open audit work

- Inspect exact dependency lockfiles, release artifacts, transitive licenses, and selected implementation/test behavior in an isolated checkout if reuse remains likely and the user authorizes that step.
- Select target Neo4j version and verify filtered vector query plans on that version.
- Confirm the first MCP client and packaging convention before Phase 7/9.
- Resolve embedding privacy/provider policy before any non-deterministic or hosted embedding test.
