#!/usr/bin/env python3
import csv, io, json, os, re, random, time, urllib.request, gc
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

SEED=47
random.seed(SEED);torch.manual_seed(SEED)
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
DICT_PATH=os.environ.get("ACP_DICT","e2e/acp_u8_dictionary.json")
ARWORD=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
TOKENIZERS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"mistralai/Mistral-7B-Instruct-v0.3",
"microsoft/Phi-3-mini-4k-instruct",
"tiiuae/Falcon3-1B-Instruct"
]
BEHAVIOR=[
("Qwen/Qwen2.5-0.5B-Instruct",24),
("HuggingFaceTB/SmolLM2-360M-Instruct",24),
("TinyLlama/TinyLlama-1.1B-Chat-v1.0",8)
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

def tc(tok,t):return len(tok(t,add_special_tokens=False)["input_ids"])
def chatids(tok,t):
 try:return tok.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True)
 except:return tok(t,add_special_tokens=False)["input_ids"]
def cc(tok,t):return len(chatids(tok,t))

def ortho(t):
 t=DIAC.sub("",t).replace("ـ","")
 t=t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩","0123456789"))
 t=t.replace("،",",").replace("؛",";")
 t=re.sub(r"[ \t]+"," ",t)
 t=re.sub(r" +([,;:.!?])",r"\1",t)
 return t

def spans(t):
 ms=list(ARWORD.finditer(t));w=[m.group(0) for m in ms];out=[]
 for i in range(len(w)):
  for n in (4,3,2,1):
   if i+n>len(w):continue
   k=tuple(w[i:i+n])
   if k in rules:out.append((ms[i].start(),ms[i+n-1].end(),rules[k],n))
 return out

def content_candidate(t,tok):
 base=tc(tok,t);raw=[]
 for s,e,new,nw in spans(t):
  a=max(0,s-40);b=min(len(t),e+40)
  sv=tc(tok,t[a:b])-tc(tok,t[a:s]+new+t[e:b])
  if sv>0:raw.append((s,e,new,sv,nw))
 raw.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
 for x in raw:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];p=0
 for s,e,new,sv,nw in sel:o += [t[p:s],new];p=e
 o.append(t[p:]);return ortho("".join(o)),len(sel)

def transform(t,tok):
 base_chat=cc(tok,t);base_content=tc(tok,t)
 c,k=content_candidate(t,tok)
 # Formatting-only variant: removes redundant spaces after MCQ labels, not wording.
 f=re.sub(r"(?m)^([A-F]\)) +",r"\1",c)
 candidates=[(t,0),(ortho(t),0),(c,k),(f,k)]
 # choose by real chat token count; tie-break by content tokens.
 best=min(candidates,key=lambda x:(cc(tok,x[0]),tc(tok,x[0])))
 if cc(tok,best[0])>base_chat:return t,base_content,base_content,base_chat,base_chat,0
 return best[0],base_content,tc(tok,best[0]),base_chat,cc(tok,best[0]),best[1]

def choice(model,tok,text,labels):
 ids=torch.tensor([chatids(tok,text)],dtype=torch.long)
 with torch.no_grad():z=model(input_ids=ids,use_cache=False).logits[0,-1].float()
 sc={}
 for L in labels:
  vals=[]
  for surf in (L," "+L):
   ii=tok(surf,add_special_tokens=False)["input_ids"]
   if len(ii)==1:vals.append(float(z[ii[0]]))
  if not vals:
   ii=tok(L,add_special_tokens=False)["input_ids"];vals=[float(z[ii[0]])]
  sc[L]=max(vals)
 return max(sc,key=sc.get)

rows=loadrows()
res={"version":"ACP-U8.3 final-candidate","dictionary_source":"U8 learned from MedAraBench train only","tokenizers":{},"behavior":{}}
for mid in TOKENIZERS:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
  B=T=CB=CT=rep=0
  for r in rows[:1200]:
   p=prompt(r);tr,b,n,cb,ct,k=transform(p,tok)
   B+=b;T+=n;CB+=cb;CT+=ct;rep+=k
  res["tokenizers"][mid]={
   "content_reduction_pct":100*(B-T)/B,
   "chat_reduction_pct":100*(CB-CT)/CB,
   "passes30_chat":100*(CB-CT)/CB>=30,
   "no_regression":T<=B and CT<=CB,
   "replacements":rep
  }
 except Exception as e:res["tokenizers"][mid]={"error":repr(e)}

res["behavior"]={}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u83_tokens_results.json","w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U83_TOKENS="+json.dumps(res["tokenizers"],ensure_ascii=False),flush=True)
