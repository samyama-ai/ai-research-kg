# Coding standards

How code, queries, data and documents are written in this repo.

Most rules below are enforced by a test or by the conformance tool, and say which. A rule marked
*by review* has no check behind it.

## Before you push

```bash
python -m pytest -q
python -m etl.conformance --url http://127.0.0.1:8090      # on a loaded graph
python -m benchmarks.run --url http://127.0.0.1:8090        # on a loaded graph, after python -m etl.build
```

`pytest` needs no running server. The full-graph tests (`tests/test_invariants.py`, the last test
of `tests/test_standards.py`) skip themselves where the catalog is not downloaded; run
`python -m etl.download_data` to run them all.

`ruff check .` is not clean on this repo yet: with line length 120 it reports 125 findings, most of
them long lines in older modules. New and changed code should pass it.

## Python

| Rule | Enforced by |
|---|---|
| Python 3.10 or later | `pyproject.toml` |
| A module starts `from __future__ import annotations` and has a docstring saying what it is for and how to run it | by review |
| No file over 500 lines, so a reviewer can read it in one pass | by review |
| Comments say **why**: a measurement, a trap, a decision. Not what the next line does | by review |

```python
# Good: records a trap nobody could guess.
# Aggregate on a property, count(x.id), not on a relationship variable (engine 1.11.0).

# Not needed: repeats the code.
# Loop over the problems.
```

## Naming

| Thing | Style | Example |
|---|---|---|
| Node label | `PascalCase`, singular | `FutureDirection` |
| Edge type | `UPPER_SNAKE_CASE`, a verb phrase read from source to target | `HAS_NEXT_EXPERIMENT` |
| Property | `snake_case` | `compute_budget_gpu_hours` |
| Property with a unit | ends with the unit | `compute_budget_gpu_hours` |
| Node id | `<label>:<value>`; parts of a problem add `#<part>` | `problem:01-tokenization/adversarial-tokenization-attacks#gap-1` |
| Coded value | as the catalog writes it (`empirically-open`); our own codes in `snake_case` | `compute_cost` |
| Query id | `AR` and two digits; `AR9x` for questions that must return nothing | `AR14` |
| Python function, variable | `snake_case` | `build_graph` |
| Python constant | `UPPER_SNAKE_CASE` | `EXAMPLE_PROBLEM` |

## Building nodes and edges

| Rule | Enforced by |
|---|---|
| Every node carries `provenance`, `source` and `method` | conformance (`etl/conformance.py`) |
| Every coded value is on its list in `schema/concepts.yaml` | conformance C9; `tests/test_standards.py` |
| Classes, edges, their domain, range and cardinality follow `schema/ai_research_kg.ttl` | conformance section 2; `tests/test_standards.py` |
| An id survives rendering unchanged, or two ids could become one | `etl.helpers.checked_id` raises |
| A missing value is left out, not written as null, zero or an empty string | `etl.helpers.props_map` drops `None` |
| Text loses double quotes and backslashes and becomes one line, because the engine takes no escapes | `etl.helpers._clean`; docs/ENGINE-NOTES.md |
| The loader counts every label and edge type on the engine against what it sent | `python -m etl.loader` |

A rule the graph breaks today is listed in `TRACKED_FAILURES` in `etl/conformance_lib.py` with the
issue that tracks its fix; `tests/test_standards.py` expects exactly those failures.

## Source data

| Rule | Enforced by |
|---|---|
| One source: the catalog at the pinned commit | `etl.download_data` checks the checkout is clean and at that commit |
| Nothing downloaded or built is committed; `data/` and `snapshots/` are git-ignored | `.gitignore` |
| Values are kept as written. Names are not corrected, merged or looked up | by review |
| A classification of ours (citation role buckets, obstruction types, institutions, venue aliases) is a fixed list in `etl/rules.py` and says so in `method` | by review; conformance |
| No external lookup (DBLP, ORCID, citation counts) | by review |

## Cypher

| Rule | Reason |
|---|---|
| Aggregate on a property, `count(x.id)`, not `count(r)` over a multi-variable `MATCH` | edge-ai-kg engine note 9, repeated in docs/ENGINE-NOTES.md |
| Under a `LIMIT`, prefer an `ORDER BY` that breaks ties | otherwise tied rows come back in any order and the `LIMIT` cuts at random |
| Match `RELATED_TO` undirected and keep each pair once | it is stored once per pair, in an arbitrary direction |

Statements the loader sends are built by `etl.helpers.cypher_literal` and `props_map`. Do not build
a literal by hand.

## Queries

A query is in the catalog (`benchmarks/queries.py`) only when:

| Rule | Enforced by |
|---|---|
| It has a unique `id` and names the scope.md question(s) it answers, or `None` | `tests/test_queries.py` |
| Every scope.md question is answered or listed in `UNANSWERED` with the reason | `tests/test_queries.py` |
| It has a second answer in plain Python in `benchmarks/reference.py` | `tests/test_reference.py` |
| The two agree on the full graph, including under a `LIMIT` | `python -m benchmarks.run` |
| It returns rows, or none for an `AR9x` question | `python -m benchmarks.run` |

The reference is written from the question, not from the Cypher, so a mistake in one is not copied
into the other.

## Tests

| Rule |
|---|
| Parser tests run on the pages in `tests/fixtures/catalog`, never on a download |
| A test that needs the downloaded catalog skips itself where it is absent |
| A check that can only pass is not a test. Each checker has a test that proves it can fail |
| Do not assert a wall-clock time |

## Documents

| Rule | Enforced by |
|---|---|
| A number quoted in a document comes from a build or a measured run, with its date | `tests/test_invariants.py` pins the README counts; by review |
| A document describes the repo as it is; how it got there goes in a log, the commit or the PR | by review |
| A value that is our rule, not the page's, is labelled as such | by review |
| A limit is stated next to the claim it limits | by review |

## Changing the schema

A label, edge type or coded value is declared in several places. Change all of them in one commit.

| Change | Files |
|---|---|
| Label or edge type | `etl/build.py`, `schema/ai_research_kg.cypher`, `schema/ai_research_kg.ttl`, `docs/schema.md`, `docs/ontology.md`, `README.md`, `DATASET_CARD.md` |
| Coded value | `schema/concepts.yaml`, the parser in `etl/`, `docs/taxonomy.md` |
| Query | `benchmarks/queries.py`, `benchmarks/reference.py`, `benchmarks/README.md` |

## Safety

| Rule |
|---|
| Load or import into a server of its own. Snapshot import appends, so import only into an empty server |
| `demo/insight_proxy.py` binds to the loopback address; it is for a development machine, not for exposing an engine |
| No secret, key or token belongs in this repo. The source needs none |
