"""Shared ETL helpers: id minting, Cypher literal rendering, batched writes.

Adapted from edge-ai-kg/etl/helpers.py. Engine notes baked in there apply here:

* Strings must be double-quoted. Embedded quotes, backslashes and newlines are
  stripped rather than escaped -- the parser does not accept backslash escapes.
* Floats must never be rendered in scientific notation.
* Edge creation matches endpoints with `WHERE`, not inline map properties --
  inline properties do not trigger an index scan on this build.
* `create_edges` batches 50 edges per statement (edge-ai-kg's measured optimum).

The write helpers return the number of rows *sent*, not confirmed created: the
engine's query result does not report a created count, and one unresolvable
endpoint id silently drops its whole edge batch. `etl/loader.py` therefore
counts nodes per label and edges per type after loading and fails on any
difference. Labels, relationship types and property keys are validated before
they are spliced into Cypher text.
"""
from __future__ import annotations

import hashlib
import math
import numbers
import re
import unicodedata
from collections.abc import Iterator, Sequence
from decimal import Decimal
from typing import Any

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def norm_id(prefix: str, value: str) -> str:
    return f"{prefix}:{value.strip().lower().replace(' ', '_')}"


def slug(text: str) -> str:
    """Lower-case slug that keeps letters of every script, so 'Łańcucki' and 'Lancucki' stay
    different ids: 'Findings of EMNLP' -> 'findings_of_emnlp', 'Vilém Zouhar' -> 'vilém_zouhar'."""
    return re.sub(r"[^\w]+", "_", unicodedata.normalize("NFKC", text).lower()).strip("_")


def short_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def identifier(name: str) -> str:
    """A label, relationship type or property key that is safe to splice into Cypher unquoted."""
    if not IDENTIFIER_RE.match(name):
        raise ValueError(f"not a safe Cypher identifier: {name!r}")
    return name


def _clean(text: Any) -> str:
    return (str(text).replace('"', "").replace("\\", "")
            .replace("\n", " ").replace("\r", " "))


def checked_id(value: Any) -> str:
    """An `id` must survive rendering unchanged, or two different ids could become one; refuse otherwise."""
    if not isinstance(value, str) or not value or _clean(value) != value:
        raise ValueError(f"id is empty or contains characters the engine would strip: {value!r}")
    return value


def _decimal_text(value: Decimal) -> str:
    """Plain decimal notation (never an exponent), trailing zeros trimmed, at least one decimal."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0")
        if text.endswith("."):
            text += "0"
    else:
        text += ".0"
    return text


def cypher_literal(value: Any) -> str:
    """Render a Python value as a Cypher literal this engine will accept.

    NaN and infinities have no Cypher literal and are rendered as `null`
    rather than invented as a number. Any integral or real type (including
    numpy scalars and Decimal) is accepted; floats are written in plain
    decimal notation so that 1e-07 does not become `1e-07` or `0.0`.
    """
    if value is None:
        return "null"
    if isinstance(value, bool) or getattr(getattr(value, "dtype", None), "kind", "") == "b":   # bool, numpy.bool_
        return "true" if bool(value) else "false"
    if isinstance(value, numbers.Integral):
        return str(int(value))
    if isinstance(value, Decimal):
        return "null" if not value.is_finite() else _decimal_text(value)
    if isinstance(value, numbers.Real):
        as_float = float(value)
        if math.isnan(as_float) or math.isinf(as_float):
            return "null"
        return _decimal_text(Decimal(repr(as_float)))
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(cypher_literal(v) for v in value) + "]"
    return f'"{_clean(value)}"'


def props_map(props: dict[str, Any]) -> str:
    """`{k: v, …}` for the non-None properties, or "" when there are none (so no empty `{}` is emitted)."""
    inner = ", ".join(f"{identifier(k)}: {cypher_literal(v)}"
                      for k, v in props.items() if v is not None)
    return "{" + inner + "}" if inner else ""


DEFAULT_EDGE_BATCH = 50


def chunked(items: Sequence, size: int) -> Iterator[Sequence]:
    for i in range(0, len(items), size):
        yield items[i:i + size]


def create_nodes(client, graph: str, label: str, rows: Sequence[dict],
                 batch: int = 250) -> int:
    """Batch-CREATE nodes. Returns the number of rows sent (see the module note)."""
    identifier(label)
    sent = 0
    for group in chunked(rows, batch):
        for r in group:
            checked_id(r.get("id"))
        parts = [f"(:{label} {props_map(r)})".replace(" )", ")") for r in group]
        client.query("CREATE " + ", ".join(parts), graph)
        sent += len(group)
    return sent


def create_edges(client, graph: str, edges: Sequence[tuple],
                 batch: int = DEFAULT_EDGE_BATCH) -> int:
    """Batch-CREATE edges. Returns the number of edges sent (see the module note).

    Each edge is `(src_label, src_id, rel_type, tgt_label, tgt_id, props|None)`
    and endpoints are looked up by their unique `id` property. A single
    unresolvable id silently drops its whole batch, so the loader verifies
    counts afterwards (see `etl/loader.py`).
    """
    sent = 0
    for group in chunked(edges, batch):
        var_of: dict[tuple[str, str], str] = {}
        match_parts, where_parts, create_parts = [], [], []
        for src_label, src_id, rel, tgt_label, tgt_id, props in group:
            for label, node_id in ((src_label, src_id), (tgt_label, tgt_id)):
                key = (label, node_id)
                if key not in var_of:
                    var = f"v{len(var_of)}"
                    var_of[key] = var
                    match_parts.append(f"({var}:{identifier(label)})")
                    where_parts.append(f"{var}.id = {cypher_literal(checked_id(node_id))}")
            rendered = props_map(props) if props else ""
            prop_part = f" {rendered}" if rendered else ""
            create_parts.append(
                f"({var_of[(src_label, src_id)]})-[:{identifier(rel)}{prop_part}]->"
                f"({var_of[(tgt_label, tgt_id)]})"
            )
        client.query(
            f"MATCH {', '.join(match_parts)} "
            f"WHERE {' AND '.join(where_parts)} "
            f"CREATE {', '.join(create_parts)}",
            graph,
        )
        sent += len(group)
    return sent
