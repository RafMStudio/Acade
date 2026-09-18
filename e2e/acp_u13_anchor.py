#!/usr/bin/env python3
import csv,io,json,os,re,urllib.request,statistics as st
from transformers import AutoTokenizer
PD="https://raw.githubusercontent.com/nyuad-cai/MedArabiQ/main/datasets/patient-doctor-qa.csv"
MA="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
ALIASES=[
("ارتفاع ضغط الدم","HTN"),("مرض السكري","DM"),("داء السكري","DM"),("مرض الكلى المزمن","CKD"),("تشبع الأكسجين","SpO2"),("مؤشر كتلة الجسم","BMI"),
("مرض الانسداد الرئوي المزمن","COPD"),("احتشاء عضلة القلب","MI"),("الرجفان الأذيني","AF"),("مرض الشرايين التاجية","CAD"),
("الخثار الوريدي العميق","DVT"),("الانصمام الرئوي","PE"),("الهيموغلوبين السكري","HbA1c"),("السكر التراكمي","HbA1c"),
("التصوير المقطعي المحوسب","CT"),("التصوير بالرنين المغناطيسي","MRI"),("تخطيط القلب الكهربائي","ECG"),("تعداد الدم الكامل","CBC"),
("التهاب المسالك البولية","UTI"),("الحماض الكيتوني السكري","DKA"),("إصابة الكلى الحادة","AKI"),("فيروس نقص المناعة البشرية","HIV"),
("التهاب الكبد الوبائي ب","HBV"),("التهاب الكبد الوبائي سي","HCV"),("سكري الحمل","GDM")]
ALIASES=sorted(ALIASES,key=lambda x:len(x[0]),reverse=True)
def fetch(url):
 raw=urllib.request.urlopen(url,timeout=120).read().decode("utf-8-sig","replace");return list(csv.DictReader(io.StringIO(raw)))
def tc(tk,s):return len(tk(s,add_special_tokens=False)["input_ids"])
def anchor(text,tk):
 base=tc(tk,text);best=text;used=[]
 # apply concept by concept only when whole-text tokens improve.
 for ar,abbr in ALIASES:
  matches=list(re.finditer(re.escape(ar),best))
  if len(matches)<2:continue
  # first occurrence anchors meaning, subsequent occurrences compact.
  m0=matches[0]
  candidate=best[:m0.start()]+ar+" ("+abbr+")"+best[m0.end():]
  # recalc remaining occurrences after anchor insert
  start=m0.start()+len(ar)+len(abbr)+3
  candidate=candidate[:start]+candidate[start:].replace(ar,abbr)
  if tc(tk,candidate)<tc(tk,best):
   best=candidate;used.append(ar)
 if tc(tk,best)>base:return text,[]
 return best,used
pd=fetch(PD);ma=fetch(MA)
texts=[]
for r in pd[:3000]:
 for k in ("Question_description","Question","Answer"):
  v=(r.get(k) or "").strip()
  if len(v)>=40:texts.append(v)
# Repetition-heavy subset is the true use case for anchored coding.
reptexts=[t for t in texts if any(len(re.findall(re.escape(ar),t))>=2 for ar,_ in ALIASES)]
res={"version":"U13 transparent first-mention anchoring","patient_texts":len(texts),"repetition_texts":len(reptexts),"models":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
  B=T=used=0;case=[]
  for t in reptexts:
   v,u=anchor(t,tk);b=tc(tk,t);n=tc(tk,v);B+=b;T+=n;used+=len(u);case.append(100*(b-n)/b if b else 0)
  res["models"][name]={"repetition_subset_reduction_pct":100*(B-T)/B if B else 0,"median_case_pct":st.median(case) if case else 0,"concepts_anchored":used,"n":len(reptexts),"no_regression":T<=B}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u13_anchor.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U13="+json.dumps(res,ensure_ascii=False),flush=True)
