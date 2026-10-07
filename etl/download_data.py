"""Fetch the ai_research catalog into ./data/ai_research at a pinned commit.

Re-runnable: same command, same files. The commit is pinned so a rebuild
gives the same graph; bump PINNED_COMMIT deliberately to take new problems.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
REPO_URL = "https://github.com/samyama-ai/ai_research.git"
PINNED_COMMIT = "a02e87b368016fd9568ba5ae8561ea601a8dee41"  # 2026-09-10, 1,000 problems
CATALOG_DIR = DATA_DIR / "ai_research"


def _git(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def download_all(commit: str = PINNED_COMMIT) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    if not (CATALOG_DIR / ".git").exists():
        _git("clone", "--quiet", REPO_URL, str(CATALOG_DIR))
    try:
        _git("checkout", "--quiet", commit, cwd=CATALOG_DIR)
    except subprocess.CalledProcessError:
        _git("fetch", "--quiet", "origin", cwd=CATALOG_DIR)
        _git("checkout", "--quiet", commit, cwd=CATALOG_DIR)
    head = _git("rev-parse", "HEAD", cwd=CATALOG_DIR)
    print(f"[download] {REPO_URL} @ {head[:12]} -> {CATALOG_DIR}")
    return CATALOG_DIR


if __name__ == "__main__":
    download_all()
