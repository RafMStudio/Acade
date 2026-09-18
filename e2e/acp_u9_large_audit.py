#!/usr/bin/env python3
import csv,io,json,os,random,urllib.request,gc,re,statistics as st
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM,AutoModelForCausalLM

SEED=83
random.seed(SEED);torch.manual_seed(SEED)
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MT="facebook/nllb-200-distilled-600M"
MODELS=[
("Qwen3","Qwen/Qwen3-0.6B",64),
("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct",64),
("Llama3.2","unsloth/Llama-3.2-1B-Instruct",32),
("Gemma3","unsloth/gemma-3-1b-it",32)
]
def load():
 raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace")
 z=list(csv.DictReader(io.StringIO(raw)));random.Random(SEED).shuffle(z);return z[:140]
def ar_prompt(r):
 z=["السؤال: "+r["Question"]]
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:z.append(f"{L}) {v}")
 z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
 return "\n".join(z)
def en_prompt(r):
 z=["Q:"+r["_qen"]]
 for L in "ABCDEF":
  v=r.get("_"+L,"")
  if v:z.append(f"{L}:{v}")
 z+=["Answer:"]
 return "\n".join(z)
def translate(rs):
 tok=AutoTokenizer.from_pretrained(MT,src_lang="arb_Arab")
 m=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True);m.eval()
 seg=[];slots=[]
 for i,r in enumerate(rs):
  seg.append(r["Question"]);slots.append((i,"_qen"))
  for L in "ABCDEF":
   v=(r.get("Option "+L) or "").strip()
   if v:seg.append(v);slots.append((i,"_"+L))
 bos=tok.convert_tokens_to_ids("eng_Latn")
 for i in range(0,len(seg),12):
  x=tok(seg[i:i+12],return_tensors="pt",padding=True,truncation=True,max_length=256)
  with torch.no_grad():g=m.generate(**x,forced_bos_token_id=bos,max_new_tokens=200,num_beams=1)
  for j,v in enumerate(tok.batch_decode(g,skip_special_tokens=True)):
   ri,k=slots[i+j];rs[ri][k]=v.strip()
 del m,tok;gc.collect()
def chatids(tok,t):
 try:return tok.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True)
 except:return tok(t,add_special_tokens=False)["input_ids"]
def cc(tok,t):return len(chatids(tok,t))
def choose(tok,r):
 a=ar_prompt(r);e=en_prompt(r)
 return (e if cc(tok,e)<=.95*cc(tok,a) else a),a,e
def choice(model,tok,p,labels):
 ids=torch.tensor([chatids(tok,p)],dtype=torch.long)
 with torch.no_grad():z=model(input_ids=ids,use_cache=False).logits[0,-1].float()
 sc={}
 for L in labels:
  vals=[]
  for s in (L," "+L):
   ii=tok(s,add_special_tokens=False)["input_ids"]
   if len(ii)==1: vals.append(float(z[ii[0]]))
  if not vals:
   ii=tok(L,add_special_tokens=False)["input_ids"];vals=[float(z[ii[0]])]
  sc[L]=max(vals)
 return max(sc,key=sc.get)
def bootstrap(flags, n=4000):
 rng=random.Random(SEED+1);N=len(flags);vals=[]
 for _ in range(n):
  vals.append(sum(flags[rng.randrange(N)] for i in range(N))/N)
 vals.sort();return [vals[int(.025*n)],vals[int(.975*n)-1]]
def bootstrap_delta(base,new,n=4000):
 rng=random.Random(SEED+2);N=len(base);vals=[]
 for _ in range(n):
  idx=[rng.randrange(N) for i in range(N)]
  vals.append(sum(new[i] for i in idx)/N-sum(base[i] for i in idx)/N)
 vals.sort();return [vals[int(.025*n)],vals[int(.975*n)-1]]
rs=load();translate(rs)
out={"version":"ACP-U9 larger behavior audit","n_translated":len(rs),"models":{}}
for name,mid,n in MODELS:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
  model=AutoModelForCausalLM.from_pretrained(mid,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);model.eval()
  agreed=[];bc=[];nc=[];reds=[];translated=0;changes=[]
  for r in rs[:n]:
   g,a,e=choose(tok,r);translated+=g==e
   labels=[L for L in "ABCDEF" if (r.get("Option "+L) or "").strip()]
   x=choice(model,tok,a,labels);y=choice(model,tok,g,labels);gold=(r.get("Correct Answer") or "").strip().upper()[:1]
   agreed.append(int(x==y));bc.append(int(x==gold));nc.append(int(y==gold));reds.append((cc(tok,a)-cc(tok,g))/cc(tok,a))
   if x!=y:changes.append({"q":r.get("Question Number"),"base":x,"new":y,"gold":gold,"reduction_pct":100*reds[-1]})
  out["models"][name]={
   "model_id":mid,"n":n,"translated_cases":translated,
   "agreement":sum(agreed)/n,"agreement_ci95":bootstrap(agreed),
   "baseline_accuracy":sum(bc)/n,"compressed_accuracy":sum(nc)/n,
   "accuracy_delta":sum(nc)/n-sum(bc)/n,"accuracy_delta_ci95":bootstrap_delta(bc,nc),
   "mean_chat_reduction_pct":100*sum(reds)/n,
   "median_chat_reduction_pct":100*st.median(reds),
   "p10_chat_reduction_pct":100*sorted(reds)[max(0,int(.1*n)-1)],
   "p90_chat_reduction_pct":100*sorted(reds)[min(n-1,int(.9*n))],
   "changed_count":len(changes),"changes":changes
  }
  del model;gc.collect()
 except Exception as e:out["models"][name]={"model_id":mid,"error":repr(e)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u9_large_audit.json","w",encoding="utf8").write(json.dumps(out,ensure_ascii=False,indent=2))
print("ACP_U9_LARGE="+json.dumps(out,ensure_ascii=False),flush=True)
