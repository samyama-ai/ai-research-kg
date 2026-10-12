# AI Research Knowledge Graph

**28,974 nodes. 62,178 edges.** 1,000 open problems in AI and machine learning, with the papers, people, labs, assumptions, gaps and next experiments around them, from 1 source.

> Part of the **Samyama** ecosystem: loaded into and queried with [samyama-graph](https://github.com/samyama-ai/samyama-graph). Sibling of the **DBMS Research KG** (`samyama-graph/case_studies/dbms-research`), built the same way from the sibling catalog.

<a href="LICENSE"><img src="https://img.shields.io/badge/code-Apache_2.0-blue" alt="Code licence"></a>
Content licence: **to be decided before publishing**: the source states no licence, CC BY 4.0 is proposed (see [`docs/standards.md`](docs/standards.md)).

---

We loaded the [`ai_research`](https://github.com/samyama-ai/ai_research) catalog into one graph, then asked:

> *"Which papers are cited across the most AI research topics?"*

```cypher
MATCH (t:Topic)<-[:IN_TOPIC]-(p:Problem)-[:CITES]->(pa:Paper)
RETURN pa.title AS paper, count(DISTINCT t.id) AS topics
ORDER BY topics DESC LIMIT 5
```

| paper | topics |
|---|---|
| Training Compute-Optimal Large Language Models | 28 |
| Scaling Laws for Neural Language Models | 20 |
| Lost in the Middle: How Language Models Use Long Contexts | 15 |
| RULER: What's the Real Context Size of Your Long-Context Language Models? | 15 |
| Quantifying Memorization Across Neural Language Models | 13 |

And why problems stay open, which the catalog names in "Why It Is Hard":

| obstruction | problems |
|---|---|
| Confounded measurement | 521 |
| Non-identifiability | 458 |
| Absent ground truth | 208 |
| Compute cost | 137 |
| Evaluation does not measure what it names | 104 |

All numbers come from the build of 2026-10-12 (`python -m etl.build`, catalog commit `a02e87b3`; `tests/test_invariants.py` pins them). The first load, on 2026-10-07 into engine 1.11.0, had 28,960 nodes before the review fixes (sister journals of Nature and Science, non-ASCII author names, the US AI Safety Institute, assumption lists). `benchmarks/queries.py` reproduces the two tables (AR15, AR08).

---

## Schema

**Node labels** (11): Problem 1,000 · Topic 35 · Paper 4,932 · Person 15,102 · Venue 561 · Institution 51 · Assumption 2,496 · OpenQuestion 3,790 · Obstruction 6 · FutureDirection 1,000 · DataSource 1

**Edge types** (11): `IN_TOPIC` 1,000 · `CITES` 12,615 {role, role_raw, position} · `AUTHORED_BY` 28,757 {position} · `APPEARED_AT` 4,468 · `RESTS_ON` 2,496 {position} · `HAS_GAP` 3,790 {position} (`kind` is on the OpenQuestion) · `BLOCKED_BY` 1,448 {detail, is_primary} · `HAS_NEXT_EXPERIMENT` 1,000 · `ACTIVE_ON` 2,476 {direction} · `RELATED_TO` 3,128 {method, shared_papers, score} (computed from shared papers) · `FROM_SOURCE` 1,000

**Data source**: `github.com/samyama-ai/ai_research` only, pinned at commit `a02e87b3`. There are no external lookups and no LLM extraction; every node is parsed from the catalog's Markdown.

See [`schema/ai_research_kg.cypher`](schema/ai_research_kg.cypher), [`docs/schema.md`](docs/schema.md) and [`DATASET_CARD.md`](DATASET_CARD.md).

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# an empty engine, pinned to the image the counts were measured on (1.11.0);
# the CORS flag lets Samyama Insight connect, see docs/ENGINE-NOTES.md
docker run -d --name samyama-ai_research -p 8090:8080 \
  ghcr.io/samyama-ai/samyama-graph@sha256:fc9a74053554f0be76fdc3973bbc2e5ff05cbb767aa27953ce184e9503206bd4 \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud

python -m etl.download_data                         # catalog -> data/ai_research (pinned commit; writes data/ai_research.lock.json)
python -m etl.loader --url http://127.0.0.1:8090    # parse + load + verify counts (~30 s)
python -m benchmarks.queries                        # the scope.md questions, 35 queries
pytest                                              # parser, invariant, count and query-catalog tests

# optional: portable snapshot, same format as dbms-research.sgsnap (snapshots/ is git-ignored)
mkdir -p snapshots && curl -X POST -o snapshots/ai-research.sgsnap http://127.0.0.1:8090/api/snapshot/export
```

`python -m etl.build` builds the graph without an engine and writes `data/graph.json`.

## Structure
```
etl/download_data.py   # clone ai_research at the pinned commit; checks the checkout is clean and at that commit
etl/rules.py           # the fixed lists: citation-role buckets, venue aliases, obstruction types, institutions
etl/text.py            # Markdown helpers: sections (by heading text), frontmatter, lists
etl/parse.py           # one page -> references, assumptions, gaps, experiment, labs
etl/build.py           # catalog walk -> Graph (ids, paper dedup, computed RELATED_TO)
etl/loader.py          # schema + batched load + count verification
etl/helpers.py         # Cypher literals, identifier checks, batched CREATE
etl/count_kg.py        # Phase 1 size estimate (kept for reference)
schema/                # Cypher schema (indexes)
benchmarks/queries.py  # query catalog AR01-AR33, AR90-AR91, with scope.md coverage
mcp_server/            # MCP server exposing the graph to Claude (from the KG template; not yet adapted)
demo/                  # recorded demo (from the KG template; not yet recorded for this graph)
tools/insight_proxy.py # local CORS proxy so Samyama Insight can reach the engine (docs/ENGINE-NOTES.md)
docs/                  # scope, schema (as built) and the v0.1 plan, standards, engine notes, logs
tests/                 # parser tests on fixtures, full-graph invariants, count and query-catalog tests
```

## Known limits (v1)

- **No Method nodes.** The bold text in "State of the Art" is evidence labels ("Established", "Claimed but unablated"), not method names, so methods can't be extracted without an LLM or an outside source.
- **People are not resolved.** The catalog writes authors three ways (`Wortsman`, `T. Moerland`, `Rico Sennrich`). As in the DBMS KG, bare surnames are never merged into full names; filter on `name_form = 'full'` for people queries.
- **Institutions** are matched by name against a fixed list of 52 labs and universities in "Current Research" (51 occur in the catalog; MIRI never does).
- **No embeddings / vector search.** The DBMS KG used OpenAI embeddings; this build uses nothing outside the catalog.
