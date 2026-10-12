# Benchmarks

`queries.py` holds the query catalog: the `docs/scope.md` questions as Cypher, AR01–AR32 (AR31 and AR32 were added for Q16 and Q32), plus AR90–AR91, which must return no rows because the graph holds no such data.

```bash
python -m benchmarks.queries --url http://127.0.0.1:8090            # run all, print 3 rows each
python -m benchmarks.queries --only AR15 --rows 10                   # one query (an unknown id is an error)
python -m benchmarks.queries --coverage                              # which scope.md question each query answers
```

**Failure rule.** A run exits non-zero when any of these happens: a query raises an error; a query other than AR9x returns no rows; an AR9x query returns rows. `--only` with an id that doesn't exist is an error, not a silent pass.

**Measured.** 2026-10-07 on engine 1.11.0 with the v1 graph: all 32 queries of that day passed, the slowest in about 30 ms. Re-run 2026-10-12 with the two new queries on the engine as it stood that day (holding the v1.1 graph): all 34 pass; the slowest, AR21 (researchers across topics), takes about 230 ms, the rest under 90 ms. Timings use `time.perf_counter()`.

**Scope coverage.** Every question 1–41 is either answered by a query or listed in `UNANSWERED` with the reason; `tests/test_queries.py` fails if a question is missing or claimed twice. Questions no query answers in v1:

| Question | Why |
|---|---|
| Q12, Q25–Q28 | methods: not extracted in v1. The bold text in "State of the Art" is evidence labels, not method names (README "Known limits") |
| Q33 | stretch question: "if X were solved, which problems would it help?" needs a directional *enables* link between problems that the catalog never states (`docs/scope.md`, Stretch) |
| Q35 | topic clusters need a community-detection step over `RELATED_TO`; not computed in v1. AR25 (strongest topic pairs) is the nearest answer |

Two queries answer no numbered question but are kept because they are useful: AR05 (topic sizes, to turn AR04's open counts into shares) and AR19 (which venues' papers are cited most). AR23 picks its author at run time (the full-name author with the most papers), so it does not depend on one hard-coded name being in the graph.
