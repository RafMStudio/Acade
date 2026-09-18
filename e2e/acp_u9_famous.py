#!/usr/bin/env python3
import csv,io,json,os,random,urllib.request,gc,time
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM,AutoModelForCausalLM

SEED=71
random.seed(SEED);torch.manual_seed(SEED)
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MT="facebook/nllb-200-distilled-600M"
TOKS=[
("Qwen3","Qwen/Qwen3-0.6B"),
("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),
("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),
("Gemma3","unsloth/gemma-3-1b-it"),
("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),
("Phi4-mini","microsoft/Phi-4-mini-instruct"),
("Falcon3","tiiuae/Falcon3-1B-Instruct"),
("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
BEH=[("Qwen3","Qwen/Qwen3-0.6B",12),("Llama3.2","unsloth/Llama-3.2-1B-Instruct",12),("Gemma3","unsloth/gemma-3-1b-it",12)]

def rows():
 raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace")
 z=list(csv.DictReader(io.StringIO(raw)));random.Random(SEED).shuffle(z);return z[:80]

def ar_prompt(r):
 z=["السؤال: "+r["Question"]]
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:z.append(f"{L}) {v}")
 z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
 return "\n".join(z)

def en_prompt(r,compact=True):
 z=[("Q:"+r["_qen"]) if compact else ("Question: "+r["_qen"])]
 for L in "ABCDEF":
  v=r.get("_"+L,"")
  if v:z.append((L+":"+v) if compact else (L+") "+v))
 z.append("Answer:")
 return "\n".join(z)

def translate(rs):
 tok=AutoTokenizer.from_pretrained(MT,src_lang="arb_Arab")
 mod=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True);mod.eval()
 seg=[];slots=[]
 for i,r in enumerate(rs):
  seg.append(r["Question"]);slots.append((i,"_qen"))
  for L in "ABCDEF":
   v=(r.get("Option "+L) or "").strip()
   if v:seg.append(v);slots.append((i,"_"+L))
 target=tok.convert_tokens_to_ids("eng_Latn")
 for i in range(0,len(seg),12):
  b=seg[i:i+12];x=tok(b,return_tensors="pt",padding=True,truncation=True,max_length=256)
  with torch.no_grad():g=mod.generate(**x,forced_bos_token_id=target,max_new_tokens=200,num_beams=1)
  outs=tok.batch_decode(g,skip_special_tokens=True)
  for j,v in enumerate(outs):
   ri,k=slots[i+j];rs[ri][k]=v.strip()
 del mod,tok;gc.collect()

def ids(tok,t):
 try:return tok.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True)
 except:return tok(t,add_special_tokens=False)["input_ids"]
def tc(tok,t):return len(tok(t,add_special_tokens=False)["input_ids"])
def cc(tok,t):return len(ids(tok,t))

def choose_repr(tok,r):
 a=ar_prompt(r);e=en_prompt(r,True)
 # Only select English if it is cheaper by at least 5%, otherwise preserve Arabic.
 ca,ce=cc(tok,a),cc(tok,e)
 return (e if ce<=ca*.95 else a),a,e

def suffix(model,tok,p,s):
 pref=torch.tensor([ids(tok,p)],dtype=torch.long);ii=tok(s,add_special_tokens=False)["input_ids"]
 if not ii:return -1e30
 total=0.0;cur=pref
 with torch.no_grad():
  for tid in ii:
   z=model(input_ids=cur,use_cache=False).logits[0,-1].float();total+=float(F.log_softmax(z,dim=-1)[tid]);cur=torch.cat([cur,torch.tensor([[tid]])],1)
 return total
def choice(model,tok,p,labels):
 pref=torch.tensor([ids(tok,p)],dtype=torch.long)
 with torch.no_grad():z=model(input_ids=pref,use_cache=False).logits[0,-1].float()
 sc={}
 for L in labels:
  vals=[]
  for surf in (L," "+L):
   ii=tok(surf,add_special_tokens=False)["input_ids"]
   vals.append(float(z[ii[0]]) if len(ii)==1 else suffix(model,tok,p,surf))
  sc[L]=max(vals)
 return max(sc,key=sc.get)

rs=rows();translate(rs)
res={"version":"ACP-U9 NLLB field-level fallback","translator":MT,"n":len(rs),"tokenizers":{},"behavior":{}}
for name,mid in TOKS:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
  B=T=CB=CT=used=0
  for r in rs:
   g,a,e=choose_repr(tok,r);B+=tc(tok,a);T+=tc(tok,g);CB+=cc(tok,a);CT+=cc(tok,g);used+=g==e
  res["tokenizers"][name]={"model_id":mid,"content_reduction_pct":100*(B-T)/B,"chat_reduction_pct":100*(CB-CT)/CB,"translated_cases":used,"passes30_content":100*(B-T)/B>=30,"passes30_chat":100*(CB-CT)/CB>=30}
 except Exception as e:res["tokenizers"][name]={"error":repr(e)}
for name,mid,n in BEH:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);mod=AutoModelForCausalLM.from_pretrained(mid,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);mod.eval()
  ag=ba=ca=0;B=T=0;changed=[]
  for r in rs[:n]:
   a=ar_prompt(r);g,_,_=choose_repr(tok,r);labels=[L for L in "ABCDEF" if (r.get("Option "+L) or "").strip()]
   x=choice(mod,tok,a,labels);y=choice(mod,tok,g,labels);gold=(r.get("Correct Answer") or "").strip().upper()[:1]
   ag+=x==y;ba+=x==gold;ca+=y==gold;B+=cc(tok,a);T+=cc(tok,g)
   if x!=y:changed.append({"q":r.get("Question Number"),"base":x,"new":y,"gold":gold})
  res["behavior"][name]={"n":n,"agreement":ag/n,"baseline_accuracy":ba/n,"compressed_accuracy":ca/n,"chat_reduction_pct":100*(B-T)/B,"changed":changed}
  del mod;gc.collect()
 except Exception as e:res["behavior"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u9_results.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U9="+json.dumps(res,ensure_ascii=False),flush=True)
