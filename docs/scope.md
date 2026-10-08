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
5. Which problems are theoretically open vs empirically open vs methodologically blocked?
6. Which problems are solved but impractical?
7. Which problems are runnable today but nobody has tried at scale?
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
22. Which labs are currently working on the most open problems?
23. Which researchers or labs are working on problem X?
24. Which researchers frequently collaborate on these problems?

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
33. If problem X were solved, which other problems could it help solve? (stretch: needs a directional link the data doesn't have)
34. Which problems depend on the same underlying assumption?
35. Which AI research topics form natural clusters?

## G Finding Research Opportunities
36. Which next experiments are cheapest to run?
37. Which open problems can be experimentally investigated on a single machine today?
38. Which topics have the most immediately runnable research experiments?
39. Which open problems are understudied — no lab active on them and fewer than 3 cited papers?

## H Questions the graph should NOT answer (should return "no data")
40. How much funding has each problem received?
41. Which model tops a given benchmark leaderboard?

## Later: Responsible AI (after the Berkeley student's survey)
- Which problems touch safety, privacy, fairness or interpretability?
- Which RAI frameworks (NIST AI RMF, EU AI Act, ISO/IEC 42001) apply to which problems?

## Brief
- Asked by: Naresh Kolimi (team meeting, 2026-10-05)
- Users: Samyama team, researchers, and the Responsible AI / Explainable AI work (Berkeley student) that gets merged in later
- Deadline: TBD (ask)

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
- Assumption: assumptions listed in "Formal Setting" (e.g. "features are linear directions")
- FutureDirection: the "Concrete Next Experiment" (with compute_budget, e.g. "200 A100-hours")

## Relationships (edges)
- Problem -IN_TOPIC-> Topic
- Problem -CITES-> Paper (property role: one of 7 grouped citation roles, plus raw source tag)
- Paper -AUTHORED_BY-> Person
- Paper -APPEARED_AT-> Venue
- Person -AFFILIATED_WITH-> Institution
- Institution -ACTIVE_ON-> Problem
- Problem -HAS_GAP-> OpenQuestion
- Problem -MENTIONS-> Method
- Problem -STATE_OF_ART-> Method (property evidence: established / claimed; same direction as the DBMS KG)
- Problem -RESTS_ON-> Assumption
- Assumption -INSTANCE_OF-> AssumptionClass (curated canonical category for Q34)
- Problem -BLOCKED_BY-> Obstruction
- Problem -HAS_NEXT_EXPERIMENT-> FutureDirection
- Problem -RELATED_TO-> Problem
  - Not in the source data; must be computed (shared papers/methods, or embedding similarity)

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

## Estimated size (counter rerun 2026-10-08; script: count_kg.py)
- Rough planning range: ~25,000–28,000 nodes and ~55,000–60,000 edges; this is not a complete count of every schema type. `count_kg.py` measures only the fields listed in its JSON output.
- Measured by `count_kg.py` on the local catalog snapshot: 1,000 problems, 35 topics, 4,941 papers, 11,659 distinct listed author strings, 2,492 assumption items, 3,810 §5 list items, 12,617 references, and 71.3% of references with an arXiv ID. Author identities and venue names are not resolved, so these are raw-string counts.
- Rough estimates only: 50–100 labs, 2–3K methods, and venue normalization from 700 raw venue strings. The parser finds references on all 1,000 pages; it does not validate that every reference line is semantically correct. `README.md` and `candidates.json` are skipped.

Full schema: see schema.md (v0.1 draft, 2026-10-05).
