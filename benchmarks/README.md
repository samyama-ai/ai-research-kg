# Benchmarks

`queries.py` holds the query catalog: the `docs/scope.md` questions as Cypher, numbered AR01–AR30, plus AR90–AR91, which must return no rows because the graph holds no such data.

```bash
python -m benchmarks.queries --url http://127.0.0.1:8090            # run all, print 3 rows each
python -m benchmarks.queries --only AR15 --rows 10                   # one query
```

A query that returns no rows (other than AR9x) fails the run. Measured 2026-10-07 on engine 1.11.0: all 32 pass; the slowest takes about 30 ms.

Not answerable in v1 (see README "Known limits"): methods (scope Q12, Q25–Q28) and "if X were solved, what would it help" (Q33).
