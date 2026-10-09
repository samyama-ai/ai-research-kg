"""Check the AI Research KG against its taxonomy, ontology, coding systems and standards.

    python -m etl.conformance                                # checks the graph the parser builds
    python -m etl.conformance --url http://127.0.0.1:8090    # ...and that the engine holds that graph
    python -m etl.conformance --write docs/conformance.md    # write the report

Every check is measured, not asserted. What is checked against:

    taxonomy        the catalog's TAXONOMY.md and topics/ folders (35 topics)
    ontology        ontology/ai_research_kg.ttl (classes, domain/range, cardinality)
    coding systems  id patterns in the ontology, vocab/concepts.yaml code lists, arXiv/DOI/ISO 8601
    standards       naming conventions, PROV-O provenance, computed-edge labelling (docs/standards.md)

A check fails (exit code 1) only on a rule the graph promises; measurements that
inform refinements (docs/taxonomy.md) are reported as information.
"""
from __future__ import annotations

import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import click
import yaml

from etl.download_data import CATALOG_DIR, PINNED_COMMIT
from etl.parse import Graph, build_graph, parse_taxonomy, problem_files, split_sections

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = ROOT / "ontology" / "ai_research_kg.ttl"
VOCAB_PATH = ROOT / "vocab" / "concepts.yaml"
KG = "https://samyama.ai/kg/ai-research/ontology#"


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def load_vocab(path: Path = VOCAB_PATH) -> dict[str, dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["schemes"]


def codes(vocab: dict, scheme: str, in_graph_only: bool = False) -> set[str]:
    return {c["code"] for c in vocab[scheme]["concepts"]
            if c.get("status", "in_use") == "in_use" and not (in_graph_only and c.get("in_graph") is False)}


def load_ontology(path: Path = ONTOLOGY_PATH) -> dict:
    """Classes, edge types and property rules from the Turtle file."""
    from rdflib import OWL, RDF, RDFS, Namespace
    from rdflib import Graph as RDFGraph

    kg = Namespace(KG)
    g = RDFGraph().parse(path, format="turtle")
    local = lambda u: str(u).split("#", 1)[1] if str(u).startswith(KG) else str(u)
    ann = lambda s, p: g.value(s, kg[p])
    classes = {}
    for c in g.subjects(RDF.type, OWL.Class):
        if str(c).startswith(KG):
            classes[local(c)] = {"id_pattern": str(ann(c, "idPattern"))}
    edges = {}
    for p in g.subjects(RDF.type, OWL.ObjectProperty):
        rule = {"domain": local(g.value(p, RDFS.domain)), "range": local(g.value(p, RDFS.range))}
        for k in ("minCount", "maxCount", "inverseMinCount", "inverseMaxCount"):
            v = ann(p, k)
            rule[k] = int(v) if v is not None else None
        rule["computed"] = bool(ann(p, "computed"))
        rule["symmetric"] = (p, RDF.type, OWL.SymmetricProperty) in g
        edges[local(p)] = rule
    props = {}
    for p in g.subjects(RDF.type, OWL.DatatypeProperty):
        label = g.value(p, RDFS.label)
        name = str(label) if label is not None else local(p)
        dom = g.value(p, RDFS.domain)
        props[local(p)] = {"name": name, "domain": local(dom) if dom is not None else None,
                           "required": bool(ann(p, "required")),
                           "code_list": str(ann(p, "codeList")) if ann(p, "codeList") is not None else None,
                           "on_edge": bool(ann(p, "onEdge"))}
    return {"classes": classes, "edges": edges, "props": props, "triples": len(g)}


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
@dataclass
class Check:
    section: str
    cid: str
    rule: str
    ok: bool | None          # True pass, False fail, None information only
    measured: str
    examples: list[str]


class Report:
    def __init__(self) -> None:
        self.checks: list[Check] = []
        self.notes: dict[str, list[str]] = defaultdict(list)

    def add(self, section, cid, rule, bad, measured=None, info=False, limit=5):
        bad = list(bad)
        ok = None if info else not bad
        if measured is None:
            measured = "all pass" if not bad else f"{len(bad):,} fail"
        self.checks.append(Check(section, cid, rule, ok, measured, [str(b) for b in bad[:limit]]))

    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.ok is False]

    def markdown(self, header: str) -> str:
        icon = {True: "✅", False: "❌", None: "ℹ️"}
        out = [header]
        for section in dict.fromkeys(c.section for c in self.checks):
            out += ["", f"## {section}", "", "| | Check | Rule | Measured | Examples |", "|---|---|---|---|---|"]
            for c in (c for c in self.checks if c.section == section):
                ex = "; ".join(f"`{e}`" if len(e) < 90 else e for e in c.examples).replace("|", "\\|")
                out.append(f"| {icon[c.ok]} | {c.cid} | {c.rule} | {c.measured} | {ex} |")
            for note in self.notes.get(section, []):
                out += ["", note]
        return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Graph helpers
