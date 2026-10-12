"""The fixed lists and patterns the parser classifies with.

Kept apart from the parsing code so that each list can be read, reviewed and
changed on its own: citation-role buckets, venue aliases, the catalog's five
obstruction types, the institution alias list, and the "Concrete Next
Experiment" field patterns. The code lists these feed are mirrored in
vocab/concepts.yaml and checked by etl/conformance.py.
"""
from __future__ import annotations

import re

# Section headings of a problem page -> short key. Matched by text, not number.
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

# Citation-role buckets for the free-text "[Tag]" on a reference. Order matters:
# the first match wins, so "SOTA / negative result" is a caution, not a sota.
# Every keyword is anchored at a word start (and at the word end where a stem would
# otherwise swallow unrelated words: "key" not "keyword", "fix" not "prefix",
# "bound" not "boundary", "limit" not "unlimited", "origin" not "original").
ROLE_RULES = [
    ("caution", r"\bcaution|\bcritiqu|\bnegative|\bcounter|\bcontra|\brefut|\blimit(?:s|ation)?\b|\billusion|\brebuttal|\bconfound|\bfragil|\bbarrier|\bimpossib"),
    ("survey", r"\bsurvey|\bposition|\broadmap|\bsok\b|\btutorial|\bprogramme|\breport"),
    ("sota", r"\bsota\b|\bstate[- ]of[- ]the[- ]art\b"),
    ("foundational", r"\bfoundational|\bbackground|^key\b|\bestablished|\bclassical|\bprecedent|\borigin\b|\boriginal\b"),
    ("method", r"\bmethod|\bmechanis|\bmitigation|\bdefen[cs]e|\btool|\balgorithm|\barchitecture|\brecipe|\bfix\b|\bsolver|\bkernel"),
    ("evidence", r"\bempirical|\bevidence|\banalysis|\bmeasure|\breplicat|\bresult|\bablation|\bdiagnos|\bscaling|\btheory|\bbound(?:s)?\b|\bhardness"),
]

# (canonical venue, regex on the lower-cased venue text)
VENUE_ALIASES = [
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
    ("CAV", r"\bcav\b"), ("USENIX Security", r"usenix security"),
    ("IEEE S&P", r"s&p|security and privacy"), ("CCS", r"\bccs\b"), ("STOC", r"\bstoc\b"),
    ("FOCS", r"\bfocs\b"), ("SODA", r"\bsoda\b"), ("CHI", r"\bchi\b"),
    ("CoRL", r"\bcorl\b"), ("ICRA", r"\bicra\b"), ("RSS", r"\brss\b"),
    ("FAccT", r"facct"),
    # journal families: the flagship title only, its sister journals keep their own names
    ("Nature Machine Intelligence", r"nature machine intelligence|\bnat\.? mach\.? intell"),
    ("Nature Communications", r"nature communications|\bnat\.? commun"),
    ("Science Advances", r"science advances|\bsci\.? adv\b"), ("Scientific Reports", r"scientific reports"),
    ("Nature", r"^nature(?:\s+\d+)?$"), ("Science", r"^science(?:\s+\d+)?$"),
    ("PNAS", r"\bpnas\b"), ("Transformer Circuits Thread", r"transformer circuits"),
    ("Distill", r"^distill\b"), ("arXiv", r"^arxiv|arxiv preprint|^preprint"),
]

# The five obstruction types the catalog's TEMPLATE.md names in "Why It Is Hard":
# code -> (display name, regex). Anything else becomes `other`.
OBSTRUCTIONS = {
    "compute_cost": ("Compute cost", r"\bcomput\w* cost|\bcompute\b|\bexpensive\b|\bcost(?:s|ly)?\b|\bflops?\b|\bexponential\b|\bfactorial\b|\bbudget\b"),
    "confounded_measurement": ("Confounded measurement", r"\bconfound"),
    "absent_ground_truth": ("Absent ground truth", r"\bground[- ]truth"),
    "non_identifiability": ("Non-identifiability", r"\bidentifiab"),
    "invalid_evaluation": ("Evaluation does not measure what it names",
                           r"does not measure|measure what it names|measures? the (?:wrong|thing)|invalid evaluation|evaluation (?:that )?does"),
}

# Author strings that name a group, not a person.
COLLECTIVE_RE = re.compile(
    r"\b(Team|Institute|Lab|Labs|Group|Inc|Foundation|Consortium|Collaboration|Organization)\b"
    r"|^(OpenAI|Anthropic|Google|Meta|DeepMind|DeepSeek-AI|AI @ Meta)$")

# "Concrete Next Experiment": bold field label -> regex on the label.
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
# A budget at or under 8 GPUs x 24 h counts as "fits on one machine".
SINGLE_MACHINE_GPU_HOURS = 192

