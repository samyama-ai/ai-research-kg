"""Walk the catalog and build the graph: nodes, edges and the computed RELATED_TO.

    python -m etl.build          # parse the pinned catalog, write data/graph.json

The page-level parsing lives in etl/parse.py; this module mints ids, deduplicates
papers across problems (arXiv id first, then normalised title, then DOI, then a
title hash) and computes RELATED_TO from shared cited papers, which says so on
the edge (`method`, `shared_papers`, `score`).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from etl.helpers import short_hash, slug
from etl.parse import (
    INSTITUTIONS,
    OBSTRUCTIONS,
    PREPRINT_VENUES,
    classify_obstructions,
    first_paragraphs,
    name_form,
    norm_title,
    parse_assumptions,
    parse_current_research,
    parse_experiment,
    parse_frontmatter,
    parse_gaps,
    parse_reference,
    parse_taxonomy,
    problem_files,
    split_sections,
)

REPO_WEB = "https://github.com/samyama-ai/ai_research"
SOURCE = "ai_research"
LICENCE_NOTE = "none stated (see docs/standards.md)"


# --------------------------------------------------------------------------- #
# Graph container
# --------------------------------------------------------------------------- #
@dataclass
class Graph:
    nodes: dict[str, dict[str, dict]] = field(default_factory=lambda: defaultdict(dict))
    edges: list[tuple] = field(default_factory=list)
    _edge_keys: set = field(default_factory=set)

    def add_node(self, label: str, node_id: str, **props) -> str:
        existing = self.nodes[label].get(node_id)
        if existing is None:
            self.nodes[label][node_id] = {"id": node_id, **props}
        else:  # keep first value, fill gaps
            for k, v in props.items():
                if existing.get(k) in (None, "") and v not in (None, ""):
                    existing[k] = v
        return node_id

    def add_edge(self, src_label, src_id, rel, tgt_label, tgt_id, props=None, dedupe=True):
        key = (src_label, src_id, rel, tgt_label, tgt_id)
        if dedupe and key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append((src_label, src_id, rel, tgt_label, tgt_id, props or None))

    def counts(self) -> tuple[dict[str, int], dict[str, int]]:
        n = {label: len(v) for label, v in sorted(self.nodes.items())}
        e = dict(sorted(Counter(e[2] for e in self.edges).items()))
        return n, e

    def to_json(self) -> dict:
        return {"nodes": {k: list(v.values()) for k, v in self.nodes.items()},
                "edges": [list(e) for e in self.edges]}


# --------------------------------------------------------------------------- #
# Catalog walk
# --------------------------------------------------------------------------- #
def _collect_references(root: Path) -> tuple[dict[Path, str], dict[str, list[dict]], dict[str, str]]:
    """Read every page once; return texts, parsed references per page, and title -> arXiv id."""
    texts: dict[Path, str] = {}
    raw_refs: dict[str, list[dict]] = {}
    for path in problem_files(root):
        text = path.read_text(encoding="utf-8")
        texts[path] = text
        refs_block = split_sections(text).get("refs", "")
        raw_refs[str(path)] = [r for r in (parse_reference(l) for l in refs_block.splitlines()) if r]
    title_to_arxiv: dict[str, str] = {}
    for refs in raw_refs.values():
        for r in refs:
            if r["arxiv_id"]:
                title_to_arxiv.setdefault(norm_title(r["title"]), r["arxiv_id"])
    return texts, raw_refs, title_to_arxiv


def catalog_dates(root: Path, commit: str) -> tuple[str | None, str | None]:
    """(retrieved_at, source_date), both YYYY-MM-DD, read from the lock file next to the catalog
    (`lock_path(root)`, i.e. `<root>.lock.json`, the one place that layout is defined), which
    etl/download_data.py writes when it fetches the catalog
    and keeps while the checkout stays at that commit. So the dates are the recorded fetch and the
    commit's own date, the same on every rebuild of the same checkout. No lock for this commit
    (for example the test fixture) gives None for both: the properties are then left off the
    nodes (never a placeholder string, which would break their xsd:date range), and conformance
    check S4 fails."""
    from etl.download_data import lock_path, read_lock

    lock = read_lock(lock_path(root))
    if not lock or lock.get("commit") != commit:
        return None, None
    retrieved_at = str(lock.get("fetched_at") or "")[:10] or None
    source_date = str(lock.get("commit_date") or "")[:10] or None
    return retrieved_at, source_date


def choose_venues(raw_refs: dict[str, list[dict]], title_to_arxiv: dict[str, str],
                  ) -> tuple[dict[str, tuple[str, list[str]]], dict[tuple[str, str], tuple[str | None, str]]]:
    """One venue per paper over all its citations: a named venue beats a preprint server, then the
    most frequent, then the first seen. Returns paper id -> (venue, every other venue the catalog
    gives, preprint servers included) and, for each (paper, venue) pair, the raw venue text and
    the page (raw_refs key) it was first read from, so the Venue node's provenance names a page
    that really carries that venue."""
    seen: dict[str, list[str]] = defaultdict(list)
    first_seen: dict[tuple[str, str], tuple[str | None, str]] = {}
    for page, refs in raw_refs.items():
        for r in refs:
            if r["venue"]:
                ppid = paper_id(r, title_to_arxiv)
                seen[ppid].append(r["venue"])
                first_seen.setdefault((ppid, r["venue"]), (r["venue_raw"], page))
    chosen: dict[str, tuple[str, list[str]]] = {}
    for ppid, names in seen.items():
        counts = Counter(names)
        ranked = sorted(dict.fromkeys(names), key=lambda v: (v in PREPRINT_VENUES, -counts[v]))
        chosen[ppid] = (ranked[0], ranked[1:])
    return chosen, first_seen


def paper_id(r: dict, title_to_arxiv: dict[str, str]) -> str:
    """arXiv id first (also via a title seen elsewhere with one), then DOI, then a title hash."""
    ax = r["arxiv_id"] or title_to_arxiv.get(norm_title(r["title"]))
    if ax:
        return f"paper:arxiv:{ax}"
    if r["doi"]:
        return f"paper:doi:{r['doi'].lower()}"
    return f"paper:t:{short_hash(norm_title(r['title']))}"


def add_related_to(g: Graph, problem_papers: dict[str, set[str]], top_k: int, min_shared: int) -> None:
    """RELATED_TO: computed from shared cited papers (Jaccard), top-k per problem, stored once per pair."""
    by_paper: dict[str, set[str]] = defaultdict(set)
    for pid, papers in problem_papers.items():
        for pp in papers:
            by_paper[pp].add(pid)
    for pid, papers in problem_papers.items():
        shared = Counter()
        for pp in papers:
            for other in by_paper[pp]:
                if other != pid:
                    shared[other] += 1
        scored = []
        for other, n in shared.items():
            if n < min_shared:
                continue
            jac = n / len(papers | problem_papers[other])
            scored.append((jac, n, other))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        for jac, n, other in scored[:top_k]:
            a, b = sorted((pid, other))
            g.add_edge("Problem", a, "RELATED_TO", "Problem", b,
                       {"method": "shared_papers", "shared_papers": n, "score": round(jac, 3)})


def build_graph(root: Path, commit: str, related_top_k: int = 5, related_min_shared: int = 2) -> Graph:
    g = Graph()
    base_url = f"{REPO_WEB}/blob/{commit}"
    # provenance dates: when the pinned catalog was fetched, and the date of that version
    retrieved_at, source_date = catalog_dates(root, commit)
    common = {"provenance": "real", "source": SOURCE}
    if retrieved_at and source_date:        # absent, not a placeholder, when the catalog has no recorded fetch
        common.update(retrieved_at=retrieved_at, source_date=source_date)

    g.add_node("DataSource", "datasource:ai_research", name="ai_research catalog",
               url=REPO_WEB, version=commit, licence=LICENCE_NOTE, **common)

    topic_ids = {}
    for t in parse_taxonomy(root):
        tid = f"topic:{t['slug']}"
        topic_ids[t["slug"]] = tid
        g.add_node("Topic", tid, name=t["name"], slug=t["slug"], number=t["number"],
                   scope=t["scope"], source_url=f"{base_url}/TAXONOMY.md", method="parsed", **common)

    texts, raw_refs, title_to_arxiv = _collect_references(root)
    paper_venue, venue_first_seen = choose_venues(raw_refs, title_to_arxiv)
    page_url = {str(path): f"{base_url}/{path.relative_to(root).as_posix()}" for path in texts}
    problem_papers: dict[str, set[str]] = {}

    for path, text in texts.items():
        fm = parse_frontmatter(text)
        sec = split_sections(text)
        topic_slug = fm.get("topic") or path.parent.name
        pid = f"problem:{fm.get('id') or f'{topic_slug}/{path.stem}'}"
        src_url = f"{base_url}/{path.relative_to(root).as_posix()}"
        p_common = {**common, "source_url": src_url}

        g.add_node("Problem", pid, title=fm.get("title") or path.stem, slug=path.stem,
                   status=fm.get("status"), topic=topic_slug,
                   first_added=fm.get("first_added"), last_reviewed=fm.get("last_reviewed"),
                   last_substantive_update=fm.get("last_substantive_update"),
                   stale_since=fm.get("stale_since") or None,
                   catalog_provenance=fm.get("provenance"),
                   statement=first_paragraphs(sec.get("statement", "")),
                   method="parsed", **p_common)
        g.add_edge("Problem", pid, "FROM_SOURCE", "DataSource", "datasource:ai_research")
        if topic_slug in topic_ids:
            g.add_edge("Problem", pid, "IN_TOPIC", "Topic", topic_ids[topic_slug])

        # references -> Paper, Person, Venue
        papers_here = set()
        for pos, r in enumerate(raw_refs[str(path)], start=1):
            ppid = paper_id(r, title_to_arxiv)
            papers_here.add(ppid)
            venue, variants = paper_venue.get(ppid, (None, []))
            venue_raw, venue_page = venue_first_seen.get((ppid, venue), (None, None))
            g.add_node("Paper", ppid, title=r["title"], year=r["year"], arxiv_id=r["arxiv_id"],
                       doi=r["doi"], venue=venue,
                       venue_raw=venue_raw,                  # None when no venue was chosen: residue is not a venue
                       venue_variants=variants or None,      # a list: one entry per other venue the catalog gives
                       authors_raw=r["authors_raw"], method="parsed",
                       source_url=src_url, **common)
            g.add_edge("Problem", pid, "CITES", "Paper", ppid,
                       {"role": r["role"], "role_raw": r["role_raw"], "position": pos})
            for apos, name in enumerate(r["authors"], start=1):
                person = g.add_node("Person", f"person:{slug(name)}", name=name,
                                    name_form=name_form(name), method="parsed",
                                    source_url=src_url, **common)
                g.add_edge("Paper", ppid, "AUTHORED_BY", "Person", person, {"position": apos})
            if venue:
                vid = f"venue:{slug(venue)}"
                g.add_node("Venue", vid, name=venue, method="parsed",
                           source_url=page_url[venue_page], **common)   # the page that names this venue
                g.add_edge("Paper", ppid, "APPEARED_AT", "Venue", vid)
        problem_papers[pid] = papers_here

        # assumptions
        for i, a in enumerate(parse_assumptions(sec.get("formal", "")), start=1):
            aid = f"{pid}#assumption-{i}"
            g.add_node("Assumption", aid, name=a["name"], text=a["text"], violated=a["violated"],
                       method="parsed", **p_common)
            g.add_edge("Problem", pid, "RESTS_ON", "Assumption", aid, {"position": i})

        # open questions
        for i, q in enumerate(parse_gaps(sec.get("not_known", "")), start=1):
            qid = f"{pid}#gap-{i}"
            g.add_node("OpenQuestion", qid, kind=q["kind"], kind_raw=q["kind_raw"],
                       is_primary=q["is_primary"], text=q["text"], method="parsed", **p_common)
            g.add_edge("Problem", pid, "HAS_GAP", "OpenQuestion", qid, {"position": i})

        # obstructions
        found, detail = classify_obstructions(sec.get("hard", ""))
        for rank, key in enumerate(found):
            name = OBSTRUCTIONS[key][0] if key in OBSTRUCTIONS else "Other"
            g.add_node("Obstruction", f"obstruction:{key}", name=name,
                       method="keyword-classified", **common)
            g.add_edge("Problem", pid, "BLOCKED_BY", "Obstruction", f"obstruction:{key}",
                       {"detail": detail, "is_primary": rank == 0})

        # next experiment
        if sec.get("next", "").strip():
            e = parse_experiment(sec["next"])
            fid = f"{pid}#next-experiment"
            g.add_node("FutureDirection", fid, **e, method="parsed", **p_common)
            g.add_edge("Problem", pid, "HAS_NEXT_EXPERIMENT", "FutureDirection", fid)

        # labs active on the problem
        for d in parse_current_research(sec.get("current", "")):
            for lab in d["labs"]:
                iid, name, kind, _ = next(x for x in INSTITUTIONS if x[0] == lab)
                g.add_node("Institution", f"institution:{iid}", name=name, kind=kind,
                           method="name-matched", **common)
                g.add_edge("Institution", f"institution:{iid}", "ACTIVE_ON", "Problem", pid,
                           {"direction": d["direction"]})

    add_related_to(g, problem_papers, related_top_k, related_min_shared)
    return g


def main() -> None:
    from etl.download_data import CATALOG_DIR, catalog_commit

    commit = catalog_commit(CATALOG_DIR)
    g = build_graph(CATALOG_DIR, commit)
    n, e = g.counts()
    out = CATALOG_DIR.parent / "graph.json"
    out.write_text(json.dumps(g.to_json(), ensure_ascii=False))
    print(f"[parse] {sum(n.values()):,} nodes, {sum(e.values()):,} edges -> {out}")
    for k, v in n.items():
        print(f"  node {k:16s} {v:6,}")
    for k, v in e.items():
        print(f"  edge {k:20s} {v:6,}")


if __name__ == "__main__":
    main()
