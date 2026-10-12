"""Invariants on the full graph, and README counts pinned to what the parser builds.

Skipped when the catalog has not been downloaded (`python -m etl.download_data`).
"""
import re
from collections import Counter
from pathlib import Path

import pytest

from etl.download_data import CATALOG_DIR, check_catalog
from etl.parse import build_graph

README = Path(__file__).resolve().parent.parent / "README.md"

pytestmark = pytest.mark.skipif(not (CATALOG_DIR / "TAXONOMY.md").exists(),
                                reason="catalog not downloaded; run python -m etl.download_data")


@pytest.fixture(scope="module")
def graph():
    commit = check_catalog(CATALOG_DIR)   # a clean clone of the right remote at the pinned commit, or an error
    return build_graph(CATALOG_DIR, commit)


def _readme_line(prefix: str) -> str:
    line = next((line for line in README.read_text(encoding="utf-8").splitlines() if line.startswith(prefix)), None)
    assert line, f"README line starting with {prefix!r} not found"
    return line


def test_ids_unique_across_labels(graph):
    ids = Counter(node_id for nodes in graph.nodes.values() for node_id in nodes)
    assert [node_id for node_id, n in ids.items() if n > 1] == []


def test_every_edge_endpoint_exists(graph):
    missing = [e for e in graph.edges
               if e[1] not in graph.nodes.get(e[0], {}) or e[4] not in graph.nodes.get(e[3], {})]
    assert missing == []


def test_every_node_has_provenance(graph):
    bad = [n["id"] for nodes in graph.nodes.values() for n in nodes.values()
           if not (n.get("id") and n.get("provenance") == "real" and n.get("source"))]
    assert bad == []


def test_catalog_shape(graph):
    n, _ = graph.counts()
    assert n["Problem"] == 1000
    assert n["Topic"] == 35
    problems_with_topic = {e[1] for e in graph.edges if e[2] == "IN_TOPIC"}
    assert len(problems_with_topic) == 1000


def test_readme_counts_match_the_graph(graph):
    n, e = graph.counts()
    m = re.search(r"\*\*([\d,]+) nodes\. ([\d,]+) edges\.", README.read_text(encoding="utf-8"))
    assert m, "README headline with node/edge counts not found"
    assert int(m.group(1).replace(",", "")) == sum(n.values())
    assert int(m.group(2).replace(",", "")) == sum(e.values())


def test_readme_label_counts_match_the_graph(graph):
    n, _ = graph.counts()
    line = _readme_line("**Node labels**")
    stated = {label: int(num.replace(",", "")) for label, num in re.findall(r"([A-Z][A-Za-z]+) ([\d,]+)", line)}
    assert stated == n


def test_readme_edge_counts_match_the_graph(graph):
    _, e = graph.counts()
    line = _readme_line("**Edge types**")
    stated = {rel: int(num.replace(",", "")) for rel, num in re.findall(r"`([A-Z_]+)` ([\d,]+)", line)}
    assert stated == e