# --------------------------------------------------------------------------- #
def edges_by_type(g: Graph) -> dict[str, list[tuple]]:
    out = defaultdict(list)
    for e in g.edges:
        out[e[2]].append(e)
    return out


def label_of(g: Graph) -> dict[str, str]:
    return {nid: label for label, nodes in g.nodes.items() for nid in nodes}


# --------------------------------------------------------------------------- #
# 1. Taxonomy
# --------------------------------------------------------------------------- #
SCOPE_STOP = {"and", "with", "of", "the", "for", "over", "in", "to", "llms", "a"}


def _stems(term: str) -> list[str]:
    return [w[:6] for w in re.findall(r"[a-z0-9]+", term.lower()) if w not in SCOPE_STOP and len(w) > 1]


def check_taxonomy(r: Report, g: Graph, root: Path, vocab: dict, areas: dict[int, str]) -> dict:
    S = "1. Taxonomy (TAXONOMY.md, 35 topics)"
    rows = parse_taxonomy(root)
    topics = g.nodes["Topic"]
    problems = g.nodes["Problem"]
    by_type = edges_by_type(g)

    r.add(S, "T1", "One Topic node per TAXONOMY.md row (35)",
          [] if len(rows) == len(topics) == 35 else [f"{len(rows)} rows, {len(topics)} nodes"],
          f"{len(rows)} rows · {len(topics)} Topic nodes")
    bad = []
    for t in rows:
        node = topics.get(f"topic:{t['slug']}")
        if node is None:
            bad.append(f"missing {t['slug']}")
            continue
        for k in ("number", "name", "slug", "scope"):
            if node.get(k) != t[k]:
                bad.append(f"{t['slug']}.{k}")
        if not t["slug"].startswith(f"{t['number']:02d}-"):
            bad.append(f"{t['slug']}: number {t['number']}")
    r.add(S, "T2", "Topic number, name, slug and scope equal the TAXONOMY.md row; slug starts with the number", bad)
    dirs = sorted(p.name for p in (root / "topics").iterdir() if p.is_dir())
    r.add(S, "T3", "Every topics/ folder is a TAXONOMY.md topic, and the reverse",
          sorted(set(dirs) ^ {t["slug"] for t in rows}), f"{len(dirs)} folders")

    in_topic = Counter(e[1] for e in by_type["IN_TOPIC"])
    r.add(S, "T4", "Every Problem has exactly one IN_TOPIC edge",
          [p for p in problems if in_topic[p] != 1], f"{len(problems):,} problems")
    bad = []
    for e in by_type["IN_TOPIC"]:
        p = problems[e[1]]
        slug_ = e[4].split(":", 1)[1]
        if p["topic"] != slug_ or not e[1].startswith(f"problem:{slug_}/"):
            bad.append(e[1])
    r.add(S, "T5", "IN_TOPIC target = the problem's folder = its frontmatter topic = its id prefix", bad)
    files = Counter(p.parent.name for p in problem_files(root))
    graph_n = Counter(e[4].split(":", 1)[1] for e in by_type["IN_TOPIC"])
    r.add(S, "T6", "Problems per topic in the graph = problem files per folder",
          [f"{t}: {graph_n[t]} vs {files[t]}" for t in files if graph_n[t] != files[t]],
          f"{min(graph_n.values())}–{max(graph_n.values())} problems per topic")
    r.add(S, "T7", "Problem.status is on the problem_status list",
          [f"{p}: {v['status']}" for p, v in problems.items() if v.get("status") not in codes(vocab, "problem_status")],
          ", ".join(f"{k} {v}" for k, v in Counter(v["status"] for v in problems.values()).most_common()))

    # ---- refinement measurements (information) ----
    texts = {}
    for path in problem_files(root):
        text = path.read_text(encoding="utf-8").lower()
        texts[f"problem:{path.parent.name}/{path.stem}"] = text.split("## 3.")[0]
    empty_terms, unmatched, term_total = [], [], 0
    for t in rows:
        terms = [x.strip() for x in t["scope"].split(",") if x.strip()]
        mine = {pid: tx for pid, tx in texts.items() if pid.startswith(f"problem:{t['slug']}/")}
        hit_any = set()
        for term in terms:
            term_total += 1
            alts = [a for a in term.split("/") if _stems(a)]
            hits = {pid for pid, tx in mine.items() if any(all(s in tx for s in _stems(a)) for a in alts)}
            hit_any |= hits
            if not hits:
                empty_terms.append(f"{t['number']:02d} {term}")
        unmatched += [pid for pid in mine if pid not in hit_any]
    r.add(S, "T8", "Each scope term names at least one problem in its topic (keyword match on title, statement, formal setting)",
          empty_terms, f"{term_total - len(empty_terms)} of {term_total} terms matched", info=True, limit=18)
    r.add(S, "T9", "Each problem matches at least one scope term of its topic",
          unmatched, f"{len(problems) - len(unmatched):,} of {len(problems):,} problems matched", info=True)

    topic_of = {pid: v["topic"] for pid, v in problems.items()}
    nb = defaultdict(Counter)
    for e in by_type["RELATED_TO"]:
        nb[e[1]][topic_of[e[4]]] += 1
        nb[e[4]][topic_of[e[1]]] += 1
    secondary = []
    for pid, cnt in sorted(nb.items()):
        total = sum(cnt.values())
        others = [(t, n) for t, n in cnt.items() if t != topic_of[pid]]
        if total >= 3 and others:
            t, n = max(others, key=lambda x: (x[1], x[0]))
            if n / total >= 2 / 3:
                secondary.append((pid, t, n, total))
    r.add(S, "T10", "Problems whose RELATED_TO neighbours sit mostly (≥ 2/3, ≥ 3 links) in one other topic",
          [f"{p} → {t} ({n}/{tot})" for p, t, n, tot in secondary],
          f"{len(secondary)} candidates for a secondary topic", info=True)
    cross = sum(1 for e in by_type["RELATED_TO"] if topic_of[e[1]] != topic_of[e[4]])
    area_of = lambda pid: areas.get(int(topic_of[pid][:2]))
    same_area = sum(1 for e in by_type["RELATED_TO"] if area_of(e[1]) == area_of(e[4]))
    n_rel = len(by_type["RELATED_TO"])
    r.add(S, "T11", "RELATED_TO links that cross topics / stay inside one proposed topic area (vocab topic_area)", [],
          f"{cross:,} of {n_rel:,} cross topics ({cross / n_rel:.0%}); {same_area:,} ({same_area / n_rel:.0%}) stay inside one area",
          info=True)
    return {"secondary": secondary, "empty_terms": empty_terms, "unmatched": unmatched}


