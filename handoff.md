# Fresh-Session Handoff — Execute the Neo4j Agent Memory Plan

**Prepared:** 2026-09-25
**Destination project folder:** `neo4j-agent-memory/`
**Handoff status:** Active implementation handoff
**Current project status:** Local synthetic vertical slice implemented and exercised against the user's Neo4j instance; later integration and readiness gates remain open.

## Continuation update — 2026-09-25

The initial assignment below records the pre-implementation state and is retained as history. Its statement that implementation has not started and its request to gather Phase 0 decisions are superseded by this update and the dated evidence in `build-record.md`.

- User decisions: Codex only for now; local deployment; latest Neo4j with APOC and GDS available; source details supplied directly as needed; hosted embeddings allowed; mostly text files; retention/privacy deferred.
- The user supplied the local Neo4j Desktop data-directory context and loopback Bolt URI. Credentials are not stored in project files.
- A Python package now provides a scoped Neo4j store, typed entities/links, text/Markdown ingestion, an optional hosted embedding adapter, indexed vector retrieval, structured task context, and local stdio MCP tools.
- Neo4j Enterprise `2026.09.0` was reachable; APOC and GDS were present. The database has package schema plus only the repeatable fictional `local-development` demo graph.
- The configured default database is `codex-mem-01`. It has been initialized with the package schema and cloned from the prior `neo4j` database after confirming that source held only the known synthetic fixture. Source and target matched at 12 nodes and 24 relationships; see the latest dated entry in `build-record.md`.
- The demo seed has exercised indexed retrieval and structured task context. No OpenAI embedding request, Codex MCP handshake, formal test suite, or real-data ingestion has occurred.
- Next: read the current phase statuses; inspect and refine the implementation, add a verified Codex project-local connection/configuration example, perform an MCP handshake only in the authorized local environment, and continue the later plan gates. Keep all data synthetic while retention/privacy is deferred.

## Assignment

Continue the user's project to build an agent-memory package for complex project-management knowledge on Neo4j. Execute the existing plan step by step. Do not stop at summarizing, polishing, or re-planning the documents: proceed with the authorized project work, gather current evidence, resolve decisions that block implementation, and create reviewable artifacts. Keep the work auditable and update the project's documentation as evidence is produced.

## User goal and agreed direction

The user wants a graph database used as persistent agent memory, not merely a fact store. The data must support projects, tasks, different clients and partners, people, and documents linked to multiple projects/tasks/clients/people at once. It must combine graph relationships with vector embeddings so relevant semantic passages can be found and expanded into useful connected project context.

The direction already established in this conversation is:

- Use Neo4j as the graph and vector store.
- Treat the Neo4j Labs and dpartin MCP repositories as references, not as complete solutions to merge without review.
- Build a domain-aware persistence/retrieval layer and tailored MCP tools. Use hybrid/vector search plus bounded graph expansion, with access filtering before context is returned to an agent.
- Add operational skills and package the MCP server and skills for the chosen agent host where supported; retain the ability to use the service independently from a plugin.
- Preserve source provenance, source-of-truth distinctions, access boundaries, temporal information, and uncertainty. Do not treat extracted facts or README feature claims as verified truth.
- Start with a small vertical slice and synthetic data. Do not load real client/partner data until scope, permissions, retention, and provider constraints are decided.

These are the working direction, not approval of unresolved deployment, provider, runtime, schema-cardinality, or security decisions. Keep those open until evidence and user input settle them.

## First read: project source of truth

Open these files from this folder before editing or implementing:

1. `README.md` — project objective, recommendation, reference links, document-maintenance rules.
2. `architecture.md` — proposed components, graph vocabulary, ingestion/retrieval flows, tool contracts, security principles, evaluation, ADRs, and open questions.
3. `implementation-plan.md` — ordered phases and acceptance criteria. It is the execution sequence.
4. `build-record.md` — current status and dated evidence. Append new progress; do not rewrite history.
5. `handoff.md` — this continuation brief; it supplements but does not supersede the other project records.

The first implementation phase is **Phase 0 — Establish scope and operating constraints**, followed by **Phase 1 — Audit the reference implementations**. The plan currently marks no phase complete. Do not skip directly to coding before decisions required for the selected slice are understood.

## Immediate next actions

