"""Small Markdown helpers for the catalog pages: sections, frontmatter, lists, plain text."""
from __future__ import annotations

import re

from etl.rules import SECTION_KEYS


def strip_md(text: str) -> str:
    """Drop bold/italic/code marks and link targets; collapse whitespace."""
    text = re.sub(r"\*\*|__|`", "", text)
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def first_paragraphs(text: str, limit: int = 1200) -> str:
    """The opening paragraphs as plain text: at least ~300 characters, at most `limit`."""
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = strip_md(para)
        if not para:
            continue
        out.append(para)
        if sum(len(p) for p in out) >= 300:
            break
    joined = " ".join(out)
    return joined[:limit].rstrip() + ("…" if len(joined) > limit else "")


def norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def split_sections(text: str) -> dict[str, str]:
    """Numbered `## N. Heading` sections keyed by heading text (SECTION_KEYS), not number."""
    sections = {}
    for m in re.finditer(r"^## \d+\.\s*([^\n]+)\n(.*?)(?=^## |\Z)", text, re.M | re.S):
        title = m.group(1).strip().lower()
        for prefix, key in SECTION_KEYS.items():
            if title.startswith(prefix):
                sections[key] = m.group(2)
                break
    return sections


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    out = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        line = line.split(" #", 1)[0].rstrip()
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def list_items(block: str) -> list[str]:
    """Top-level list items (`- x` or `1. x`), continuation lines joined."""
    items, cur = [], None
    for line in block.splitlines():
        if re.match(r"^(?:-|\*|\d+\.)\s+\S", line):
            if cur is not None:
                items.append(cur)
            cur = re.sub(r"^(?:-|\*|\d+\.)\s+", "", line)
        elif cur is not None and line.startswith((" ", "\t")) and line.strip():
            cur += " " + line.strip()
        elif cur is not None and not line.strip():
            continue
        elif cur is not None:
            items.append(cur)
            cur = None
    if cur is not None:
        items.append(cur)
    return items
