# Engine Notes

Things Samyama Graph does that a newcomer would not expect. Engine **1.11.0** (`ghcr.io/samyama-ai/samyama-graph:latest`, digest `fc9a7405…`), measured 2026-10-06/07.

## 1. Insight can't connect unless the engine is started with `--cors-origin`
Since samyama-graph PR #1356 the HTTP API allows **no** browser origins by default. The build guide's `docker run` line has no flag, so Samyama Insight (https://graph.samyama.cloud) fails, and Insight wrongly reports *"This page cannot reach an unencrypted server"*.

```bash
docker run -d --name samyama-ai_research -p 8090:8080 ghcr.io/samyama-ai/samyama-graph:latest \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud
```

## 2. Even with the flag, a signed-in Insight is blocked
The preflight answers `Access-Control-Allow-Headers: *`. Browsers do **not** let the `*` wildcard cover the `Authorization` header, which Insight sends when you're signed in. Workaround used on this machine: a small CORS proxy on `127.0.0.1:8091` (`~/samyama_ws/insight-proxy/proxy.py`) that echoes the requested headers. Connect Insight to `http://localhost:8091`.

Chrome 153 also needed `chrome://flags/#local-network-access-check` set to **Disabled**.

Both are engine/guide issues worth filing on samyama-graph.

## 3. `samyama --help` inside the container starts a second server
It runs the demo and server start-up instead of printing help. Don't run it with `docker exec`.

## 4. `DETACH DELETE` is not a full reset
(edge-ai-kg engine note 8) Property columns survive. To reload, recreate the container instead:
`docker rm -f samyama-ai_research` and then the `docker run` above. The loader refuses to load into a non-empty graph.

## 5. Aggregate on a property
(edge-ai-kg engine note 9) Use `count(x.id)`, not `count(r)` over a multi-variable `MATCH`.

## 6. Strings
Double quotes and backslashes are stripped from string values on load (`etl/helpers.py`). LaTeX like `$\hat p$` therefore reads `$hat p$` in the graph.

## 7. Snapshot export is POST
`curl -X POST -o snapshots/ai-research.sgsnap http://127.0.0.1:8090/api/snapshot/export`. `GET` returns 405. The result is 3.4 MB (gzip'd JSON lines, `sgsnap` v2).

## 8. Load timing (measured 2026-10-07, engine 1.11.0, laptop, Docker)
Parse 2.4 s · nodes 1.4 s · edges 28.0 s (62,178 edges, 50 per statement) · ~32 s end to end.
