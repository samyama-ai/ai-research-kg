# Demo

Narrated walkthrough of the AI Research KG on a fast, real subset.

```bash
python -m demo.demo
```
Record/regenerate:
```bash
asciinema rec --overwrite --cols 92 --rows 32 --idle-time-limit 2.0 \
  -c "bash -c 'python -m demo.demo'" demo/ai_research.cast
agg demo/ai_research.cast demo/ai_research.gif
```
