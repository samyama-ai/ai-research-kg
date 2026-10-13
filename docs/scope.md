# ai-research-kg — scope

## Core question
What are the open problems in AI research, and how do they connect
to topics, papers, people and methods?

Note: "problem" = any of the 1,000 catalog entries; "open" = status: open.
Other statuses: partially-solved, empirically-open, methodologically-blocked, solved-but-impractical. Staleness is represented by `stale_since`, not a status.
Counts (2026-10-05): open 401, empirically-open 295, partially-solved 189, methodologically-blocked 96, solved-but-impractical 19.

## A Problems & Topics
1. What are the 35 AI research topics?
2. How many problems are there in total, and how many are open?
3. How many problems are in each topic?
4. Which topics have the largest share of open problems?
5. Which gaps are theoretically open vs empirically open vs methodologically blocked, and which problems have each kind? (These are classes of the *gaps* in "What Is Not Known"; a problem's own `status` is a separate field, see the note above.)
6. Which problems are solved but impractical?
7. Which problems, whatever their status, have a next experiment that fits on a single machine (§8 compute budget)? (The catalog doesn't record who has tried what, so "nobody has tried at scale" can't be answered from it. Q37 is the same question for open problems only.)
8. What are the most common reasons these AI problems remain hard?

## B Understanding an AI Research Problem
9. What does problem X state, and what is its current status?
10. Which AI topic does problem X belong to?
11. Which papers are most relevant to problem X?
12. What methods have been tried on problem X?
13. What is the proposed next experiment for problem X?

## C Papers & Research
14. Which papers are cited by the most problems?
15. Which papers are connected to problems across the most AI topics?
16. Which problems share important papers or research foundations?
17. Which surveys cover the most problems?
18. Which papers provide foundational methods for the largest number of problems?
19. Which papers identify limitations or unresolved issues relevant to open problems?

## D Researchers & Labs
20. Which researchers are linked to the most problems?
21. Which researchers work across the most AI topics?
22. Which labs are named (§7 Current Research) on the most open problems? (The page naming a lab is the only evidence; activity isn't independently verified.)
23. Which researchers or labs are working on problem X?
24. Which researchers frequently collaborate on these problems?

Data path in v1: *researchers* are reached through the papers a problem cites (Problem → CITES → Paper → AUTHORED_BY → Person), *labs* through the "Current Research" bullets (Institution → ACTIVE_ON → Problem). There is no Person → Institution link in v1 (AFFILIATED_WITH needs an external lookup), so a researcher cannot be joined to a lab.

## E Methods
25. Which methods are state of the art for the most problems?
26. Which methods appear across multiple AI research topics?
27. Which problems mention method X (e.g. LoRA, RLHF)?
28. Which methods are claimed to work but lack adequate ablation or evidence?

## F Research Connections — core graph questions
29. Which problems are related to the most other problems?
30. Which pairs of AI topics are most strongly connected?
31. Which problems are most similar to problem X?
32. Which problems bridge otherwise unrelated AI topics?
34. Which problems depend on the same underlying assumption?
35. Which AI research topics form natural clusters?

## G Finding Research Opportunities
36. Which next experiments are cheapest to run?
37. Which *open* problems have a next experiment that fits on a single machine today? (Q7 without the status filter.)
38. Which topics have the most immediately runnable research experiments?
39. Which open problems are understudied — no lab active on them and fewer than 3 cited papers?

## H Questions the graph should NOT answer (should return "no data")
40. How much funding has each problem received?
41. Which model tops a given benchmark leaderboard?

## Stretch (not in the core list; needs data the catalog doesn't have)
33. If problem X were solved, which other problems could it help solve? Needs a directional "enables" link between problems, which the catalog never states. The number is kept so schema.md §10 still lines up.

## Later: Responsible AI (after the survey of RAI frameworks a UC Berkeley student working with the team is preparing; unpublished, no citation yet)
- Which problems touch safety, privacy, fairness or interpretability?
- Which RAI frameworks (NIST AI RMF, EU AI Act, ISO/IEC 42001) apply to which problems?

## Brief
- Asked by: Naresh Kolimi (team meeting, 2026-10-05)
- Users: Samyama team, researchers, and the Responsible AI / Explainable AI work (Berkeley student) that gets merged in later
- Deadline: none set. Asked at the 2026-10-05 meeting; no date given as of 2026-10-12. The lead decides when v1 is reviewed

## Entities (nodes)
- Problem: one per markdown file (id, title, status, provenance, dates, embedding for similarity search)
- Topic: the 35 topics in TAXONOMY.md
- Paper: from "Key References" (title, year, venue, arXiv id)
- Person: paper authors
- Institution / Lab: named in "Current Research"
- Venue: NeurIPS, ICML, ICLR, ACL...
- Method / Algorithm: named in "State of the Art"
- OpenQuestion: each classified gap in "What Is Not Known" (theoretically open / empirically open / methodologically blocked)
- Obstruction: reasons a problem is hard, from "Why It Is Hard" (e.g. compute, no ground truth, bad measurement)
- Assumption: one node per listed assumption in "Formal Setting" (e.g. "features are linear directions"); each belongs to exactly one problem, and a problem has several
- AssumptionClass: a curated canonical category that similar assumptions point to (answers Q34 without merging problem-specific wording)
- FutureDirection: the "Concrete Next Experiment" (with compute_budget, e.g. "200 A100-hours")
- DataSource: bookkeeping node for the pinned ai_research commit (licence, version, fetched_at)

## Relationships (edges)
- Problem -IN_TOPIC-> Topic
- Problem -CITES-> Paper (property role: one of 7 grouped citation roles, or `untagged` when the source has no tag; raw source tag kept)
- Paper -AUTHORED_BY-> Person
- Paper -APPEARED_AT-> Venue
- Person -AFFILIATED_WITH-> Institution (planned; not in v1, it needs an external lookup)
- Institution -ACTIVE_ON-> Problem
- Problem -HAS_GAP-> OpenQuestion
- Problem -MENTIONS-> Method
- Problem -STATE_OF_ART-> Method (property evidence: established / claimed / benchmark_only, as in schema.md §3; same direction as the DBMS KG)
- Problem -RESTS_ON-> Assumption
- Assumption -INSTANCE_OF-> AssumptionClass (curated canonical category for Q34)
- Problem -BLOCKED_BY-> Obstruction
- Problem -HAS_NEXT_EXPERIMENT-> FutureDirection
- Problem -RELATED_TO-> Problem
  - Not in the source data; must be computed (shared papers/methods, or embedding similarity)
- Problem -FROM_SOURCE-> DataSource (bookkeeping: which pinned catalog version the page was read from)

## Data source
- github.com/samyama-ai/ai_research: 1,000 problems, 35 topics, one .md file per problem (TEMPLATE.md layout)
- Real data, so no synthetic data is needed
- Licence: the repo has NO licence file. Ask Naresh/Sandeep before publishing. **No source snapshot may be published until its licence is confirmed.**

## Out of scope
- Benchmark leaderboards, model rankings
- Funding, company data, GPU prices
- Citation counts from outside the catalog

## Reference KG
- DBMS Research snap: samyama-graph/case_studies/dbms-research (same structure, sibling catalog)

## Estimated size (counter rerun 2026-10-12 on commit a02e87b3; script: count_kg.py)
- Rough planning range: ~28,000–29,000 nodes and ~64,000–65,000 edges (schema.md §11 shows the arithmetic: measured counts plus estimates for the types the counter doesn't produce).
- Measured by `count_kg.py`: 1,000 problems, 35 topics, 5,004 papers, 11,894 distinct listed author strings, 708 distinct normalised raw venue strings, 43 institutions / 1,950 rule-matched links, 2,492 assumption items, 3,810 §5 list items, 12,878 references (261 without a role tag), and 71.5% of references with an arXiv ID. Author identities and venue names are not resolved, so these are raw-string counts.
- Rough estimates only: ~200 venues after cleanup (same figure as schema.md), 2–3K methods, 8–12 obstruction types. The parser finds references on all 1,000 pages and reports any bullet it can't parse with its file line number; it does not validate that every reference line is semantically correct. `README.md` and `candidates.json` are skipped.

Full schema: see schema.md (v1 as built); the Phase 1 plan is schema-v0.1-plan.md (v0.1, 2026-10-05).