# --------------------------------------------------------------------------- #
# 2. Ontology
# --------------------------------------------------------------------------- #
ASSUMPTION_HEAD_RE = re.compile(r"\*\*[^*\n]{0,40}assum[^*\n]{0,40}\*\*", re.I)


def check_ontology(r: Report, g: Graph, onto: dict, root: Path) -> None:
    S = "2. Ontology (ontology/ai_research_kg.ttl)"
    labels = set(g.nodes)
    types = {e[2] for e in g.edges}
    r.add(S, "O1", "Node labels in the graph = classes in the ontology",
          sorted(labels ^ set(onto["classes"])), f"{len(labels)} labels · {len(onto['classes'])} classes")
    r.add(S, "O2", "Edge types in the graph = object properties in the ontology",
          sorted(types ^ set(onto["edges"])), f"{len(types)} types · {len(onto['edges'])} properties")
    by_type = edges_by_type(g)
    bad = [f"{e[2]} {e[0]}→{e[3]}" for e in g.edges
           if e[2] in onto["edges"] and (e[0], e[3]) != (onto["edges"][e[2]]["domain"], onto["edges"][e[2]]["range"])]
    r.add(S, "O3", "Every edge goes from its property's domain to its range", sorted(set(bad)),
          f"{len(g.edges):,} edges")
    bad = []
    for t, rule in onto["edges"].items():
        out_n = Counter(e[1] for e in by_type[t])
        in_n = Counter(e[4] for e in by_type[t])
        for nid in g.nodes.get(rule["domain"], {}):
            if rule["minCount"] is not None and out_n[nid] < rule["minCount"]:
                bad.append(f"{t}: {nid} has {out_n[nid]} < {rule['minCount']}")
            if rule["maxCount"] is not None and out_n[nid] > rule["maxCount"]:
                bad.append(f"{t}: {nid} has {out_n[nid]} > {rule['maxCount']}")
        for nid in g.nodes.get(rule["range"], {}):
            if rule["inverseMinCount"] is not None and in_n[nid] < rule["inverseMinCount"]:
                bad.append(f"{t}: {nid} has {in_n[nid]} incoming < {rule['inverseMinCount']}")
            if rule["inverseMaxCount"] is not None and in_n[nid] > rule["inverseMaxCount"]:
                bad.append(f"{t}: {nid} has {in_n[nid]} incoming > {rule['inverseMaxCount']}")
    r.add(S, "O4", "Cardinalities (kg:minCount, maxCount, inverseMinCount, inverseMaxCount)", bad)
    bad = []
    for p in onto["props"].values():
        if not p["required"]:
            continue
        for label in ([p["domain"]] if p["domain"] else labels):
            for nid, node in g.nodes.get(label, {}).items():
                if node.get(p["name"]) in (None, ""):
                    bad.append(f"{label}.{p['name']} missing on {nid}")
    for label in labels - {"DataSource"}:
        bad += [f"{label}.method missing on {nid}" for nid, n in g.nodes[label].items() if not n.get("method")]
    r.add(S, "O5", "Required properties are present (kg:required; method on every node but DataSource)", bad)
    primary = Counter(e[1] for e in by_type["BLOCKED_BY"] if e[5] and e[5].get("is_primary"))
    r.add(S, "O6", "Exactly one BLOCKED_BY per problem has is_primary = true",
          [p for p in g.nodes["Problem"] if primary[p] != 1])
    pairs = Counter(tuple(sorted((e[1], e[4]))) for e in by_type["RELATED_TO"])
    bad = [f"{e[1]}→{e[4]}" for e in by_type["RELATED_TO"] if e[1] >= e[4]]
    bad += [f"duplicate pair {p}" for p, n in pairs.items() if n > 1]
    r.add(S, "O7", "Symmetric RELATED_TO is stored once per pair, smaller id first", bad)
    linked = {e[1] for e in g.edges} | {e[4] for e in g.edges}
    r.add(S, "O8", "No orphan nodes", [nid for label in labels for nid in g.nodes[label] if nid not in linked])

    rests = {e[1] for e in by_type["RESTS_ON"]}
    gaps = {e[1] for e in by_type["HAS_GAP"]}
    no_rests = [p for p in g.nodes["Problem"] if p not in rests]
    missed = []
    for pid in no_rests:
        sec = split_sections((root / "topics" / f"{pid.split(':', 1)[1]}.md").read_text(encoding="utf-8"))
        if ASSUMPTION_HEAD_RE.search(sec.get("formal", "")):
            missed.append(pid)
    r.add(S, "O9", "Problems with no RESTS_ON although their Formal Setting has a bold 'Assumptions…' heading (parser gap)",
          missed, f"{len(no_rests)} problems have no Assumption; {len(missed)} of them do state assumptions",
          info=True)
    r.add(S, "O10", "Problems with no HAS_GAP (no labelled item in What Is Not Known)",
          [p for p in g.nodes["Problem"] if p not in gaps], info=True,
          measured=f"{sum(1 for p in g.nodes['Problem'] if p not in gaps)} problems")


