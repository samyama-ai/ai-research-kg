# Dataset Card — AI Research KG

## Summary
A knowledge graph of 1,000 open problems in AI and machine learning: 29,707 nodes and 62,842 edges, built from the `ai_research` catalog. Sibling of the DBMS Research KG.

| | |
|---|---|
| Version | **v1.1**, first built 2026-10-09 (29,696 nodes); rebuilt 2026-10-12 after review with the counts above. v1 (2026-10-07) had 28,960 nodes / 62,178 edges |
| Built from | `ai_research` commit `a02e87b368016fd9568ba5ae8561ea601a8dee41` (catalog dated 2026-09-10) with the parser in this repository (`etl/build.py`) |
| Engine | Samyama Graph 1.11.0 (`ghcr.io/samyama-ai/samyama-graph@sha256:fc9a7405…`, see README) |
| Code licence | Apache 2.0 (`LICENSE`) |
| Graph (content) licence | **not yet decided**: the source states no licence, so the graph inherits none. CC BY 4.0 is proposed, as for the DBMS sibling (`docs/standards.md`). Until the source's owner decides, no snapshot of the graph is published |

## Source

| Source | What it gives | Licence | Real or synthetic |
|---|---|---|---|
| [`github.com/samyama-ai/ai_research`](https://github.com/samyama-ai/ai_research) @ `a02e87b368016fd9568ba5ae8561ea601a8dee41` | every node and edge | **none stated** (the DBMS sibling states CC BY 4.0; see `docs/standards.md`) | **real** data, see note below |

That is the only source: no external APIs, no LLM extraction, no synthetic data.

**Note on `provenance: "real"`.** This is the Samyama build-guide flag that separates data parsed from a real source from synthetic or generated data; every node here is `real` in that sense. It says nothing about whether the catalog's statements are correct. The catalog's own prose-quality flag is kept separately as `Problem.catalog_provenance`, and all 1,000 problems are `synthesized` there, meaning the catalog's text has not been individually verified by its authors. Treat the graph as a map for orientation; cite the linked papers, not the graph.

## How each part is built

| Part | Rule | Method tag |
|---|---|---|
| Problem, Topic, Paper, Person, Venue, Assumption, OpenQuestion, FutureDirection | parsed from fixed sections of each Markdown file | `parsed` |
| Obstruction | "Why It Is Hard" mapped by keywords to the 5 obstruction types named in the catalog's `TEMPLATE.md`, plus `other` | `keyword-classified` |
| Institution | "Current Research" matched against a fixed list of 52 labs and universities (`etl/rules.py: INSTITUTIONS`); 51 of them occur in the catalog | `name-matched` |
| RELATED_TO | computed: two problems that cite ≥2 of the same papers, top 5 per problem by Jaccard score | edge `method: shared_papers` |
| CITES.role | ~670 free-text reference tags grouped into 7 roles; the original tag is kept in `role_raw` | — |

## Intended uses
- Exploring which problems, papers, people and labs connect across AI research topics.
- Finding research opportunities: empirically open problems, cheap next experiments, problems no lab is named on.
- A Samyama case study that mirrors the DBMS Research KG.

## Out of scope
- Benchmark leaderboards, model rankings, funding, citation counts from outside the catalog.
- Identity resolution of people (see limits).
- Being cited as a primary source.

## Known limits
- **People:** authors appear in three forms (surname / initials / full name) and are not merged, so a bare surname like "Zhang" stands for many people. Use `name_form = 'full'` for people questions.
- **Methods:** not extracted in v1.
- **Institutions:** only the 52 names on the list are found (51 occur); others are missed.
- **Experiment budgets:** `compute_budget_gpu_hours` is parsed for 361 of 1,000 experiments, from text like "~200 A100-hours"; the rest are empty, never guessed.
- **Provenance dates:** every node carries `retrieved_at` (when the pinned catalog was fetched) and `source_date` (the pinned commit's date); edges carry no provenance of their own.
- **One source file** has sections 9 and 10 swapped; the parser finds sections by name, so it's handled.
