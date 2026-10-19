# Benchmarks

The `docs/scope.md` questions as Cypher, each answered twice: on the engine, and again in plain
Python from the built graph.

| File | |
|---|---|
| `queries.py` | The catalog: AR01–AR33 (AR31, AR32 and AR33 were added for Q16, Q32 and Q7), plus AR90–AR91, which must return no rows because the graph holds no such data |
| `reference.py` | Each query again in plain Python over `data/graph.json`, and `check()`, which compares the two |
| `run.py` | Runs, times and checks the catalog |

```bash
python -m etl.build                                              # data/graph.json, for the reference
python -m benchmarks.run --url http://127.0.0.1:8090             # run all, check each, print 3 rows
python -m benchmarks.run --only AR15 --rows 10                   # one query (an unknown id is an error)
python -m benchmarks.run --coverage                              # which scope.md question each query answers
python -m benchmarks.run --no-check                              # without the reference
python -m benchmarks.reference --only AR15                       # the reference's own answer
```

**Failure rule.** A run exits non-zero when any of these happens: a query raises an error; a query other than AR9x returns no rows; an AR9x query returns rows; an answer disagrees with its reference. `--only` with an id that doesn't exist is an error, not a silent pass. Build `data/graph.json` from the same commit the engine holds.

## Why every query has a reference

A query that runs has not been shown to be right. The reference is written from the question, not
from the Cypher, so a mistake in one is not copied into the other. `check()` tests four things,
because each can fail on its own:

1. the number of rows;
2. that every row is one the reference also produced;
3. that the rows are in the promised order;
4. under a `LIMIT`, that they are the top rows and not just any correct ones.

Rows that sort equal may come back in either order. Text is compared as the loader stores it
(quotes and backslashes stripped, `docs/ENGINE-NOTES.md`). `tests/test_reference.py` shows each of
the four checks failing on a wrong answer.

## Adding a query

1. Add an entry to `QUERIES` in `queries.py`, with the scope.md question it answers.
2. Add its answer to `answers()` in `reference.py`, written from the question.
3. Run `pytest`, then `python -m benchmarks.run` on a loaded graph.

## Results

**Measured.** 2026-10-18 on engine 1.11.0 holding the v1.1 graph (29,707 nodes, 62,842 edges): all 35 queries pass and every answer agrees with its reference; the slowest, AR20 and AR21 (researchers), take about 65 ms, the rest under 50 ms. Earlier runs: 2026-10-07 (v1, 32 queries, slowest about 30 ms) and 2026-10-12 (v1.1, 35 queries, slowest AR21 about 230 ms). Timings use `time.perf_counter()`; one machine, one run, so treat them as an order of magnitude.

**Scope coverage.** Every question 1–41 is either answered by a query or listed in `UNANSWERED` with the reason; `tests/test_queries.py` fails if a question is missing or claimed twice. Questions no query answers in v1:

| Question | Why |
|---|---|
| Q12, Q25–Q28 | methods: not extracted in v1. The bold text in "State of the Art" is evidence labels, not method names (README "Known limits") |
| Q33 | stretch question: "if X were solved, which problems would it help?" needs a directional *enables* link between problems that the catalog never states (`docs/scope.md`, Stretch) |
| Q35 | topic clusters need a community-detection step over `RELATED_TO`; not computed in v1. AR25 (strongest topic pairs) is the nearest answer |

Two queries answer no numbered question but are kept because they are useful: AR05 (topic sizes, to turn AR04's open counts into shares) and AR19 (which venues' papers are cited most). AR23 picks its author at run time (the full-name author with the most papers), so it does not depend on one hard-coded name being in the graph.
