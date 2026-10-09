"""Export the built graph as a `.sgsnap`, and load it back without running the ETL.

    python -m etl.snapshot export --url http://127.0.0.1:8090   # after loading the graph into that server
    python -m etl.snapshot import --url http://127.0.0.1:8091   # into a FRESH server

WHY. Building the graph needs the catalog checkout (data/, not committed) and about a minute.
A snapshot is the built graph itself: anyone with a Samyama server can have it in seconds.

A `.sgsnap` is serialised ENGINE STATE, not a build. `snapshots/manifest.json` records the git commit
that built it, the engine version, the counts per label and relationship, and a SHA-256, so a stale
snapshot is visible. Re-export when the code or data changes.

THE TRAP (measured by interconnect-ip-kg, 2026-09-21; copied from enterprise-valuation-kg): import APPENDS, silently. A second import
into the same server doubles every node and edge, with no error. So `import`:
  - refuses a graph that is not empty (checked by QUERY, not by the status counters), and
  - counts again afterwards and fails unless every count equals the manifest.

Engine: samyama-graph 1.11.0 (`ghcr.io/samyama-ai/samyama-graph:latest`), which serves exactly
one graph named 'default'.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

import click

from etl.download_data import PINNED_COMMIT

ROOT = Path(__file__).resolve().parent.parent
SNAP_DIR = ROOT / "snapshots"
SNAP_FILE = SNAP_DIR / "ai-research.sgsnap"
MANIFEST = SNAP_DIR / "manifest.json"
GRAPH = "default"


def _post(url: str, body: bytes = b"", content_type: str | None = None, timeout: int = 600) -> bytes:
    req = urllib.request.Request(url, data=body, method="POST")
    if content_type:
        req.add_header("Content-Type", content_type)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def counts(url: str) -> dict:
    """What the graph holds, asked of the graph by query, never of /api/status."""
    from samyama import SamyamaClient

    c = SamyamaClient.connect(url)
    one = lambda q: c.query(q, GRAPH).records[0][0]  # noqa: E731
    rows = lambda q: c.query(q, GRAPH).records       # noqa: E731
    out = {"nodes": one("MATCH (n) RETURN count(n)"), "edges": one("MATCH ()-[r]->() RETURN count(r)")}
    # every label and relationship type the graph holds, counted by the graph itself
    out["labels"] = {lab: n for lab, n in sorted(
        rows("MATCH (n) WITH labels(n)[0] AS label, count(n) AS n RETURN label, n"))}
    out["relationships"] = {rel: n for rel, n in sorted(
        rows("MATCH ()-[r]->() WITH type(r) AS rel, count(r) AS n RETURN rel, n"))}
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!snapshots"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except OSError:
        return "unknown"


@click.group()
def cli() -> None:
    pass


@cli.command("export")
@click.option("--url", required=True)
def export_cmd(url: str) -> None:
    url = url.rstrip("/")
    before = counts(url)
    if not before["nodes"]:
        raise click.ClickException("the graph is empty: load it first (python -m etl.loader --url ...)")
    SNAP_DIR.mkdir(exist_ok=True)
    SNAP_FILE.write_bytes(_post(url + "/api/snapshot/export"))
    manifest = {
        "file": SNAP_FILE.name, "bytes": SNAP_FILE.stat().st_size, "sha256": sha256(SNAP_FILE),
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "commit": _commit(), "engine_version": _get(url + "/api/status").get("version"),
        "graph": GRAPH, "catalog": "github.com/samyama-ai/ai_research", "catalog_commit": PINNED_COMMIT,
        **before,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    click.echo(f"[snapshot] wrote {SNAP_FILE.relative_to(ROOT)} ({manifest['bytes'] / 1e6:.1f} MB): "
               f"{before['nodes']:,} nodes, {before['edges']:,} edges, engine {manifest['engine_version']}")
    if manifest["commit"].endswith("-dirty"):
        click.echo("[snapshot] warning: built from uncommitted changes; commit and re-export before sharing")


@cli.command("import")
@click.option("--url", required=True)
@click.option("--file", "path", type=click.Path(exists=True, path_type=Path), default=SNAP_FILE)
def import_cmd(url: str, path: Path) -> None:
    url = url.rstrip("/")
    manifest = json.loads(MANIFEST.read_text())
    if sha256(path) != manifest["sha256"]:
        raise click.ClickException("the snapshot's SHA-256 does not match manifest.json")
    have = counts(url)["nodes"]
    if have:
        raise click.ClickException(f"the graph already holds {have:,} nodes. Import APPENDS silently and would "
                                   "duplicate everything: use a fresh server container.")
    boundary = uuid.uuid4().hex
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{path.name}\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n").encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    _post(url + "/api/snapshot/import", body, f"multipart/form-data; boundary={boundary}")
    after = counts(url)
    diffs = {k: (after[k], manifest[k]) for k in ("nodes", "edges", "labels", "relationships") if after[k] != manifest[k]}
    if diffs:
        click.echo(json.dumps(diffs, indent=1))
        sys.exit("[snapshot] imported counts differ from the manifest (see above)")
    click.echo(f"[snapshot] imported and verified: {after['nodes']:,} nodes, {after['edges']:,} edges")


if __name__ == "__main__":
    cli()