# (id, display name, kind, regex) checked against "Current Research", case-sensitively.
# Patterns exclude the known other meanings of a name: the MIT licence, FAIR data principles,
# Apple products, Cambridge University Press and Cambridge MA, British Columbia, model names
# (Mistral 7B, Qwen2.5) rather than the company. 52 names; MIRI never occurs at the pinned commit.
INSTITUTIONS = [
    ("google_deepmind", "Google DeepMind", "industry", r"Google DeepMind|\bDeepMind\b|\bGDM\b"),
    ("google_research", "Google Research", "industry", r"Google Research|Google Brain|\bGoogle\b(?! DeepMind)"),
    ("anthropic", "Anthropic", "industry", r"\bAnthropic\b"),
    ("openai", "OpenAI", "industry", r"\bOpenAI\b"),
    ("meta", "Meta AI (FAIR)", "industry", r"\bMeta(?: AI| FAIR)?\b(?!-)|\bFAIR\b(?!\s+(?:data|principles?))"),
    ("microsoft", "Microsoft Research", "industry", r"\bMicrosoft\b|\bMSR\b"),
    ("apple", "Apple", "industry", r"\bApple\b(?!\s+(?:Silicon|Watch|Vision|M\d))"),
    ("nvidia", "NVIDIA", "industry", r"\bNVIDIA\b|\bNvidia\b"),
    ("amazon", "Amazon", "industry", r"\bAmazon\b|\bAWS\b"),
    ("ibm", "IBM Research", "industry", r"\bIBM\b"),
    ("deepseek", "DeepSeek", "industry", r"\bDeepSeek\b"),
    ("alibaba", "Alibaba (Qwen)", "industry", r"\bAlibaba\b|\bQwen\b(?![-\d.])"),
    ("bytedance", "ByteDance", "industry", r"\bByteDance\b"),
    ("tencent", "Tencent", "industry", r"\bTencent\b"),
    ("baidu", "Baidu", "industry", r"\bBaidu\b"),
    ("mistral", "Mistral AI", "industry", r"\bMistral\b(?![- ]?(?:\d|7B|Large|Small|Nemo|Medium))"),
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
    ("uk_aisi", "UK AI Security Institute", "government", r"UK AISI|UK AI (?:Security|Safety) Institute|(?<!US )(?<!U\.S\. )AI (?:Security|Safety) Institute(?! \(US)"),
    ("us_aisi", "US AI Safety Institute (CAISI)", "government", r"US AISI|U\.?S\.? AI Safety Institute|\bCAISI\b"),
    ("stanford", "Stanford University", "academic", r"\bStanford\b"),
    ("berkeley", "UC Berkeley", "academic", r"\bBerkeley\b|\bBAIR\b"),
    ("mit", "MIT", "academic", r"\bMIT\b(?!\s+[Ll]icen[cs]e)"),
    ("cmu", "Carnegie Mellon University", "academic", r"\bCMU\b|Carnegie Mellon"),
    ("princeton", "Princeton University", "academic", r"\bPrinceton\b"),
    ("harvard", "Harvard University", "academic", r"\bHarvard\b"),
    ("oxford", "University of Oxford", "academic", r"\bOxford\b"),
    ("cambridge", "University of Cambridge", "academic", r"\bCambridge\b(?!,? ?MA\b)(?! University Press)"),
    ("eth", "ETH Zurich", "academic", r"\bETH\b"),
    ("epfl", "EPFL", "academic", r"\bEPFL\b"),
    ("mila", "Mila", "academic", r"\bMila\b"),
    ("toronto", "University of Toronto / Vector", "academic", r"\bToronto\b|Vector Institute"),
    ("uw", "University of Washington", "academic", r"University of Washington|\bUW\b"),
    ("nyu", "NYU", "academic", r"\bNYU\b"),
    ("cornell", "Cornell University", "academic", r"\bCornell\b"),
    ("columbia", "Columbia University", "academic", r"(?<!British )\bColumbia\b"),
    ("tsinghua", "Tsinghua University", "academic", r"\bTsinghua\b"),
    ("pku", "Peking University", "academic", r"\bPeking\b|\bPKU\b"),
    ("kaist", "KAIST", "academic", r"\bKAIST\b"),
    ("tum", "TU Munich", "academic", r"\bTUM\b|TU Munich"),
    ("edinburgh", "University of Edinburgh", "academic", r"\bEdinburgh\b"),
    ("ucl", "UCL", "academic", r"\bUCL\b"),
]
INSTITUTION_BY_ID = {entry[0]: entry for entry in INSTITUTIONS}