1. Inspect the folder and workspace state; preserve existing changes and confirm exact paths before any edits. This workspace has previously contained standalone Markdown documentation and may not be a Git checkout, so determine the actual state rather than assuming Git metadata exists.
2. Re-read the project documents and use their current contents as authority. This handoff supplements them; it does not supersede them.
3. Begin Phase 0 by gathering the user's intended first client(s), local/private vs shared deployment, source systems, Neo4j hosting/version, embedding privacy/provider constraints, document formats/volume, and access/retention requirements. Continue independent discovery while those answers are pending; do not place real data in a prototype.
4. Create a dated Phase 0 decisions artifact (prefer `scope-and-constraints.md`) and update `architecture.md` only when a choice is supported. Mark assumptions and provisional choices visibly.
5. Begin Phase 1 by inspecting current upstream code, manifests, licenses, tests, releases, and security posture for at least:
   - `https://github.com/neo4j-contrib/mcp-neo4j`
   - `https://github.com/neo4j/mcp`
   - `https://github.com/dpartin/neo4j-mcp`
   - Official Neo4j GraphRAG documentation and implementation recommendations.
6. Build a capability/evidence matrix that separates documented features, present code, tested behavior, release/distribution state, license terms, and unresolved risk. Use source files and tests where available; do not infer implementation quality from star counts or repository descriptions.
7. Do not clone, install, execute, or copy an upstream project until the chosen checkout location, security, dependencies, and license obligations have been checked. Use an isolated working tree or temporary checkout if implementation requires it; preserve the user's current files.
8. Update `implementation-plan.md` with evidence-based status only and append progress to `build-record.md` after each meaningful phase or decision.

## Required working behavior

- Carry out the work rather than responding with another proposal. Ask the user for decisions only where the answer materially affects architecture, privacy, access, cost, or data handling; explain why the decision blocks that slice. Continue non-dependent research and design meanwhile.
- Verify current upstream repository state and official docs when work begins; the initial plan review is dated 2026-09-25 and may become stale.
- Keep test/verification evidence specific: command, environment/version, expected result, observed result, and any limitation. Do not claim tests were run when they were not.
- Do not add, install, deploy, publish, or connect an external service without the appropriate user authorization. Build a concrete reviewable artifact before asking for any approval needed for an external action.
- Never put secrets, real client documents, or real personal data in source control, examples, prompts, or test fixtures. Synthetic-only data is the default until privacy and retention controls are decided.
- Keep arbitrary Cypher isolated from ordinary domain tools; prefer typed and permission-aware operations. Apply workspace/project access checks in trusted server code before retrieval reaches the LLM.
- Preserve provenance, source references, confidence/review state, and time semantics. State whether content is imported, inferred, user-confirmed, or source-system authoritative.
- When a requested operation fails, report whether it executed. Do not bypass failed security/approval checks.
- Keep docs synchronized: architecture choices and rationale in `architecture.md`; ordered execution and acceptance in `implementation-plan.md`; chronological evidence in `build-record.md`; links in `README.md`.

## Definition of a successful first slice

The first slice should prove this entire path with synthetic data:

1. Create a workspace, project, tasks, clients/partners, and people with explicit typed links.
2. Ingest a synthetic document once and create stable document/chunk records with source and locator metadata.
3. Link that document to multiple projects/tasks/parties with link provenance.
4. Generate and store embeddings with model and dimension metadata.
5. Retrieve a semantic passage using a workspace/project scope, expand to relevant graph context, and return source citations.
6. Answer exact task/project state questions through structured graph queries rather than relying on vector similarity.
7. Demonstrate that repeated ingestion is idempotent, ambiguous links remain reviewable, and a caller outside the allowed scope receives no protected information.
8. Expose the slice through a small set of typed MCP tools and document setup, operation, and limitations.

Do not declare the package production-ready from a working MCP handshake or successful demo alone. Broader retrieval evaluation, failure handling, security review, backup/restore, migration, and operational readiness remain gates in later phases.

## Suggested initial prompt for the new session

> Execute the Neo4j Agent Memory plan in `neo4j-agent-memory/`. Read `README.md`, `architecture.md`, `implementation-plan.md`, `build-record.md`, and `handoff.md` first. The project is currently documentation only. Start with Phase 0 and Phase 1: inspect current workspace state, collect only materially blocking scope decisions while continuing independent upstream/license/code review, and create the scope artifact plus a source-backed reference capability matrix. Preserve existing files and synthetic-data boundaries. Do not claim implementation or tests that have not happened. Update the plan and append evidence to the build record as you go. Continue into subsequent phases whenever prerequisites are resolved; keep the user informed with concrete progress and ask focused questions only when required decisions block safe, useful work.