# --------------------------------------------------------------------------- #
# 3. Coding systems
# --------------------------------------------------------------------------- #
ARXIV_RE = re.compile(r"^(\d{2})(\d{2})\.(\d{4,5})$")
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
YM_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def check_coding(r: Report, g: Graph, onto: dict, vocab: dict) -> None:
    S = "3. Coding systems (identifiers and code lists)"
    bad = []
    for label, nodes in g.nodes.items():
        rx = re.compile(onto["classes"][label]["id_pattern"])
        bad += [nid for nid in nodes if not rx.match(nid)]
    r.add(S, "C1", "Every id matches its class's kg:idPattern", bad,
          f"{len(bad)} of {sum(len(v) for v in g.nodes.values()):,} ids fail")
    ids = Counter(nid for nodes in g.nodes.values() for nid in nodes)
    r.add(S, "C2", "Ids are unique across the whole graph", [i for i, n in ids.items() if n > 1])
    nums = sorted(t["number"] for t in g.nodes["Topic"].values())
    r.add(S, "C3", "Topic numbers are 1–35, each used once", [] if nums == list(range(1, 36)) else [str(nums)])

    papers = g.nodes["Paper"]
    bad, warn = [], []
    for pid, p in papers.items():
        ax = p.get("arxiv_id")
        if pid.startswith("paper:arxiv:") and ax and pid != f"paper:arxiv:{ax}":
            bad.append(f"{pid} vs arxiv_id {ax}")
        if not ax:
            continue
        m = ARXIV_RE.match(ax)
        if not m or not 1 <= int(m[2]) <= 12 or (int(m[1]) >= 15) != (len(m[3]) == 5):
            bad.append(f"{pid}: {ax}")
        elif p.get("year") and p["year"] < 2000 + int(m[1]):
            warn.append(f"{pid}: year {p['year']}, arXiv 20{m[1]}")
    kinds = Counter(pid.split(":")[1] for pid in papers)
    r.add(S, "C4", "arXiv identifiers are valid (YYMM month 01–12; 5 digits from 2015, 4 before) and equal the id", bad,
          f"{sum(1 for p in papers.values() if p.get('arxiv_id')):,} arXiv ids")
    r.add(S, "C5", "Paper.year earlier than its arXiv id's year (venue year precedes posting; not an error)", warn,
          f"{len(warn)} papers", info=True)
    r.add(S, "C6", "DOIs match 10.NNNN/suffix", [p["doi"] for p in papers.values() if p.get("doi") and not DOI_RE.match(p["doi"])],
          f"{sum(1 for p in papers.values() if p.get('doi'))} DOI · paper ids: "
          + ", ".join(f"{k} {v:,}" for k, v in kinds.most_common()))
    bad = [f"{pid}.{k}={v[k]}" for pid, v in g.nodes["Problem"].items()
           for k in ("first_added", "last_reviewed", "last_substantive_update", "stale_since")
           if v.get(k) not in (None, "") and not YM_RE.match(str(v[k]))]
    r.add(S, "C7", "Problem dates are ISO 8601 year-month (YYYY-MM)", bad)
    src = g.nodes["DataSource"]
    r.add(S, "C8", "DataSource.version is a 40-hex git commit equal to the pinned commit",
          [d.get("version") for d in src.values() if d.get("version") != PINNED_COMMIT or not re.fullmatch(r"[0-9a-f]{40}", d.get("version", ""))])

    # code lists
    node_props = [("Problem", "status", "problem_status"), ("Problem", "catalog_provenance", "catalog_provenance"),
                  ("OpenQuestion", "kind", "gap_kind"), ("Assumption", "violated", "assumption_status"),
                  ("Person", "name_form", "name_form"), ("Institution", "kind", "institution_kind")]
    bad, used = [], defaultdict(Counter)
    for label, prop, scheme in node_props:
        for nid, n in g.nodes[label].items():
            used[scheme][n.get(prop)] += 1
            if n.get(prop) not in codes(vocab, scheme):
                bad.append(f"{nid}.{prop}={n.get(prop)}")
    for label, nodes in g.nodes.items():
        for nid, n in nodes.items():
            used["provenance"][n.get("provenance")] += 1
            if n.get("provenance") not in codes(vocab, "provenance"):
                bad.append(f"{nid}.provenance")
            if label != "DataSource":
                used["extraction_method"][n.get("method")] += 1
                if n.get("method") not in codes(vocab, "extraction_method"):
                    bad.append(f"{nid}.method={n.get('method')}")
    for nid in g.nodes["Obstruction"]:
        used["obstruction"][nid.split(":", 1)[1]] += 1
        if nid.split(":", 1)[1] not in codes(vocab, "obstruction"):
            bad.append(nid)
    for e in edges_by_type(g)["CITES"]:
        used["cites_role"][e[5]["role"]] += 1
        if e[5]["role"] not in codes(vocab, "cites_role"):
            bad.append(f"CITES.role={e[5]['role']}")
    for e in edges_by_type(g)["RELATED_TO"]:
        used["relatedness_method"][e[5]["method"]] += 1
        if e[5]["method"] not in codes(vocab, "relatedness_method") or not 0 < e[5]["score"] <= 1:
            bad.append(f"RELATED_TO {e[1]}: {e[5]}")
    r.add(S, "C9", "Every coded value is on its vocab/concepts.yaml list (10 schemes)", bad,
          f"{sum(sum(c.values()) for c in used.values()):,} values checked")
    unused = [f"{s}:{c}" for s in used for c in codes(vocab, s, in_graph_only=True) if not used[s][c]]
    r.add(S, "C10", "Every in-use code is used at least once (a code nobody uses should go)", unused)
    lines = ["**Code-list usage (measured):**", ""]
    for s in sorted(used):
        lines.append(f"- `{s}`: " + ", ".join(f"{k} {v:,}" for k, v in used[s].most_common()))
    r.notes[S].append("\n".join(lines))

    venues = g.nodes["Venue"]
    per_venue = Counter(e[4] for e in edges_by_type(g)["APPEARED_AT"])
    residue = [v["name"] for v in venues.values()
               if not re.search(r"[A-Za-z]{2}", v["name"]) or re.search(r"[(/]|^\W|, –|\.\s*\(", v["name"])]
    r.add(S, "C11", "Venue names are clean venue names (no parser residue)", residue,
          f"{len(venues)} venues, {sum(1 for v in venues if per_venue[v] == 1)} with a single paper; "
          f"{len(residue)} look like residue", info=True)
    variants = Counter(f"{p['venue']} vs {p['venue_variants']}" for p in g.nodes["Paper"].values()
                       if p.get("venue_variants"))
    r.add(S, "C13", "Papers the catalog gives other venues for (kept in Paper.venue_variants; APPEARED_AT holds the chosen one)",
          [f"{p} ({n})" for p, n in variants.most_common()], f"{sum(variants.values())} papers", info=True, limit=8)
    persons = g.nodes["Person"]
    short = sum(1 for p in persons.values() if p["name_form"] in ("initials", "surname"))
    r.add(S, "C12", "Person identity: share of names that are initials or surname only (no DBLP/ORCID id in v1)", [],
          f"{short:,} of {len(persons):,} ({short / len(persons):.0%})", info=True)


