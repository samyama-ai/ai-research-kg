# Phase 1 log — understand the domain

Work log for the AI Research KG, following *How to Build a Samyama KG* (Phase 1). Newest entry first.

## 2026-10-05 — scope, size estimate, schema draft

**Who:** Krithi, after Naresh's team meeting on 2026-10-05.

### What was done

1. **Found the reference KG.** The "snap" Naresh mentioned is the **DBMS Research KG**, in `Samyama.ai/samyama-graph` under `case_studies/dbms-research` (18,751 nodes, 38,539 edges). Its snapshot is `dbms-research.sgsnap` on the `kg-snapshots-v7` release. The raw data is `github.com/samyama-ai/dbms_research`. This KG copies that structure.
2. **Chose the repo name:** `ai-research-kg`, matching the `<topic>-kg` pattern (cricket-kg, edge-ai-kg, ...). The data repo `samyama-ai/ai_research` keeps its own name. The repo was created from `kg-repo-template` on Gitea.
3. **Read the build guide** (*How to Build a Samyama KG*, 9 phases) and the four-layer graph-stack wiki page. This KG is mainly Layer 1 (domain vocabulary and connections), stored in Layer 2 (openCypher).
4. **Wrote the scope note** (`docs/scope.md`): one core question, 41 example questions in groups A–H (including two the graph should refuse), the brief, the entity and relationship glossary, the data source and licence, out-of-scope items, and the reference KG.
5. **Estimated the graph size** (`etl/count_kg.py`, run over all 1,000 problem files): about 20K nodes and 45–50K edges in the baseline, in the same range as the DBMS Research KG. The schema draft pushes this to ~25–28K / ~55–60K once OpenQuestion, MENTIONS and BLOCKED_BY are included.
6. **Drafted the schema** (`docs/schema.md`, v0.1): 12 core node types plus a DataSource bookkeeping node, 15 relationship types (one computed, RELATED_TO), provenance on every node and edge, fixed vocabularies for citation roles and obstructions, question coverage against the scope, and an implementation checklist. Laid out like the *Enterprise Valuation KG — Detailed Schema*.

### Decisions

| Decision | Choice | Why |
|---|---|---|
| "Open problem" | "problem" = any catalog entry; "open" = `status: open` | The catalog has 5 statuses, so the word was ambiguous |
| RELATED_TO | Computed (shared papers/methods or embedding similarity), labelled as computed | The problem pages have no "related problems" section |
| Citation roles | ~500 raw tag variants grouped into ~6 roles, raw kept in `role_raw` | Needed for the survey / foundational / caution questions |
| Edge names | Same as the DBMS Research KG where the meaning is the same | So the two KGs can be bridged later |

### Known data issues (from the count script)

- Author names are messy (surname only, initials, full name). Resolve through arXiv IDs; about 71% of references have one.
- 656 raw venue spellings need normalising to ~200 venues.
- 1 problem has no references. Leave it with none; never invent.
- `README.md` and `candidates.json` inside topic folders are not problems and must be skipped.

### Open questions for Naresh / Sandeep

- `ai_research` has **no licence file**. Confirm before anything is published.
- Confirm the repo name `ai-research-kg` and the snapshot name `ai-research.sgsnap`.
- Deadline for the first snapshot.
- Whether the Responsible AI / Explainable AI extension (Section 7 of the schema) waits for the Berkeley student's survey.

### Next

- Phase 2: set up the laptop (SSH key, token, venv, Docker, engine image), clone `ai_research` and `samyama-graph`.
- Get `docs/schema.md` reviewed before loading any data.
- Fill in the README placeholders and rename `schema/template_kg.cypher` to `schema/ai_research_kg.cypher` once the schema is approved.
