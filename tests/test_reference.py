"""benchmarks/reference.py: every catalog query has a plain-Python answer, and check() can fail.

Runs on a small made-up graph, not on a download. A checker that can only pass is not a test, so
each way an engine answer can be wrong is shown to be caught.
"""
from __future__ import annotations

from benchmarks.queries import EXAMPLE_PROBLEM, QUERIES
from benchmarks.reference import Answer, G, answers, check


def node(label, nid, **props):
    return label, {"id": nid, **props}


def fixture() -> G:
    rows = [
        node("Topic", "t1", name="Alignment", number=1),
        node("Topic", "t2", name="Robustness", number=2),
        node("Problem", "p1", title="Verify internals", slug=EXAMPLE_PROBLEM, status="open",
             statement='Bound $\\theta$ with "quotes"'),
        node("Problem", "p2", title="Certify robustness", slug="certify", status="solved-but-impractical"),
        node("Problem", "p3", title="Detect drift", slug="drift", status="open"),
        node("FutureDirection", "f1", question="Q1", compute_budget_gpu_hours=5.0, single_machine=True),
        node("FutureDirection", "f2", question="Q2", compute_budget_gpu_hours=None, single_machine=True),
        node("FutureDirection", "f3", question="Q3", compute_budget_gpu_hours=50.0, single_machine=False),
        node("OpenQuestion", "q1", kind="theoretical"),
        node("Obstruction", "o1", name="scale"),
        node("Assumption", "a1", name="Linearity"),
        node("Institution", "i1", name="Lab A"),
        node("Person", "x1", name="Ada Lovelace", name_form="full"),
        node("Person", "x2", name="Alan Turing", name_form="full"),
        node("Paper", "pa1", title="Paper one", year=2020),
        node("Paper", "pa2", title="Paper two", year=None),
        node("Venue", "v1", name="NeurIPS"),
    ]
    nodes: dict[str, list] = {}
    for label, props in rows:
        nodes.setdefault(label, []).append(props)
    label = {props["id"]: lab for lab, props in rows}
    pairs = [
        ("p1", "IN_TOPIC", "t1", None), ("p2", "IN_TOPIC", "t2", None), ("p3", "IN_TOPIC", "t2", None),
        ("p1", "HAS_NEXT_EXPERIMENT", "f1", None), ("p2", "HAS_NEXT_EXPERIMENT", "f2", None),
        ("p3", "HAS_NEXT_EXPERIMENT", "f3", None),
        ("p1", "HAS_GAP", "q1", None), ("p1", "BLOCKED_BY", "o1", None), ("p2", "RESTS_ON", "a1", None),
        ("i1", "ACTIVE_ON", "p1", {"direction": "probes"}),
        ("p1", "CITES", "pa1", {"role": "survey"}), ("p2", "CITES", "pa1", {"role": "foundational"}),
        ("p3", "CITES", "pa2", {"role": "caution"}),
        ("pa1", "AUTHORED_BY", "x1", None), ("pa1", "AUTHORED_BY", "x2", None),
        ("pa1", "APPEARED_AT", "v1", None),
        ("p1", "RELATED_TO", "p2", {"shared_papers": 1, "score": 0.5}),
    ]
    edges = [[label[a], a, rel, label[b], b, props] for a, rel, b, props in pairs]
    return G({"nodes": nodes, "edges": edges})


def test_every_catalog_query_has_a_reference():
    assert set(answers(fixture())) == {q["id"] for q in QUERIES}


def test_reference_answers_on_the_fixture():
    a = answers(fixture())
    assert sorted(a["AR02"].rows) == [("open", 2), ("solved-but-impractical", 1)]
    assert sorted(a["AR14"].rows) == [("Paper one", 2020, 2), ("Paper two", None, 1)]
    assert sorted(a["AR15"].rows) == [("Paper one", 2), ("Paper two", 1)]     # topics per paper
    assert a["AR23"].rows == [("Ada Lovelace", "Alan Turing", 1)]       # never paired with herself
    assert sorted(a["AR24"].rows) == [("Certify robustness", 1), ("Verify internals", 1)]
    assert a["AR25"].rows == [("Alignment", "Robustness", 1)]
    assert sorted(a["AR30"].rows) == [("Detect drift",)]
    assert a["AR90"].rows == [] and a["AR91"].rows == []


def test_text_is_compared_as_the_loader_stores_it():
    assert answers(fixture())["AR10"].rows[0][3] == "Bound $theta$ with quotes"


def test_agreeing_rows_pass_and_ties_may_come_in_either_order():
    ref = Answer([("a", 2), ("b", 2), ("c", 1)], ((1, True),), 2)
    assert check([["b", 2], ["a", 2]], ref) == []
    assert check([["a", 2], ["b", 2]], ref) == []


def test_a_missing_row_is_caught():
    assert check([["a", 2]], Answer([("a", 2), ("b", 1)])) != []


def test_a_row_the_reference_lacks_is_caught():
    assert check([["a", 2], ["z", 9]], Answer([("a", 2), ("b", 1)])) != []


def test_wrong_order_is_caught():
    assert check([["c", 1], ["a", 3]], Answer([("a", 3), ("c", 1)], ((1, True),))) != []


def test_correct_rows_that_are_not_the_top_under_a_limit_are_caught():
    ref = Answer([("a", 3), ("b", 2), ("c", 1)], ((1, True),), 2)
    assert check([["a", 3], ["c", 1]], ref) != []


def test_null_sorts_last_ascending():
    ref = Answer([("x", None), ("y", 5.0)], ((1, False),))
    assert check([["y", 5.0], ["x", None]], ref) == []
    assert check([["x", None], ["y", 5.0]], ref) != []