# --------------------------------------------------------------------------- #
# 4. Standards
# --------------------------------------------------------------------------- #
def check_standards(r: Report, g: Graph) -> None:
    S = "4. Standards (naming, PROV-O provenance, computed edges)"
    r.add(S, "S1", "Node labels are PascalCase singular; edge types UPPER_SNAKE (as the DBMS and Valuation KGs)",
          [l for l in g.nodes if not re.fullmatch(r"[A-Z][a-z]+(?:[A-Z][a-z]+)*", l) or l.endswith("s")]
          + [t for t in {e[2] for e in g.edges} if not re.fullmatch(r"[A-Z]+(?:_[A-Z]+)*", t)])
    r.add(S, "S2", "PROV-O: every node names its source (`source`) and kind (`provenance`)",
          [nid for nodes in g.nodes.values() for nid, n in nodes.items() if not n.get("source") or not n.get("provenance")])
    no_url = Counter(label for label, nodes in g.nodes.items() for n in nodes.values() if not n.get("source_url"))
    r.add(S, "S3", "PROV-O: nodes read from one page carry `source_url` (prov:hadPrimarySource)",
          [f"{l}: {n}" for l, n in no_url.items() if l not in ("Institution", "Obstruction", "DataSource")],
          "pass; shared nodes (" + ", ".join(f"{l} {n}" for l, n in sorted(no_url.items()))
          + ") have no single page, by design")
    r.add(S, "S4", "PROV-O dates on every node, as docs/schema.md §4 requires: `retrieved_at` (when the pinned "
          "catalog was fetched) and `source_date` (the date of that catalog version)",
          sorted({l for l, nodes in g.nodes.items() for n in nodes.values()
                  if not n.get("retrieved_at") or not n.get("source_date")}),
          f"{sum(1 for v in g.nodes.values() for n in v.values() if n.get('retrieved_at') and n.get('source_date')):,} of "
          f"{sum(len(v) for v in g.nodes.values()):,} nodes carry both")
    r.add(S, "S5", "Edges carry provenance (docs/schema.md §4: 'every node and edge'); today only the problem page at the edge's source implies it",
          sorted({e[2] for e in g.edges if not (e[5] or {}).get("source")}),
          "no edge carries `source`", info=True)
    r.add(S, "S6", "Computed edges say so: RELATED_TO carries method and score",
          [e[1] for e in edges_by_type(g)["RELATED_TO"] if not e[5] or "method" not in e[5] or "score" not in e[5]])
    r.add(S, "S7", "No Person named 'et al.' and no empty names",
          [p["name"] for p in g.nodes["Person"].values() if not p["name"].strip() or re.search(r"\bet al\b", p["name"], re.I)])
    lic = [d.get("licence") for d in g.nodes["DataSource"].values()]
    r.add(S, "S8", "The DataSource states a licence (CC BY 4.0 proposed, as dbms_research)", [], f"licence = {lic}", info=True)


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
def check_engine(r: Report, g: Graph, url: str) -> None:
    from samyama import SamyamaClient

    S = "5. Loaded graph (engine)"
    client = SamyamaClient.connect(url)
    one = lambda cy: client.query(cy).records[0][0]
    n_want, e_want = g.counts()
    bad = []
    for label, want in n_want.items():
        got = one(f"MATCH (n:{label}) RETURN count(n)")
        if got != want:
            bad.append(f"{label}: engine {got} vs build {want}")
    for t, want in e_want.items():
        got = one(f"MATCH ()-[r:{t}]->() RETURN count(r)")
        if got != want:
            bad.append(f"{t}: engine {got} vs build {want}")
    total_n, total_e = one("MATCH (n) RETURN count(n)"), one("MATCH ()-[r]->() RETURN count(r)")
    r.add(S, "E1", f"The engine at {url} holds exactly the graph checked above (counts per label and edge type)", bad,
          f"{total_n:,} nodes · {total_e:,} edges")


