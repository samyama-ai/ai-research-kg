"""Estimate the AI Research KG size from the ai_research catalog.

Parses every problem page under <ai_research>/topics/*/*.md and counts the
nodes and edges the schema in docs/schema.md would produce. It is an
estimate only: no data is loaded. Written for Phase 1 (scope) on 2026-10-05.

Usage:
    python etl/count_kg.py /path/to/ai_research
"""
import collections
import glob
import json
import os
import re
import sys

root = sys.argv[1]
files = [f for f in glob.glob(f"{root}/topics/*/*.md") if not f.endswith("README.md")]
C = collections.Counter
status, prov, roles, venues_c = C(), C(), C(), C()
topics=set(); papers={}; persons=set(); venues=set(); assumptions=0; fut=0
e = C(); per_problem_refs=[]; no_refs=0; labs_text=[]
ref_re = re.compile(r"^- \*\*\[([^\]]+)\]\*\*\s*(.+?)\s*\*(.+?)\*\s*(.*)$")
def norm(t): return re.sub(r"[^a-z0-9]+"," ",t.lower()).strip()
for f in files:
    s=open(f,encoding="utf-8").read()
    fm = s.split("---")[1] if s.startswith("---") else ""
    m=re.search(r"^status:\s*(\S+)",fm,re.M); status[m.group(1) if m else "MISSING"]+=1
    m=re.search(r"^provenance:\s*(\S+)",fm,re.M); prov[m.group(1) if m else "MISSING"]+=1
    topics.add(os.path.basename(os.path.dirname(f))); e["IN_TOPIC"]+=1
    sec = {}
    for m in re.finditer(r"^## (\d+)\.[^\n]*\n(.*?)(?=^## |\Z)", s, re.M|re.S): sec[m.group(1)]=m.group(2)
    # references
    n=0; seen=set()
    for line in sec.get("9","").splitlines():
        m=ref_re.match(line.strip())
        if not m: continue
        role,auth,title,rest=m.groups(); k=norm(title)
        if k in seen: continue
        seen.add(k); n+=1; roles[role]+=1
        if k not in papers:
            vm=re.match(r"\s*([^,—]*?),?\s*((?:19|20)\d\d)",rest)
            venue=(vm.group(1).strip().rstrip(".") if vm else "")
            papers[k]=dict(auth=auth, venue=venue)
    e["CITES"]+=n; per_problem_refs.append(n); no_refs+= (n==0)
    # assumptions (numbered/bulleted list after "Assumptions" in section 2)
    s2=sec.get("2","")
    m=re.search(r"Assumptions.*?\n(.*)",s2,re.S|re.I)
    if m:
        a=len(re.findall(r"^\s*(?:\d+\.|-)\s+\S",m.group(1),re.M)); assumptions+=a; e["RESTS_ON"]+=a
    if sec.get("8","").strip(): fut+=1; e["HAS_NEXT_EXPERIMENT"]+=1
    labs_text.append(sec.get("7",""))
# authors / venues
for k,p in papers.items():
    a=re.sub(r",?\s*et al\.?","",p["auth"]).rstrip(". ")
    names=[x.strip() for x in re.split(r",| & | and ",a) if x.strip()]
    for nm in names: persons.add(nm.lower())
    e["AUTHORED_BY"]+=len(names)
    if p["venue"]: venues.add(p["venue"].lower()); e["APPEARED_AT"]+=1
etal=sum(1 for p in papers.values() if "et al" in p["auth"])
LABS=["Anthropic","OpenAI","Google DeepMind","DeepMind","Google","Meta","FAIR","Microsoft","Apple","NVIDIA","Allen Institute","AI2","EleutherAI","Hugging Face","Mistral","DeepSeek","Alibaba","Qwen","Redwood","Apollo","METR","MIRI","Stanford","Berkeley","MIT","CMU","Carnegie Mellon","Princeton","Oxford","Cambridge","ETH","Mila","Toronto","Tsinghua","Peking","NYU","Harvard","UW","Cohere","xAI","Together","Databricks","MosaicML","IBM","Amazon","Samsung","Baidu","ByteDance","Tencent","Salesforce","Character.AI","UK AISI","US AISI","Epoch"]
labs=C()
for t in labs_text:
    for L in LABS:
        if re.search(r"\b"+re.escape(L)+r"\b",t): labs[L]+=1
print(json.dumps(dict(problems=len(files),topics=len(topics),status=status,provenance=prov,
 papers=len(papers),papers_with_et_al=etal,persons_listed=len(persons),venues=len(venues),
 assumptions=assumptions,future_experiments=fut,ref_roles=roles.most_common(),
 refs_per_problem=dict(min=min(per_problem_refs),max=max(per_problem_refs),avg=round(sum(per_problem_refs)/len(per_problem_refs),1)),
 problems_without_refs=no_refs, labs_mentioned=len(labs), lab_problem_links=sum(labs.values()), top_labs=labs.most_common(8), edges=e),indent=1))
