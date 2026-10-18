"""Inputs and report table of the conformance tool.

Split out of etl/conformance.py, which holds the checks themselves, so that each file
stays short enough to review. Nothing here looks at the graph's content.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml

from etl.parse import Graph

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = ROOT / "schema" / "ai_research_kg.ttl"
VOCAB_PATH = ROOT / "schema" / "concepts.yaml"
KG = "https://samyama.ai/kg/ai-research/ontology#"

# Rules the graph breaks today, and where each fix is tracked. The test suite
# (tests/test_standards.py) expects exactly these failures, so fixing one means removing it here.
# v1.1 fixed the three v1 failures (two venues per paper O4, the empty id `venue:` C1, no
# retrieved_at S4), so the dict is empty; a new failure must be added here with its fix.
TRACKED_FAILURES: dict[str, str] = {}
# Open points that are not rule failures but need a decision; tracked in issue #6.
TRACKED_OPEN = {
    "S8": "ai_research states no licence, so DataSource.licence says 'none stated' → waiting on the lead "
          "(issue #6; CC BY 4.0 proposed as dbms_research). Blocks publishing a snapshot outside the team; "
          "building, and sharing the .sgsnap inside the team, go on",
    "O9": "assumption parsing: v1.1 reads the four forms the catalog uses (list, table, inline (i)/(ii), prose), "
          "405 → 220 problems without an Assumption (v1 as rebuilt on 2026-10-12; the first v1 build had 404); the 6 left that state assumptions use unheaded numbered lists (PR #5)",
}


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def load_vocab(path: Path = VOCAB_PATH) -> dict[str, dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["schemes"]


def codes(vocab: dict, scheme: str, in_graph_only: bool = False) -> set[str]:
    return {c["code"] for c in vocab[scheme]["concepts"]
            if c.get("status", "in_use") == "in_use" and not (in_graph_only and c.get("in_graph") is False)}


def load_ontology(path: Path = ONTOLOGY_PATH) -> dict:
    """Classes, edge types and property rules from the Turtle file.

    A property's name in the graph is its local name unless the file says otherwise with
    kg:propertyName (two classes both carry a ``kind``); rdfs:label is only a label.
    kg:notRequiredOn names the classes a kg:required property may be missing from.
    """
    from rdflib import OWL, RDF, RDFS, Namespace
    from rdflib import Graph as RDFGraph

    kg = Namespace(KG)
    g = RDFGraph().parse(path, format="turtle")

    def local(uri) -> str:
        return str(uri).split("#", 1)[1] if str(uri).startswith(KG) else str(uri)

    def ann(subject, name: str):
        return g.value(subject, kg[name])

    classes = {local(c): {"id_pattern": str(ann(c, "idPattern"))}
               for c in g.subjects(RDF.type, OWL.Class) if str(c).startswith(KG)}
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
        name = ann(p, "propertyName")
        dom = g.value(p, RDFS.domain)
        code_list = ann(p, "codeList")
        props[local(p)] = {
            "name": str(name) if name is not None else local(p),
            "domain": local(dom) if dom is not None else None,
            "required": bool(ann(p, "required")),
            "not_required_on": {local(c) for c in g.objects(p, kg["notRequiredOn"])},
            "code_list": str(code_list) if code_list is not None else None,
            "on_edge": bool(ann(p, "onEdge")),
        }
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


def inline_code(text: str) -> str:
    """Wrap text as Markdown inline code, surviving backticks inside the text."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


class Report:
    def __init__(self, examples: int = 5) -> None:
        """``examples`` is the default number of examples kept per check; 0 keeps them all."""
        self.examples = examples
        self.checks: list[Check] = []
        self.notes: dict[str, list[str]] = defaultdict(list)

    def add(self, section, cid, rule, bad, measured=None, info=False, limit=None):
        bad = [str(b) for b in bad]
        ok = None if info else not bad
        if measured is None:
            measured = "all pass" if not bad else f"{len(bad):,} fail"
        keep = None if self.examples == 0 else max(limit or 0, self.examples)
        self.checks.append(Check(section, cid, rule, ok, measured, bad[:keep]))

    def failures(self) -> list[Check]:
        return [c for c in self.checks if c.ok is False]

    def markdown(self, header: str) -> str:
        icon = {True: "✅", False: "❌", None: "ℹ️"}
        out = [header]
        for section in dict.fromkeys(c.section for c in self.checks):
            out += ["", f"## {section}", "", "| | Check | Rule | Measured | Examples |", "|---|---|---|---|---|"]
            for c in (c for c in self.checks if c.section == section):
                examples = "; ".join(inline_code(e) for e in c.examples).replace("|", "\\|")
                out.append(f"| {icon[c.ok]} | {c.cid} | {c.rule} | {c.measured} | {examples} |")
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
