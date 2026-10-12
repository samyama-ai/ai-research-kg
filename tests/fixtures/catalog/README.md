# Fixture catalog

A two-page stand-in for `data/ai_research`, so the parser tests run without the download.

| File | What it is |
|---|---|
| `TAXONOMY.md` | two rows of the real taxonomy (topics 20 and 22) |
| `topics/20-interpretability/internals-based-safety-verification.md` | a copy of the real page at `ai_research` commit `a02e87b3`, the problem read in Phase 1 |
| `topics/22-safety-robustness/fixture-swapped-sections.md` | handwritten; sections 9 and 10 are swapped on purpose, to test that sections are found by heading text |

**Corrections to the copied page (2026-10-12).** The source text has four slips, which the fixture does not repeat; they are marked in an HTML comment at the top of the file: Llama-2-7B has 32 layers (the text said 16 in one place and 32 in another), its MLP activation is SwiGLU not GELU, the branch-and-bound split depth is 11,008 × 32 ≈ 3.5 × 10⁵ not 10⁵, and two "(frontier — verify)" markers were removed. The footer links point at the pinned GitHub commit instead of relative paths that don't resolve from here. None of this changes what the parser extracts (the tests pin the extracted values). The slips should be reported to `ai_research`.
