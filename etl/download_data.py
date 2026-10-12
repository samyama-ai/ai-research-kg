"""Fetch the ai_research catalog into ./data/ai_research at a pinned commit.

    python -m etl.download_data                 # clone or update, check out PINNED_COMMIT
    python -m etl.download_data --commit <sha>  # a different commit (bump PINNED_COMMIT to keep it)

Re-runnable: same command, same files. The commit is pinned so a rebuild gives
the same graph. The script refuses to continue when the checkout is not the
requested commit, when `data/ai_research` is not a clone of REPO_URL, or when
the working tree has local changes (they would silently change the graph).
Each run records what it did in `data/ai_research.lock.json` (repo, commit,
commit date, fetch time), which the loader and docs can cite.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPO_URL = "https://github.com/samyama-ai/ai_research.git"
PINNED_COMMIT = "a02e87b368016fd9568ba5ae8561ea601a8dee41"  # 2026-09-10, 1,000 problems
CATALOG_DIR = DATA_DIR / "ai_research"
LOCK_PATH = DATA_DIR / "ai_research.lock.json"


class CatalogError(RuntimeError):
    """The catalog checkout is not in the state a reproducible build needs."""


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def catalog_commit(root: Path = CATALOG_DIR) -> str:
    """The full SHA the catalog checkout is at."""
    if not (root / ".git").exists():
        raise CatalogError(f"{root} is not a git checkout; run python -m etl.download_data")
    return _git("rev-parse", "HEAD", cwd=root)


def check_catalog(root: Path = CATALOG_DIR, commit: str = PINNED_COMMIT) -> str:
    """Raise unless `root` is a clean clone of REPO_URL at `commit`; return the commit."""
    head = catalog_commit(root)
    if head != commit:
        raise CatalogError(f"catalog at {head[:8]}, not the pinned {commit[:8]}; run python -m etl.download_data")
    remote = _git("remote", "get-url", "origin", cwd=root)
    if remote.rstrip("/").removesuffix(".git") != REPO_URL.removesuffix(".git"):
        raise CatalogError(f"{root} is a clone of {remote}, not {REPO_URL}")
    if _git("status", "--porcelain", cwd=root):
        raise CatalogError(f"{root} has local changes; a build from it would not be reproducible")
    return head


def download_all(commit: str = PINNED_COMMIT) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    if CATALOG_DIR.exists() and not (CATALOG_DIR / ".git").exists():
        raise CatalogError(f"{CATALOG_DIR} exists but is not a git checkout; move it away first")
    if not CATALOG_DIR.exists():
        _git("clone", "--quiet", REPO_URL, str(CATALOG_DIR))
    try:
        _git("checkout", "--quiet", "--detach", commit, cwd=CATALOG_DIR)
    except subprocess.CalledProcessError:
        _git("fetch", "--quiet", "origin", cwd=CATALOG_DIR)
        _git("checkout", "--quiet", "--detach", commit, cwd=CATALOG_DIR)
    head = check_catalog(CATALOG_DIR, commit)
    lock = {
        "repo": REPO_URL,
        "commit": head,
        "commit_date": _git("show", "-s", "--format=%cI", head, cwd=CATALOG_DIR),
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "problem_files": len(list((CATALOG_DIR / "topics").glob("*/*.md"))),
    }
    LOCK_PATH.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
    print(f"[download] {REPO_URL} @ {head[:12]} ({lock['commit_date'][:10]}) -> {CATALOG_DIR}; lock: {LOCK_PATH.name}")
    return CATALOG_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--commit", default=PINNED_COMMIT, help="commit to check out (default: PINNED_COMMIT)")
    args = parser.parse_args(argv)
    try:
        download_all(args.commit)
    except (CatalogError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"[download] error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
