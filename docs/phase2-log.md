# Phase 2 log — set up the machine

Work log for the AI Research KG, following *How to Build a Samyama KG* (Phase 2). Phase 1 is in `docs/phase1-log.md` (PR #1).

## 2026-10-06 — machine setup and template placeholders

**Who:** Krithi.

### What was done

1. **Installed Docker** and added the user to the `docker` group, so Docker runs without `sudo`.
2. **Pulled the Samyama engine image** `ghcr.io/samyama-ai/samyama-graph:latest` (engine 1.11.0).
3. **Started the engine** as the container `samyama-ai_research` on `localhost:8090`. A test query (`RETURN 1 AS ok`) returns a result.
4. **Set up the Python environment.** Created `.venv` and installed this repo with `pip install -e ".[dev]"`.
5. **Filled the template placeholders** for the name and slug (this PR):

   | Placeholder | Value |
   |---|---|
   | `{{KG_NAME}}` | AI Research |
   | `{{KG_SLUG}}` | `ai_research` (tenant, file names) |
   | Package / MCP server name | `ai-research-kg` |
   | `{{YEAR}}` in LICENSE | 2026 |

   Counts (`{{N}}`, `{{M}}`, `{{K}}`), the hero query and the schema placeholders are left for Phases 5 and 8, once the schema is approved and data is loaded.
6. **Skipped the SSH key.** HTTPS with a token already works for clone and push.

### How to start the engine

The build guide's `docker run` line is missing a flag. Use this instead:

```bash
docker run -d --name samyama-ai_research -p 8090:8080 \
  ghcr.io/samyama-ai/samyama-graph:latest \
  samyama --host 0.0.0.0 --cors-origin https://graph.samyama.cloud
```

Check it:

```bash
curl -s -H 'Content-Type: application/json' \
  -d '{"query":"RETURN 1 AS ok"}' http://127.0.0.1:8090/api/query
```

### Gotchas found

- **CORS must be set.** Since samyama-graph PR #1356, the engine allows no browser origins by default. Without `--cors-origin`, Samyama Insight (graph.samyama.cloud) cannot connect. Insight then shows a misleading "cannot reach an unencrypted server" error, which looks like a mixed-content problem but is not. The build guide should be updated.
- **Don't run `samyama --help` inside the container.** It starts a second server instead of printing help.
- **Port.** The engine is on host port 8090, but `mcp_server/config.yaml` still points at 8080 (the template default). Change it when the MCP server is built.
- **Schema file name.** The README now links to `schema/ai_research_kg.cypher`, which doesn't exist yet. `schema/template_kg.cypher` gets renamed when the schema is approved.

### Also today (outside this repo)

- **Finished paper 20**, *How much of the multilingual token tax is removable* (arXiv 2609.00378): Parts III to V of its DOCUMENTATION.md. That covers the four-move plan (§7), what the code runs and how far each number can be trusted (§11), and the final results, auto-checks, limitations and rerun steps (§13 onward).
- **Studied and finished paper 15**, *Knowledge-Graph Grounding Helps LLMs Only for Out-of-Training Knowledge: A Controlled Study on Clinical Question Answering* (arXiv 2606.22419), `papers/paper15-clinical-llm-graphrag` in samyama-research.

### Next

- Get PR #1 (scope and schema) reviewed.
- Phase 3 onward: standards and taxonomies (`docs/standards.md`), then the real schema file `schema/ai_research_kg.cypher`.