# --------------------------------------------------------------------------- #
@click.command()
@click.option("--url", default=None, help="Also compare with a running Samyama server.")
@click.option("--write", "write_path", type=click.Path(path_type=Path), default=None, help="Write the Markdown report here.")
def cli(url, write_path):
    root = CATALOG_DIR
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    if commit != PINNED_COMMIT:
        raise click.ClickException(f"catalog at {commit[:8]}, not the pinned {PINNED_COMMIT[:8]}")
    g = build_graph(root, commit)
    vocab, onto = load_vocab(), load_ontology()
    areas = {n: c["code"] for c in vocab["topic_area"]["concepts"] for n in c["topics"]}
    r = Report()
    check_taxonomy(r, g, root, vocab, areas)
    check_ontology(r, g, onto, root)
    check_coding(r, g, onto, vocab)
    check_standards(r, g)
    if url:
        check_engine(r, g, url)
    n, e = g.counts()
    fails = r.failures()
    header = "\n".join([
        "# Conformance report",
        "",
        f"Generated by `python -m etl.conformance{' --url ' + url if url else ''}` on {date.today().isoformat()}. "
        f"Catalog `ai_research` at `{commit[:8]}`; {sum(n.values()):,} nodes, {sum(e.values()):,} edges. "
        "Do not edit by hand: rerun the command.",
        "",
        "✅ the graph keeps the rule · ❌ it breaks the rule · ℹ️ a measurement for review (docs/taxonomy.md, docs/standards.md)",
        "",
        f"**Result: {sum(1 for c in r.checks if c.ok)} pass, {len(fails)} fail, "
        f"{sum(1 for c in r.checks if c.ok is None)} measurements.**",
    ])
    text = r.markdown(header)
    if write_path:
        write_path.write_text(text, encoding="utf-8")
        click.echo(f"[conformance] wrote {write_path}")
    else:
        click.echo(text)
    for c in fails:
        click.echo(f"FAIL {c.cid}: {c.rule} -- {c.measured}", err=True)
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    cli()
