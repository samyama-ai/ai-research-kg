"""Parse the ai_research catalog into nodes and edges.

Everything comes from the catalog itself (data/ai_research at a pinned commit):
no external lookups, no LLM extraction. What each label is built from:

    Topic           TAXONOMY.md table
    Problem         one topics/NN-*/<slug>.md file: frontmatter + "Problem Statement"
    Paper           "Key References" lines, deduplicated by arXiv id, then by title
    Person          author lists in "Key References" (no merging of name forms)
    Venue           the venue text of each reference, normalised
    Assumption      the "Assumptions" list in "Formal Setting"
    OpenQuestion    classified items in "What Is Not Known"
    Obstruction     "Why It Is Hard", mapped to the catalog's own 5 obstruction types
    FutureDirection "Concrete Next Experiment"
    Institution     labs named in "Current Research", matched against a fixed alias list
    DataSource      the catalog itself

RELATED_TO is computed from shared cited papers and says so on the edge.

Sections are found by their heading text, not their number: one file has
sections 9 and 10 swapped.
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from etl.helpers import short_hash, slug

REPO_WEB = "https://github.com/samyama-ai/ai_research"
SOURCE = "ai_research"


# --------------------------------------------------------------------------- #
# Graph container
# --------------------------------------------------------------------------- #
@dataclass
class Graph:
    nodes: dict[str, dict[str, dict]] = field(default_factory=lambda: defaultdict(dict))
    edges: list[tuple] = field(default_factory=list)
    _edge_keys: set = field(default_factory=set)

    def add_node(self, label: str, node_id: str, **props) -> str:
        existing = self.nodes[label].get(node_id)
        if existing is None:
            self.nodes[label][node_id] = {"id": node_id, **props}
        else:  # keep first value, fill gaps
            for k, v in props.items():
                if existing.get(k) in (None, "") and v not in (None, ""):
                    existing[k] = v
        return node_id

    def add_edge(self, src_label, src_id, rel, tgt_label, tgt_id, props=None, dedupe=True):
        key = (src_label, src_id, rel, tgt_label, tgt_id)
        if dedupe and key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append((src_label, src_id, rel, tgt_label, tgt_id, props or None))

    def counts(self) -> tuple[dict[str, int], dict[str, int]]:
        n = {label: len(v) for label, v in sorted(self.nodes.items())}
        e = dict(sorted(Counter(e[2] for e in self.edges).items()))
        return n, e

    def to_json(self) -> dict:
        return {"nodes": {k: list(v.values()) for k, v in self.nodes.items()},
                "edges": [list(e) for e in self.edges]}


# --------------------------------------------------------------------------- #
# Small text helpers
# --------------------------------------------------------------------------- #
def _strip_md(text: str) -> str:
    text = re.sub(r"\*\*|__|`", "", text)
    text = re.sub(r"(?<!\*)\*(?!\*)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _first_paragraphs(text: str, limit: int = 1200) -> str:
    out = []
    for para in re.split(r"\n\s*\n", text.strip()):
        para = _strip_md(para)
        if not para:
            continue
        out.append(para)
        if sum(len(p) for p in out) >= 300:
            break
    joined = " ".join(out)
    return joined[:limit].rstrip() + ("…" if len(joined) > limit else "")


def _norm_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


SECTION_KEYS = {
    "problem statement": "statement",
    "formal setting": "formal",
    "state of the art": "sota",
    "what is known": "known",
    "what is not known": "not_known",
    "why it is hard": "hard",
    "current research": "current",
    "concrete next experiment": "next",
    "key references": "refs",
    "worked example": "example",
}


def split_sections(text: str) -> dict[str, str]:
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


# --------------------------------------------------------------------------- #
# References
# --------------------------------------------------------------------------- #
REF_RE = re.compile(r"^\s*[-*]\s+\*\*\[([^\]]+)\]\*\*\s*(.*?)\s*\*([^*]+)\*\s*(.*)$")
ARXIV_RE = re.compile(r"arXiv[:\s]*(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
DOI_RE = re.compile(r"\b(10\.\d{4,9}/[^\s,;)]+)")
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-3]\d)\b")

ROLE_RULES = [  # order matters: first match wins
    ("caution", r"caution|critiqu|negative|counter|contra|refut|limit|illusion|rebuttal|confound|fragil|barrier|impossib"),
    ("survey", r"survey|position|roadmap|sok|tutorial|programme|report"),
    ("sota", r"sota|state of the art"),
    ("foundational", r"foundational|background|^key|established|classical|precedent|origin"),
    ("method", r"method|mechanis|mitigation|defen[cs]e|tool|algorithm|architecture|recipe|fix|solver|kernel"),
    ("evidence", r"empirical|evidence|analysis|measure|replicat|result|ablation|diagnos|scaling|theory|bound|hardness"),
]


def role_bucket(tag: str) -> str:
    t = tag.lower().strip()
    for name, pat in ROLE_RULES:
        if re.search(pat, t):
            return name
    return "context"


VENUE_ALIASES = [  # (canonical, regex)
    ("NeurIPS", r"\bneurips\b|\bnips\b|neural information processing"),
    ("ICML", r"\bicml\b"), ("ICLR", r"\biclr\b"),
    ("EMNLP", r"\bemnlp\b"), ("NAACL", r"\bnaacl\b"), ("EACL", r"\beacl\b"),
    ("ACL", r"\bacl\b"), ("TACL", r"\btacl\b|transactions of the association for computational"),
    ("COLING", r"\bcoling\b"), ("COLM", r"\bcolm\b"),
    ("CVPR", r"\bcvpr\b"), ("ICCV", r"\biccv\b"), ("ECCV", r"\beccv\b"),
    ("AAAI", r"\baaai\b"), ("IJCAI", r"\bijcai\b"),
    ("TMLR", r"\btmlr\b|transactions on machine learning research"),
    ("JMLR", r"\bjmlr\b|journal of machine learning research"),
    ("COLT", r"\bcolt\b"), ("AISTATS", r"\baistats\b"), ("UAI", r"\buai\b"),
    ("KDD", r"\bkdd\b"), ("SIGMOD", r"\bsigmod\b"), ("VLDB", r"\bvldb\b|\bpvldb\b"),
    ("MLSys", r"\bmlsys\b"), ("OSDI", r"\bosdi\b"), ("SOSP", r"\bsosp\b"),
    ("ASPLOS", r"\basplos\b"), ("ISCA", r"\bisca\b"), ("SC", r"^sc\b|supercomputing"),
    ("Interspeech", r"interspeech"), ("ICASSP", r"\bicassp\b"),
    ("NSDI", r"\bnsdi\b"), ("FAST", r"usenix fast|^fast(?:\s*'?\d{2,4})?$"), ("USENIX ATC", r"usenix atc"),
    ("CACM", r"\bcacm\b|communications of the acm"),
    ("IJCV", r"\bijcv\b|international journal of computer vision"),
    ("TPAMI", r"\btpami\b|pattern analysis and machine intelligence"),
    ("CAV", r"\bcav\b"), ("USENIX Security", r"usenix security"),
    ("IEEE S&P", r"s&p|security and privacy"), ("CCS", r"\bccs\b"), ("STOC", r"\bstoc\b"), ("FOCS", r"\bfocs\b"), ("SODA", r"\bsoda\b"), ("CHI", r"\bchi\b"),
    ("CoRL", r"\bcorl\b"), ("ICRA", r"\bicra\b"), ("RSS", r"\brss\b"),
    ("FAccT", r"facct"), ("Nature", r"^nature\b"), ("Science", r"^science\b"),
    ("PNAS", r"\bpnas\b"), ("Transformer Circuits Thread", r"transformer circuits"),
    ("Distill", r"^distill\b"), ("arXiv", r"^arxiv|arxiv preprint|^preprint"),
]


PREPRINT_VENUES = {"arXiv", "OpenReview"}


def normalise_venue(raw: str) -> str | None:
    raw = raw.strip(" .,;:—–-/(")
    if not re.search(r"[A-Za-z]{2}", raw) or re.match(r"identifier omitted", raw, re.I):
        return None  # parser residue such as "(" is not a venue
    low = raw.lower()
    for canonical, pat in VENUE_ALIASES:
        if re.search(pat, low):
            return canonical
    raw = re.sub(r"\s*\((?:[^)]*)\)\s*$", "", raw).strip(" .,")
    raw = re.sub(r"\s+\d+(?:\s*\(\d+\))?$", "", raw).strip(" .,")  # "CACM 52" -> "CACM"
    return raw or None


INITIALS_RE = re.compile(r"^(?:[A-Z][a-z]?\.\s?-?)+$")


def split_authors(text: str) -> list[str]:
    text = re.sub(r"\([^)]*\)", "", text)            # "(Llama Team)", "(METR)" affiliations
    text = re.sub(r"\([^,]*|[^,(]*\)", lambda m: m.group(0).split("(")[0].replace(")", ""), text)
    text = re.sub(r",?\s*\bet al\.?", "", text).strip()
    text = text.replace(" and ", ", ").replace(" & ", ", ")
    parts = [p.strip() for p in text.split(",") if p.strip()]
    parts = [p if INITIALS_RE.match(p) else p.rstrip(".") for p in parts]
    names: list[str] = []
    for p in parts:
        if INITIALS_RE.match(p) and names:  # "Moerland, T." -> "T. Moerland"
            names[-1] = f"{p} {names[-1]}"
        else:
            names.append(p)
    return [n for n in names if 1 < len(n) <= 60 and not n.lower().startswith(("the ", "team"))]


COLLECTIVE_RE = re.compile(r"\b(Team|Institute|Lab|Labs|Group|Inc|Foundation|Consortium|Collaboration|Organization)\b|^(OpenAI|Anthropic|Google|Meta|DeepMind|DeepSeek-AI|AI @ Meta)$")


def name_form(name: str) -> str:
    if COLLECTIVE_RE.search(name):
        return "collective"
    tokens = name.split()
    if len(tokens) == 1:
        return "surname"
    if all(INITIALS_RE.match(t) for t in tokens[:-1]):
        return "initials"
    return "full"


def parse_reference(line: str) -> dict | None:
    m = REF_RE.match(line)
    if not m:
        return None
    tag, authors, title, rest = m.groups()
    title = title.strip().rstrip(".")
    arxiv = ARXIV_RE.search(rest)
    doi = DOI_RE.search(rest)
    years = YEAR_RE.findall(rest)
    venue_part = re.split(r"—|\s-\s|arXiv[:\s]", rest)[0]
    venue_part = YEAR_RE.sub("", venue_part)
    return {
        "role_raw": tag.strip(),
        "role": role_bucket(tag),
        "authors_raw": authors.strip().rstrip("."),
        "authors": split_authors(authors),
        "title": title,
        "arxiv_id": arxiv.group(1) if arxiv else None,
        "doi": doi.group(1).rstrip(".") if doi else None,
        "year": int(years[0]) if years else None,
        "venue": normalise_venue(venue_part),
        "venue_raw": venue_part.strip(" .,;") or None,
    }


# --------------------------------------------------------------------------- #
# Section classifiers
# --------------------------------------------------------------------------- #
OBSTRUCTIONS = {  # the five named in the catalog's TEMPLATE.md §6
    "compute_cost": ("Compute cost", r"comput\w* cost|\bcompute\b|expensive|\bcost\b|flop|exponential|factorial|budget"),
    "confounded_measurement": ("Confounded measurement", r"confound"),
    "absent_ground_truth": ("Absent ground truth", r"ground[- ]truth"),
    "non_identifiability": ("Non-identifiability", r"identifiab"),
    "invalid_evaluation": ("Evaluation does not measure what it names",
                           r"does not measure|measure what it names|measures? the (?:wrong|thing)|invalid evaluation|evaluation (?:that )?does"),
}


def classify_obstructions(section: str) -> tuple[list[str], str]:
    bold = re.findall(r"\*\*([^*\n]{3,200})\*\*", section)
    head = bold[0] if bold else ""
    for text in (head, _first_paragraphs(section, 600)):
        found = [k for k, (_, pat) in OBSTRUCTIONS.items() if re.search(pat, text, re.I)]
        if found:
            return found, _strip_md(head)[:200]
    return ["other"], _strip_md(head)[:200]


def classify_gap(head: str) -> str:
    h = head.lower()
    if "theoretic" in h:
        return "theoretically_open"
    if "empiric" in h:
        return "empirically_open"
    if "method" in h:
        return "methodologically_blocked"
    return "unclassified"


VIOLATED_RE = re.compile(r"\bviolated\b|\bfails?\b|does not hold|broken|(?:—|–|:)\s*false\b(?!\s+(?:positives?|alarms?|discover))|(?:^|[.;]\s+)false\b|\bfalse in practice", re.I)
PARTLY_RE = re.compile(r"\bpartly\b|\bpartially\b|approximately|weakly|sometimes|mostly", re.I)
HOLDS_RE = re.compile(r"\bholds\b|\breasonable\b|\bsafe\b", re.I)


MIXED_RE = re.compile(r"\btrue (?:for|when|in|under)\b", re.I)   # "true for X ...; false for Y"


def assumption_status(text: str) -> str:
    if (PARTLY_RE.search(text) or MIXED_RE.search(text)) and VIOLATED_RE.search(text):
        return "partly"
    if VIOLATED_RE.search(text):
        return "violated"
    if HOLDS_RE.search(text):
        return "holds"
    return "unstated"


# a heading, not emphasis: bold that starts with "Assumption(s)" and ends with ":" or "." (inside
# or right after the bold). It may sit mid-paragraph, as it does on many pages
ASSUMPTION_HEAD_RE = re.compile(
    r"\*\*(?:(?:further|other|key|the)\s+)?assumptions?\b[^*\n]{0,80}?(?:[:.]\*\*|\*\*[:.])", re.I)
INLINE_ENUM_RE = re.compile(r"(?:^|\s)\((?:i{1,3}|iv|vi{0,3}|ix|x|\d{1,2}|[a-h])\)\s+")
PROSE_ITEM_RE = re.compile(r"(?<=[.;])\s+(?=[A-Z$*][^.:;]{2,100}:\s*\*)")


def _assumption(item: str) -> dict:
    nm = re.match(r"\*([^*]{2,120}?)[:.]\*\s*[:.]?\s*(.*)", item) or \
        re.match(r"\*\*([^*]{2,120}?)[:.]?\*\*\s*[:.]?\s*(.*)", item) or \
        re.match(r"([^:—]{2,100}?)\s*(?::|—|–| - )\s*(.*)", item)
    name = _strip_md(nm.group(1)) if nm else " ".join(_strip_md(item).split()[:8])
    text = _strip_md(item)
    return {"name": name[:160], "text": text[:1200], "violated": assumption_status(text)}


def _first_block(text: str) -> str:
    """The list or table directly under a heading: up to the first blank line that is not
    followed by another list item, table row or indented continuation."""
    lines = text.lstrip("\n").splitlines()
    out = []
    for i, line in enumerate(lines):
        if not line.strip():
            nxt = next((l for l in lines[i + 1:] if l.strip()), "")
            if not re.match(r"\s*(?:-|\*|\d+\.|\|)\s*\S", nxt):
                break
        out.append(line)
    return "\n".join(out)


def parse_assumptions(formal: str) -> list[dict]:
    """The "Assumptions" part of Formal Setting, in the four forms the catalog uses:
    a list under the heading, a table under it, an inline (i)/(ii) list on the
    heading line, or prose items "Name: *status* — why."."""
    m = ASSUMPTION_HEAD_RE.search(formal)
    if not m:
        return []
    line_end = formal.find("\n", m.end())
    inline = formal[m.end(): line_end if line_end != -1 else None].strip()
    below = _first_block(formal[line_end:] if line_end != -1 else "")
    if inline and INLINE_ENUM_RE.search(inline):
        items = [p.strip() for p in INLINE_ENUM_RE.split(inline)[1:] if p.strip()]
    elif below.startswith("|"):
        rows = [r for r in below.splitlines() if r.startswith("|")][2:]
        items = [" — ".join(c.strip() for c in r.strip("|").split("|")) for r in rows]
    elif re.match(r"(?:-|\*|\d+\.)\s+\S", below):
        items = list_items(below)          # text on the heading line is then an introduction
    elif inline:
        items = [p.strip() for p in PROSE_ITEM_RE.split(inline) if p.strip()]
    else:
        items = []
    return [_assumption(i) for i in items if len(_strip_md(i)) > 3]


def parse_gaps(not_known: str) -> list[dict]:
    out = []
    for item in list_items(not_known):
        m = re.match(r"\*\*([^*]{3,120})\*\*\s*[:.]?\s*(.*)", item)
        if not m:
            continue
        head = m.group(1).strip().rstrip(".:")
        out.append({"kind": classify_gap(head), "kind_raw": head[:120],
                    "is_primary": bool(re.search(r"primary|core", head, re.I)),
                    "text": _strip_md(m.group(2))[:1200]})
    return out


EXP_FIELDS = {
    "question": r"question",
    "scale": r"scale",
    "control_arm": r"control|arms?\b",
    "deciding_number": r"deciding|decid",
}
BUDGET_RE = re.compile(
    r"(~|≈|about\s+)?(\d[\d,]*(?:\.\d+)?)\s*(k)?\s*(?:[AH]\d{2,3}|GPU|TPU[\w-]*|accelerator)?[\s-]*(?:GPU[\s-]*)?hours?",
    re.I)
SINGLE_MACHINE_RE = re.compile(
    r"single (?:GPU|node|machine|A100|H100|workstation)|one (?:GPU|node|machine|A100|H100)|\blaptop\b|\bCPU[- ]only\b|8\s*[×x]\s*[AH]100",
    re.I)


def parse_experiment(section: str) -> dict:
    out: dict = {"text": _first_paragraphs(section, 1500)}
    blocks = re.split(r"(?m)^(?=(?:[-*]\s+)?\*\*[^*\n]{2,60}\*\*)", section)
    for block in blocks:
        m = re.match(r"(?:[-*]\s+)?\*\*([^*\n]{2,60}?)[:.]?\*\*[:.]?\s*(.*)", block, re.S)
        if not m:
            continue
        label = re.sub(r"^the\s+", "", m.group(1).strip().lower())
        for key, pat in EXP_FIELDS.items():
            if key not in out and re.match(pat, label):
                out[key] = _strip_md(m.group(2))[:1200]
                break
    hours = []
    for bm in BUDGET_RE.finditer(section):
        try:
            value = float(bm.group(2).replace(",", ""))
        except ValueError:
            continue
        if bm.group(3):
            value *= 1000
        if "hour" in bm.group(0).lower() and re.search(r"GPU|[AH]\d{2,3}|TPU|accelerator", bm.group(0), re.I):
            hours.append(value)
    out["compute_budget_gpu_hours"] = max(hours) if hours else None
    single = bool(SINGLE_MACHINE_RE.search(section))
    if out["compute_budget_gpu_hours"] is not None and out["compute_budget_gpu_hours"] <= 192:
        single = True
    out["single_machine"] = single if (single or out["compute_budget_gpu_hours"] is not None) else None
    return out


INSTITUTIONS = [  # (id, display name, kind, regex) -- checked against "Current Research"
    ("google_deepmind", "Google DeepMind", "industry", r"Google DeepMind|\bDeepMind\b|\bGDM\b"),
    ("google_research", "Google Research", "industry", r"Google Research|Google Brain|\bGoogle\b(?! DeepMind)"),
    ("anthropic", "Anthropic", "industry", r"\bAnthropic\b"),
    ("openai", "OpenAI", "industry", r"\bOpenAI\b"),
    ("meta", "Meta AI (FAIR)", "industry", r"\bMeta(?: AI| FAIR)?\b(?!-)|\bFAIR\b"),
    ("microsoft", "Microsoft Research", "industry", r"\bMicrosoft\b|\bMSR\b"),
    ("apple", "Apple", "industry", r"\bApple\b"),
    ("nvidia", "NVIDIA", "industry", r"\bNVIDIA\b|\bNvidia\b"),
    ("amazon", "Amazon", "industry", r"\bAmazon\b|\bAWS\b"),
    ("ibm", "IBM Research", "industry", r"\bIBM\b"),
    ("deepseek", "DeepSeek", "industry", r"\bDeepSeek\b"),
    ("alibaba", "Alibaba (Qwen)", "industry", r"\bAlibaba\b|\bQwen\b"),
    ("bytedance", "ByteDance", "industry", r"\bByteDance\b"),
    ("tencent", "Tencent", "industry", r"\bTencent\b"),
    ("baidu", "Baidu", "industry", r"\bBaidu\b"),
    ("mistral", "Mistral AI", "industry", r"\bMistral\b"),
    ("cohere", "Cohere", "industry", r"\bCohere\b"),
    ("xai", "xAI", "industry", r"\bxAI\b"),
    ("huggingface", "Hugging Face", "industry", r"Hugging ?Face"),
    ("together", "Together AI", "industry", r"Together AI"),
    ("databricks", "Databricks (MosaicML)", "industry", r"\bDatabricks\b|\bMosaicML\b"),
    ("ai2", "Allen Institute for AI", "non-profit", r"\bAI2\b|\bAi2\b|Allen Institute|AllenAI"),
    ("eleutherai", "EleutherAI", "non-profit", r"\bEleutherAI\b|\bEleuther\b"),
    ("redwood", "Redwood Research", "non-profit", r"\bRedwood\b"),
    ("apollo", "Apollo Research", "non-profit", r"\bApollo Research\b"),
    ("metr", "METR", "non-profit", r"\bMETR\b"),
    ("miri", "MIRI", "non-profit", r"\bMIRI\b"),
    ("epoch", "Epoch AI", "non-profit", r"\bEpoch AI\b"),
    ("uk_aisi", "UK AI Security Institute", "government", r"UK AISI|AI Security Institute|AI Safety Institute"),
    ("stanford", "Stanford University", "academic", r"\bStanford\b"),
    ("berkeley", "UC Berkeley", "academic", r"\bBerkeley\b|\bBAIR\b"),
    ("mit", "MIT", "academic", r"\bMIT\b"),
    ("cmu", "Carnegie Mellon University", "academic", r"\bCMU\b|Carnegie Mellon"),
    ("princeton", "Princeton University", "academic", r"\bPrinceton\b"),
    ("harvard", "Harvard University", "academic", r"\bHarvard\b"),
    ("oxford", "University of Oxford", "academic", r"\bOxford\b"),
    ("cambridge", "University of Cambridge", "academic", r"\bCambridge\b"),
    ("eth", "ETH Zurich", "academic", r"\bETH\b"),
    ("epfl", "EPFL", "academic", r"\bEPFL\b"),
    ("mila", "Mila", "academic", r"\bMila\b"),
    ("toronto", "University of Toronto / Vector", "academic", r"\bToronto\b|Vector Institute"),
    ("uw", "University of Washington", "academic", r"University of Washington|\bUW\b"),
    ("nyu", "NYU", "academic", r"\bNYU\b"),
    ("cornell", "Cornell University", "academic", r"\bCornell\b"),
    ("columbia", "Columbia University", "academic", r"\bColumbia\b"),
    ("tsinghua", "Tsinghua University", "academic", r"\bTsinghua\b"),
    ("pku", "Peking University", "academic", r"\bPeking\b|\bPKU\b"),
    ("kaist", "KAIST", "academic", r"\bKAIST\b"),
    ("tum", "TU Munich", "academic", r"\bTUM\b|TU Munich"),
    ("edinburgh", "University of Edinburgh", "academic", r"\bEdinburgh\b"),
    ("ucl", "UCL", "academic", r"\bUCL\b"),
]


def parse_current_research(section: str) -> list[dict]:
    out = []
    for item in list_items(section):
        m = re.match(r"\*\*([^*]{2,150})\*\*", item)
        direction = _strip_md(m.group(1)).rstrip(".:") if m else " ".join(_strip_md(item).split()[:10])
        labs = [iid for iid, _, _, pat in INSTITUTIONS if re.search(pat, item)]
        out.append({"direction": direction[:200], "labs": labs})
    return out


# --------------------------------------------------------------------------- #
# Catalog walk
# --------------------------------------------------------------------------- #
def parse_taxonomy(root: Path) -> list[dict]:
    topics = []
    for line in (root / "TAXONOMY.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(\d{2})\s*\|\s*([^|]+?)\s*\|\s*\[`([^`]+)`\][^|]*\|\s*([^|]*?)\s*\|\s*$", line)
        if m:
            topics.append({"number": int(m.group(1)), "name": m.group(2).strip(),
                           "slug": m.group(3).strip(), "scope": m.group(4).strip()})
    return topics


def problem_files(root: Path) -> list[Path]:
    return sorted(p for p in (root / "topics").glob("*/*.md") if p.name != "README.md")


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                              check=True, timeout=30).stdout.strip()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError):
        return ""


def catalog_dates(root: Path, commit: str) -> tuple[str, str]:
    """(retrieved_at, source_date), both YYYY-MM-DD. retrieved_at is when the pinned commit was
    checked out here (git's reflog for HEAD), source_date the commit's own date. A checkout
    without git (the test fixture) gives 'unknown' for both."""
    source_date = _git(root, "log", "-1", "--format=%cs", commit) or "unknown"
    m = re.search(r"@\{(\d{4}-\d{2}-\d{2})\}", _git(root, "log", "-g", "-1", "--date=short", "--format=%gd", "HEAD"))
    return (m.group(1) if m else "unknown"), source_date


def build_graph(root: Path, commit: str, related_top_k: int = 5, related_min_shared: int = 2) -> Graph:
    g = Graph()
    base_url = f"{REPO_WEB}/blob/{commit}"
    # provenance dates: when the pinned catalog was fetched, and the date of that version
    retrieved_at, source_date = catalog_dates(root, commit)
    common = {"provenance": "real", "source": SOURCE, "retrieved_at": retrieved_at, "source_date": source_date}

    g.add_node("DataSource", "datasource:ai_research", name="ai_research catalog",
               url=REPO_WEB, version=commit, licence="none stated (see docs/standards.md)", **common)

    topic_ids = {}
    for t in parse_taxonomy(root):
        tid = f"topic:{t['slug']}"
        topic_ids[t["slug"]] = tid
        g.add_node("Topic", tid, name=t["name"], slug=t["slug"], number=t["number"],
                   scope=t["scope"], source_url=f"{base_url}/TAXONOMY.md", method="parsed", **common)

    # first pass: references, so papers can be deduplicated across problems
    raw_refs: dict[str, list[dict]] = {}
    texts: dict[Path, str] = {}
    for path in problem_files(root):
        text = path.read_text(encoding="utf-8")
        texts[path] = text
        refs_block = split_sections(text).get("refs", "")
        raw_refs[str(path)] = [r for r in (parse_reference(l) for l in refs_block.splitlines()) if r]

    title_to_arxiv: dict[str, str] = {}
    for refs in raw_refs.values():
        for r in refs:
            if r["arxiv_id"]:
                title_to_arxiv.setdefault(_norm_title(r["title"]), r["arxiv_id"])

    def paper_id(r: dict) -> str:
        ax = r["arxiv_id"] or title_to_arxiv.get(_norm_title(r["title"]))
        if ax:
            return f"paper:arxiv:{ax}"
        if r["doi"]:
            return f"paper:doi:{r['doi'].lower()}"
        return f"paper:t:{short_hash(_norm_title(r['title']))}"

    # one venue per paper, chosen over all its citations: a named venue beats a
    # preprint server, then the most frequent, then the first seen
    seen_venues: dict[str, list[str]] = defaultdict(list)
    venue_raw_of: dict[tuple[str, str], str | None] = {}
    for refs in raw_refs.values():
        for r in refs:
            if r["venue"]:
                seen_venues[paper_id(r)].append(r["venue"])
                venue_raw_of.setdefault((paper_id(r), r["venue"]), r["venue_raw"])
    paper_venue: dict[str, tuple[str, list[str]]] = {}
    for ppid, names in seen_venues.items():
        counts = Counter(names)
        ranked = sorted(dict.fromkeys(names), key=lambda v: (v in PREPRINT_VENUES, -counts[v]))
        paper_venue[ppid] = (ranked[0], [v for v in ranked[1:] if v not in PREPRINT_VENUES])

    problem_papers: dict[str, set[str]] = {}

    for path, text in texts.items():
        fm = parse_frontmatter(text)
        sec = split_sections(text)
        topic_slug = fm.get("topic") or path.parent.name
        pid = f"problem:{fm.get('id') or f'{topic_slug}/{path.stem}'}"
        src_url = f"{base_url}/{path.relative_to(root).as_posix()}"
        p_common = {**common, "source_url": src_url}

        g.add_node("Problem", pid, title=fm.get("title") or path.stem, slug=path.stem,
                   status=fm.get("status"), topic=topic_slug,
                   first_added=fm.get("first_added"), last_reviewed=fm.get("last_reviewed"),
                   last_substantive_update=fm.get("last_substantive_update"),
                   stale_since=fm.get("stale_since") or None,
                   catalog_provenance=fm.get("provenance"),
                   statement=_first_paragraphs(sec.get("statement", "")),
                   method="parsed", **p_common)
        g.add_edge("Problem", pid, "FROM_SOURCE", "DataSource", "datasource:ai_research")
        if topic_slug in topic_ids:
            g.add_edge("Problem", pid, "IN_TOPIC", "Topic", topic_ids[topic_slug])

        # references -> Paper, Person, Venue
        papers_here = set()
        for pos, r in enumerate(raw_refs[str(path)], start=1):
            ppid = paper_id(r)
            papers_here.add(ppid)
            venue, variants = paper_venue.get(ppid, (None, []))
            g.add_node("Paper", ppid, title=r["title"], year=r["year"], arxiv_id=r["arxiv_id"],
                       doi=r["doi"], venue=venue,
                       venue_raw=venue_raw_of.get((ppid, venue)) if venue else r["venue_raw"],
                       venue_variants="; ".join(variants) or None,
                       authors_raw=r["authors_raw"], method="parsed",
                       source_url=src_url, **common)
            g.add_edge("Problem", pid, "CITES", "Paper", ppid,
                       {"role": r["role"], "role_raw": r["role_raw"], "position": pos})
            for apos, name in enumerate(r["authors"], start=1):
                person = g.add_node("Person", f"person:{slug(name)}", name=name,
                                    name_form=name_form(name), method="parsed",
                                    source_url=src_url, **common)
                g.add_edge("Paper", ppid, "AUTHORED_BY", "Person", person, {"position": apos})
            if venue:
                vid = f"venue:{slug(venue)}"
                g.add_node("Venue", vid, name=venue, method="parsed",
                           source_url=src_url, **common)
                g.add_edge("Paper", ppid, "APPEARED_AT", "Venue", vid)
        problem_papers[pid] = papers_here

        # assumptions
        for i, a in enumerate(parse_assumptions(sec.get("formal", "")), start=1):
            aid = f"{pid}#assumption-{i}"
            g.add_node("Assumption", aid, name=a["name"], text=a["text"], violated=a["violated"],
                       method="parsed", **p_common)
            g.add_edge("Problem", pid, "RESTS_ON", "Assumption", aid, {"position": i})

        # open questions
        for i, q in enumerate(parse_gaps(sec.get("not_known", "")), start=1):
            qid = f"{pid}#gap-{i}"
            g.add_node("OpenQuestion", qid, kind=q["kind"], kind_raw=q["kind_raw"],
                       is_primary=q["is_primary"], text=q["text"], method="parsed", **p_common)
            g.add_edge("Problem", pid, "HAS_GAP", "OpenQuestion", qid, {"position": i})

        # obstructions
        found, detail = classify_obstructions(sec.get("hard", ""))
        for rank, key in enumerate(found):
            name = OBSTRUCTIONS[key][0] if key in OBSTRUCTIONS else "Other"
            g.add_node("Obstruction", f"obstruction:{key}", name=name,
                       method="keyword-classified", **common)
            g.add_edge("Problem", pid, "BLOCKED_BY", "Obstruction", f"obstruction:{key}",
                       {"detail": detail, "is_primary": rank == 0})

        # next experiment
        if sec.get("next", "").strip():
            e = parse_experiment(sec["next"])
            fid = f"{pid}#next-experiment"
            g.add_node("FutureDirection", fid, **e, method="parsed", **p_common)
            g.add_edge("Problem", pid, "HAS_NEXT_EXPERIMENT", "FutureDirection", fid)

        # labs active on the problem
        for d in parse_current_research(sec.get("current", "")):
            for lab in d["labs"]:
                iid, name, kind, _ = next(x for x in INSTITUTIONS if x[0] == lab)
                g.add_node("Institution", f"institution:{iid}", name=name, kind=kind,
                           method="name-matched", **common)
                g.add_edge("Institution", f"institution:{iid}", "ACTIVE_ON", "Problem", pid,
                           {"direction": d["direction"]})

    # RELATED_TO: computed from shared cited papers (Jaccard), top-k per problem
    by_paper: dict[str, set[str]] = defaultdict(set)
    for pid, papers in problem_papers.items():
        for pp in papers:
            by_paper[pp].add(pid)
    for pid, papers in problem_papers.items():
        shared = Counter()
        for pp in papers:
            for other in by_paper[pp]:
                if other != pid:
                    shared[other] += 1
        scored = []
        for other, n in shared.items():
            if n < related_min_shared:
                continue
            jac = n / len(papers | problem_papers[other])
            scored.append((jac, n, other))
        scored.sort(key=lambda x: (-x[0], -x[1], x[2]))
        for jac, n, other in scored[:related_top_k]:
            a, b = sorted((pid, other))
            g.add_edge("Problem", a, "RELATED_TO", "Problem", b,
                       {"method": "shared_papers", "shared_papers": n, "score": round(jac, 3)})
    return g


def main() -> None:
    from etl.download_data import CATALOG_DIR
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=CATALOG_DIR, check=True,
                            capture_output=True, text=True).stdout.strip()
    g = build_graph(CATALOG_DIR, commit)
    n, e = g.counts()
    out = CATALOG_DIR.parent / "graph.json"
    out.write_text(json.dumps(g.to_json(), ensure_ascii=False))
    print(f"[parse] {sum(n.values()):,} nodes, {sum(e.values()):,} edges -> {out}")
    for k, v in n.items():
        print(f"  node {k:16s} {v:6,}")
    for k, v in e.items():
        print(f"  edge {k:20s} {v:6,}")


if __name__ == "__main__":
    main()
