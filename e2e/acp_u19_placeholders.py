#!/usr/bin/env python3
import json,os,torch,re
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
MODELS=[
("HPLT","HPLT/translate-ar-en-v1.0-hplt_opus",False),
("NLLB","facebook/nllb-200-distilled-600M",True)
]
PATTERNS={
"numeric":lambda i:str(970000003+i*149),
"xml":lambda i:f"<x{i}>",
"doubleunderscore":lambda i:f"__P{i}__",
"bracket":lambda i:f"[P{i}]",
"zxq":lambda i:f"ZXQ{i}QXZ",
"word":lambda i:f"PROTECTED{i}TOKEN",
"alpha":lambda i:chr(65+i)+chr(75+i)+chr(80+i)+"SAFE"
}
TEMPLATES=[
"المريض يعاني من {p0} مع {p1}.",
"لا تعط الدواء قبل {p0} وبعد {p1}.",
"النتيجة هي {p0} وقياس آخر {p1}.",
"ألم في {p0} دون {p1}.",
"المريضة لديها {p0} مع قيمة {p1}.",
"يؤخذ {p0} كل {p1} ساعات.",
"لوحظ {p0} في الجانب {p1}.",
"الهدف هو {p0} وليس {p1}.",
]
res={"version":"U19 placeholder survival","models":{}}
for name,mid,nllb in MODELS:
 tok=AutoTokenizer.from_pretrained(mid,src_lang="arb_Arab" if nllb else None,trust_remote_code=True)
 m=AutoModelForSeq2SeqLM.from_pretrained(mid,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);m.eval()
 bos=tok.convert_tokens_to_ids("eng_Latn") if nllb else None
 rr={}
 for pn,fn in PATTERNS.items():
  src=[];expected=[]
  for t in TEMPLATES:
   p0,p1=fn(0),fn(1);src.append(t.format(p0=p0,p1=p1));expected.append([p0,p1])
  x=tok(src,return_tensors="pt",padding=True,truncation=True,max_length=128)
  with torch.no_grad():
   kwargs={"max_new_tokens":128,"num_beams":1}
   if nllb:kwargs["forced_bos_token_id"]=bos
   g=m.generate(**x,**kwargs)
  outs=tok.batch_decode(g,skip_special_tokens=True)
  exact=sum(all(p in o for p in exp) for o,exp in zip(outs,expected))
  charcost=sum(len(" ".join(exp)) for exp in expected)/len(expected)
  rr[pn]={"exact_case_rate":exact/len(src),"outputs":[{"src":a,"out":b,"expected":c} for a,b,c in zip(src,outs,expected)],"placeholder_chars":charcost}
 res["models"][name]=rr
 del m
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u19_placeholders.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U19="+json.dumps(res,ensure_ascii=False),flush=True)
