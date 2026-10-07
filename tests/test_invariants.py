"""Invariants on the full graph, and README counts pinned to what the parser builds.

Skipped when the catalog has not been downloaded (`python -m etl.download_data`).
"""
import re
import subprocess
from collections import Counter
from pathlib import Path

import pytest

from etl.download_data import CATALOG_DIR, PINNED_COMMIT
from etl.parse import build_graph

README = Path(__file__).resolve().parent.parent / "README.md"

pytestmark = pytest.mark.skipif(not (CATALOG_DIR / "TAXONOMY.md").exists(),
                                reason="catalog not downloaded; run python -m etl.download_data")


@pytest.fixture(scope="module")
def graph():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CATALOG_DIR, check=True,
                          capture_output=True, text=True).stdout.strip()
    assert head == PINNED_COMMIT, "catalog is not at the pinned commit"
    return build_graph(CATALOG_DIR, head)


def test_ids_unique_across_labels(graph):
    ids = Counter(i for label in graph.nodes.values() for i in label)
    assert [i for i, n in ids.items() if n > 1] == []


def test_every_edge_endpoint_exists(graph):
    missing = [e for e in graph.edges
               if e[1] not in graph.nodes[e[0]] or e[4] not in graph.nodes[e[3]]]
    assert missing == []


def test_every_node_has_provenance(graph):
    bad = [n["id"] for label in graph.nodes.values() for n in label.values()
           if not (n.get("id") and n.get("provenance") == "real" and n.get("source"))]
    assert bad == []


def test_catalog_shape(graph):
    n, _ = graph.counts()
    assert n["Problem"] == 1000
    assert n["Topic"] == 35
    every_problem_has_a_topic = {e[1] for e in graph.edges if e[2] == "IN_TOPIC"}
    assert len(every_problem_has_a_topic) == 1000


def test_readme_counts_match_the_graph(graph):
    n, e = graph.counts()
    m = re.search(r"\*\*([\d,]+) nodes\. ([\d,]+) edges\.", README.read_text(encoding="utf-8"))
    assert m, "README headline with node/edge counts not found"
    assert int(m.group(1).replace(",", "")) == sum(n.values())
    assert int(m.group(2).replace(",", "")) == sum(e.values())


def test_readme_label_counts_match_the_graph(graph):
    n, _ = graph.counts()
    line = next(l for l in README.read_text(encoding="utf-8").splitlines()
                if l.startswith("**Node labels**"))
    stated = {label: int(num.replace(",", ""))
              for label, num in re.findall(r"([A-Z][A-Za-z]+) ([\d,]+)", line)}
    assert stated == n
