#!/usr/bin/env python3
import csv, io, json, os, re, random, time, urllib.request, gc, math
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM

SEED=59
random.seed(SEED); torch.manual_seed(SEED)
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
DICT_PATH=os.environ.get("ACP_DICT","e2e/acp_u8_dictionary.json")
ARWORD=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")

TOKENIZERS=[
("Qwen3","Qwen/Qwen3-0.6B"),
("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),
("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),
("Gemma3","unsloth/gemma-3-1b-it"),
("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),
("Phi4-mini","microsoft/Phi-4-mini-instruct"),
("Falcon3","tiiuae/Falcon3-1B-Instruct"),
("DeepSeek-R1-Distill","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
]
BEHAVIOR=[
("Qwen3","Qwen/Qwen3-0.6B",16),
("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct",16),
("Llama3.2","unsloth/Llama-3.2-1B-Instruct",16),
("Gemma3","unsloth/gemma-3-1b-it",16),
("DeepSeek-R1-Distill","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",12)
]

def loadrows():
    raw=urllib.request.urlopen(TEST_URL,timeout=120).read().decode("utf-8-sig","replace")
    return list(csv.DictReader(io.StringIO(raw)))

def prompt(r):
    z=["السؤال: "+r["Question"]]
    for L in "ABCDEF":
        v=(r.get("Option "+L) or "").strip()
        if v:z.append(f"{L}) {v}")
    z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
    return "\n".join(z)

d=json.load(open(DICT_PATH,encoding="utf-8"))
rules={tuple(x["ar"].split()):x["en"] for x in d["rules"]}

def tc(tok,t): return len(tok(t,add_special_tokens=False)["input_ids"])
def chatids(tok,t):
    msgs=[{"role":"user","content":t}]
    try:
        return tok.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True)
    except Exception:
        return tok(t,add_special_tokens=False)["input_ids"]
def cc(tok,t): return len(chatids(tok,t))

def ortho(t):
    t=DIAC.sub("",t).replace("ـ","")
    t=t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩","0123456789"))
    t=t.replace("،",",").replace("؛",";")
    t=re.sub(r"[ \t]+"," ",t)
    t=re.sub(r" +([,;:.!?])",r"\1",t)
    return t

def spans(t):
    ms=list(ARWORD.finditer(t)); w=[m.group(0) for m in ms]; out=[]
    maxn=6
    for i in range(len(w)):
        for n in range(maxn,0,-1):
            if i+n>len(w): continue
            k=tuple(w[i:i+n])
            if k in rules:
                out.append((ms[i].start(),ms[i+n-1].end(),rules[k],n))
    return out

def content_candidate(t,tok):
    raw=[]
    for s,e,new,nw in spans(t):
        a=max(0,s-48); b=min(len(t),e+48)
        sv=tc(tok,t[a:b])-tc(tok,t[a:s]+new+t[e:b])
        if sv>0: raw.append((s,e,new,sv,nw))
    raw.sort(key=lambda x:(-x[3],-x[4],x[0]))
    sel=[]
    for x in raw:
        if all(x[1]<=y[0] or x[0]>=y[1] for y in sel): sel.append(x)
    sel.sort()
    o=[];p=0
    for s,e,new,sv,nw in sel:o += [t[p:s],new];p=e
    o.append(t[p:])
    return ortho("".join(o)),len(sel)

def transform(t,tok):
    base_chat=cc(tok,t); base_content=tc(tok,t)
    c,k=content_candidate(t,tok)
    # only presentation-neutral formatting: whitespace/Arabic diacritics/digits; no wording deletion
    f=re.sub(r"(?m)^([A-F]\)) +",r"\1",c)
    candidates=[(t,0),(ortho(t),0),(c,k),(f,k)]
    best=min(candidates,key=lambda x:(cc(tok,x[0]),tc(tok,x[0])))
    if cc(tok,best[0])>base_chat:
        return t,base_content,base_content,base_chat,base_chat,0
    return best[0],base_content,tc(tok,best[0]),base_chat,cc(tok,best[0]),best[1]

def suffix_score(model,tok,prefix,suffix):
    pref=torch.tensor([chatids(tok,prefix)],dtype=torch.long)
    suffix_ids=tok(suffix,add_special_tokens=False)["input_ids"]
    if not suffix_ids:return -1e30
    total=0.0
    cur=pref
    with torch.no_grad():
        for tid in suffix_ids:
            z=model(input_ids=cur,use_cache=False).logits[0,-1].float()
            total += float(F.log_softmax(z,dim=-1)[tid])
            cur=torch.cat([cur,torch.tensor([[tid]],dtype=torch.long)],dim=1)
    return total

def choice(model,tok,text,labels):
    # score both bare and leading-space label forms; supports multi-token labels
    sc={}
    for L in labels:
        sc[L]=max(suffix_score(model,tok,text,L),suffix_score(model,tok,text," "+L))
    return max(sc,key=sc.get)

rows=loadrows()
res={"version":"ACP-U8.1 famous-model benchmark","dictionary":"frozen U8 dictionary learned from MedAraBench train split","tokenizers":{},"behavior":{}}

for name,mid in TOKENIZERS:
    try:
        tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
        B=T=CB=CT=rep=0
        for r in rows[:1200]:
            p=prompt(r);tr,b,n,cb,ct,k=transform(p,tok)
            B+=b;T+=n;CB+=cb;CT+=ct;rep+=k
        cr=100*(B-T)/B; chr=100*(CB-CT)/CB
        res["tokenizers"][name]={
            "model_id":mid,
            "content_reduction_pct":cr,
            "chat_reduction_pct":chr,
            "passes30_content":cr>=30,
            "passes30_chat":chr>=30,
            "no_regression":T<=B and CT<=CB,
            "replacements":rep
        }
    except Exception as e:
        res["tokenizers"][name]={"model_id":mid,"error":repr(e)}

sample=list(rows); random.Random(SEED).shuffle(sample)
for name,mid,ncase in BEHAVIOR:
    try:
        tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
        model=AutoModelForCausalLM.from_pretrained(mid,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True)
        model.eval()
        for p in model.parameters():p.requires_grad_(False)
        base=[];new=[];gold=[];B=T=CB=CT=0;changed=[]
        t0=time.perf_counter()
        for r in sample[:ncase]:
            p=prompt(r); tr,b,n,cb,ct,k=transform(p,tok)
            labels=[L for L in "ABCDEF" if (r.get("Option "+L) or "").strip()]
            a=choice(model,tok,p,labels); c=choice(model,tok,tr,labels); g=(r.get("Correct Answer") or "").strip().upper()[:1]
            base.append(a);new.append(c);gold.append(g);B+=b;T+=n;CB+=cb;CT+=ct
            if a!=c: changed.append({"q":r.get("Question Number"),"base":a,"new":c,"gold":g,"tokens":[b,n],"chat_tokens":[cb,ct]})
        agreement=sum(a==b for a,b in zip(base,new))/ncase
        bacc=sum(a==g for a,g in zip(base,gold))/ncase
        cacc=sum(a==g for a,g in zip(new,gold))/ncase
        res["behavior"][name]={
            "model_id":mid,"n":ncase,"agreement":agreement,
            "baseline_accuracy":bacc,"compressed_accuracy":cacc,"accuracy_delta":cacc-bacc,
            "content_reduction_pct":100*(B-T)/B,"chat_reduction_pct":100*(CB-CT)/CB,
            "changed_answers":changed,"seconds":time.perf_counter()-t0
        }
        del model;gc.collect()
    except Exception as e:
        res["behavior"][name]={"model_id":mid,"error":repr(e)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_famous_models_results.json","w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_FAMOUS="+json.dumps(res,ensure_ascii=False),flush=True)
