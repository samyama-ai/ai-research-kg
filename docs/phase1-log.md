# Phase 1 log — understand the domain

Work log for the AI Research KG, following *How to Build a Samyama KG* (Phase 1). Newest entry first.

## 2026-10-12 — AI reviewer, round 2 (PR #1)

**Who:** Krithi. Fixes for the AI-Reviewer's second REQUEST_CHANGES (2026-10-09) on PR #1.

### `etl/count_kg.py`

- `split_authors` no longer breaks `Surname, T.` pairs: a comma-separated token made only of initials (`T`, `T. M.`, `J.-P.`) is glued back to the surname. `and`, `&` and `;` are separators too.
- Institution matching is case-sensitive, whole-word and works from a canonical-name → alias table (`Google DeepMind` ⊃ `DeepMind`, `Meta AI` ⊃ `FAIR`, `Carnegie Mellon` ⊃ `CMU`…). Lower-case `fair`, `epoch`, `Meta-learning` and `Together` at the start of a sentence no longer count. Ambiguous bare words (`Meta`, `Epoch`, `UW`) were dropped from the list.
- Reference bullets without a `**[Tag]**` were silently skipped before; they are now counted as references with role `untagged` (261 of them).
- Unparsed reference lines are reported with their line number in the file, not in the section.
- Paper grouping moved into `PaperIndex`: a title seen with two different arXiv IDs stays two papers and the title keeps pointing at the first, so a later title-only citation can't be re-pointed. A title-only record that later shows up with an arXiv ID stays one paper.
- Duplicate `if/elif` branches in `parse_reference` merged; the parser also returns `year`.
- Frontmatter values are read to the end of the line (quotes stripped) instead of stopping at the first space.
- Output gains `nodes_measured`, `edges_measured` (now including ACTIVE_ON) and their totals, so schema.md §11 can show its arithmetic.
- `tests/test_count_kg.py` grew from 1 to 6 tests; the fixture page covers each of the bugs above.

### Recount (commit `a02e87b3`, same catalog as before)

| Figure | Before | After | Why |
|---|---|---|---|
| References (CITES) | 12,617 | 12,878 | 261 untagged bullets were being dropped |
| Papers | 4,941 | 5,004 | same |
| Distinct author strings | 11,659 | 11,894 | new papers add names; the initials fix removes bogus one-letter "authors" |
| AUTHORED_BY | 19,529 | 19,166 | `Surname, T.` is one author again |
| APPEARED_AT | 4,262 | 4,313 | untagged references with venues |
| Institutions / ACTIVE_ON | 50 / 1,901 | 45 / 2,057 | aliases collapse (DeepMind → Google DeepMind); `Microsoft`, `Nvidia`, `UC Berkeley`, `AI2` now recognised; `fair`/`epoch` false hits gone |
| arXiv share | 71.3% | 71.5% | |
| Min references per problem | 4 | 8 | the low pages were the ones with untagged bullets |

### Docs made consistent

- schema.md: diagram now shows AssumptionClass / INSTANCE_OF / INTRODUCED_IN, puts `{kind}` on the OpenQuestion node and names the Section 4 provenance fields; new edge **FROM_SOURCE** (Problem → DataSource) so DataSource is reachable, 16 relationship types; §9 example uses a resolved full name (`Jason Gross`, variant `Gross`) instead of a bare surname; §11 shows measured + estimated arithmetic (~28–29K nodes, ~64–65K edges); the Berkeley survey is described as unpublished internal work with no citation yet.
- scope.md: AssumptionClass and DataSource added to the node list, FROM_SOURCE to the edges; STATE_OF_ART `evidence` has the same three values as the schema; venue wording matches; Q7 and Q22 reworded to what the data supports; Q33 moved to a Stretch section (number kept).

## 2026-10-05 — scope, size estimate, schema draft

**Who:** Krithi, after Naresh's team meeting on 2026-10-05.

### What was done

1. **Found the reference KG.** The "snap" Sandeep Kunkunuru mentioned is the **DBMS Research KG**, in `Samyama.ai/samyama-graph` under `case_studies/dbms-research` (18,751 nodes, 38,539 edges). Its snapshot is `dbms-research.sgsnap` on the `kg-snapshots-v7` release. The raw data is `github.com/samyama-ai/dbms_research`. This KG copies that structure.
2. **Chose the repo name:** `ai-research-kg`, matching the `<topic>-kg` pattern (cricket-kg, edge-ai-kg, ...). The data repo `samyama-ai/ai_research` keeps its own name. The repo was created from `kg-repo-template` on Gitea.
3. **Read the build guide** (*How to Build a Samyama KG*, 9 phases) and the four-layer graph-stack wiki page. This KG is mainly Layer 1 (domain vocabulary and connections), stored in Layer 2 (openCypher).
4. **Wrote the scope note** (`docs/scope.md`): one core question, 41 example questions in groups A–H (including two the graph should refuse), the brief, the entity and relationship glossary, the data source and licence, out-of-scope items, and the reference KG.
5. **Estimated the graph size** (`etl/count_kg.py`, run over all 1,000 problem files): the script reports measured source counts for the fields it parses. Whole-graph totals (~25–28K nodes / ~55–60K edges) are rough planning estimates because some node and edge types are not produced by the counter.
6. **Drafted the schema** (`docs/schema.md`, v0.1): 12 core node types plus a DataSource bookkeeping node, 16 relationship types (one computed, RELATED_TO; one bookkeeping, FROM_SOURCE, added 2026-10-12), provenance on every node and edge, fixed vocabularies for citation roles and obstructions, question coverage against the scope, and an implementation checklist. Laid out like the *Enterprise Valuation KG — Detailed Schema*.

### Decisions

| Decision | Choice | Why |
|---|---|---|
| "Open problem" | "problem" = any catalog entry; "open" = `status: open` | The catalog has 5 statuses, so the word was ambiguous |
| RELATED_TO | Computed (shared papers/methods or embedding similarity), labelled as computed | The problem pages have no "related problems" section |
| Citation roles | ~500 raw tag variants grouped into 7 roles, raw kept in `role_raw` | Needed for the survey / foundational / caution questions |
| Edge names | Same as the DBMS Research KG where the meaning is the same | So the two KGs can be bridged later |

### Known data issues (from the count script)

- Author strings are messy (surname only, initials, full name). The counter preserves `Surname, Initial` pairs; 71.5% of references have an arXiv ID. 261 reference bullets carry no role tag. Person identities still need resolution.
- Venue normalization is unresolved: the counter finds 699 distinct normalised raw venue strings, with ~200 venues only a rough estimate.
- The counter parses references on all 1,000 pages; this is a syntax count and not semantic validation.
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
