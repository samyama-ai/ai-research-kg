# Engine Notes

Things Samyama Graph does that a newcomer would not expect. Engine **1.11.0** (`ghcr.io/samyama-ai/samyama-graph@sha256:fc9a74053554f0be76fdc3973bbc2e5ff05cbb767aa27953ce184e9503206bd4`, which `:latest` pointed at on 2026-10-05), measured 2026-10-06/07. The README's `docker run` pins that digest.

## 1. Insight can't connect unless the engine is started with `--cors-origin`
Since samyama-graph PR #1356 the HTTP API allows **no** browser origins by default. The build guide's `docker run` line has no flag, so Samyama Insight (https://graph.samyama.cloud) fails, and Insight wrongly reports *"This page cannot reach an unencrypted server"*.

```bash
docker run -d --name samyama-ai_research -p 8090:8080 \
  ghcr.io/samyama-ai/samyama-graph@sha256:fc9a74053554f0be76fdc3973bbc2e5ff05cbb767aa27953ce184e9503206bd4 \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud
```

## 2. Even with the flag, a signed-in Insight is blocked
The preflight answers `Access-Control-Allow-Headers: *`. Browsers do **not** let the `*` wildcard cover the `Authorization` header, which Insight sends when you're signed in. Workaround: the small CORS proxy in this repo, [`demo/insight_proxy.py`](../demo/insight_proxy.py), listens on `127.0.0.1:8091`, forwards to the engine on `8090` and echoes the requested headers for the Insight origin only. Run `python demo/insight_proxy.py` and connect Insight to `http://localhost:8091`.

Chrome 153 also needed `chrome://flags/#local-network-access-check` set to **Disabled**. **Warning:** that flag is a browser security check (it stops public web pages from reaching services on your local network). Only disable it on a development machine, while you use Insight, and set it back to Default afterwards; don't do this on a machine that holds anything sensitive.

Both are engine/guide issues worth filing on samyama-graph.

## 3. `samyama --help` inside the container starts a second server
It runs the demo and server start-up instead of printing help. Don't run it with `docker exec`.

## 4. `DETACH DELETE` is not a full reset
(edge-ai-kg engine note 8) Property columns survive. To reload, recreate the container instead:
`docker rm -f samyama-ai_research` and then the `docker run` above. The loader refuses to load into a non-empty graph.

## 5. Aggregate on a property
(edge-ai-kg engine note 9) Use `count(x.id)`, not `count(r)` over a multi-variable `MATCH`.

## 6. Strings
Double quotes and backslashes are stripped from string values on load, and newlines and carriage returns are replaced by spaces (`etl/helpers.py: _clean`). LaTeX like `$\hat p$` therefore reads `$hat p$` in the graph, and multi-line text is one line.

## 7. Snapshot export is POST
`curl -X POST -o snapshots/ai-research.sgsnap http://127.0.0.1:8090/api/snapshot/export`. `GET` returns 405. The result is 3.4 MB (gzip'd JSON lines, `sgsnap` v2).

## 8. Load timing (measured 2026-10-07, engine 1.11.0, laptop, Docker)
Parse 2.4 s · nodes 1.4 s · edges 28.0 s (62,178 edges, 50 per statement) · ~32 s end to end.
