#!/usr/bin/env python3
import re,json,os,csv,io,urllib.request,random,gc
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM

SEED=181
random.seed(SEED);torch.manual_seed(SEED)
MT="HPLT/translate-ar-en-v1.0-hplt_opus"
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]

GLOSS=[
("استبعاد الحمل","ruling out pregnancy"),("لا تتجاوز","do not exceed"),("لا يعاني المريض من","patient does not have"),("لا يعاني من","does not have"),
("لا توجد","there is no"),("لا يوجد","there is no"),("ليس لدى","does not have"),("لم يحدث","did not occur"),("ينفي","denies"),
("بدون","without"),("دون","without"),("لا تعط","do not give"),
("الجانب الأيسر","left side"),("الجانب الأيمن","right side"),("اليسرى","left"),("اليمنى","right"),("الأيسر","left"),("الأيمن","right"),
("الحمل","pregnancy"),("حامل","pregnant"),("حساسية","allergy"),("الخاصرة","flank"),("دوخة","dizziness"),("الدوخة","dizziness"),
("الهواء المحيط","ambient air"),("الكرياتينين","creatinine"),("تشبع الأكسجين","oxygen saturation"),("ضغط الدم","blood pressure"),
("سكر الدم","blood glucose"),("السكر التراكمي","HbA1c"),("الهيموغلوبين","hemoglobin"),("البوتاسيوم","potassium"),("الصوديوم","sodium"),
("الأنسولين","insulin"),("الانسولين","insulin"),("الأموكسيسيلين","amoxicillin"),("الوارفارين","warfarin"),("حمى","fever"),("الحمى","fever"),("الحمّى","fever"),
("ارتفاع ضغط الدم","hypertension"),("مرض السكري","diabetes"),("داء السكري","diabetes"),("مرض الكلى المزمن","chronic kidney disease"),
("احتشاء عضلة القلب","myocardial infarction"),("الرجفان الأذيني","atrial fibrillation"),("مرض الانسداد الرئوي المزمن","chronic obstructive pulmonary disease"),
("التهاب المسالك البولية","urinary tract infection"),("التصوير المقطعي المحوسب","computed tomography"),("التصوير بالرنين المغناطيسي","magnetic resonance imaging"),
("تخطيط القلب الكهربائي","electrocardiogram"),("مؤشر كتلة الجسم","body mass index")
]
GLOSS=sorted(GLOSS,key=lambda x:len(x[0]),reverse=True)
EN_CANON=[
("chronic obstructive pulmonary disease","COPD"),("chronic kidney disease","CKD"),("myocardial infarction","MI"),
("atrial fibrillation","AF"),("urinary tract infection","UTI"),("magnetic resonance imaging","MRI"),
("computed tomography","CT"),("electrocardiogram","ECG"),("body mass index","BMI"),("oxygen saturation","SpO2"),
("blood pressure","BP"),("hemoglobin a1c","HbA1c"),("deep vein thrombosis","DVT"),("pulmonary embolism","PE")
]
VAL=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?|units?))?(?![A-Za-z])",re.I)
NEG_RE=re.compile(r"(?<![\w\u0600-\u06ff])(?:لا|ليس|ليست|لم|لن|دون|بدون|ينفي)(?![\w\u0600-\u06ff])")
LEFT_RE=re.compile(r"(?:الأيسر|اليسرى|يسار|\bleft\b)",re.I);RIGHT_RE=re.compile(r"(?:الأيمن|اليمنى|يمين|\bright\b)",re.I)

STRESS=[
"لا يعاني المريض من ألم في الصدر.","لا توجد علامات لالتهاب رئوي.","المريض بدون حساسية معروفة للأدوية.","لم يحدث نزيف بعد العملية.",
"ليس لدى المريض تاريخ سابق للسكتة الدماغية.","ينفي المريض وجود ضيق في التنفس.","لا يوجد ألم في الجانب الأيسر من الصدر.","لا يوجد ضعف في الطرف الأيمن.",
"ألم في الركبة اليسرى منذ ثلاثة أيام.","تورم في الساق اليمنى.","ضعف في الذراع اليسرى بعد السكتة.","كسر في عظم الفخذ الأيمن.",
"ألم في الخاصرة اليمنى دون حمى.","الكتلة موجودة في الثدي الأيسر.","أعط المريض 500 mg من الأموكسيسيلين.","يتناول المريض 5 mg من الوارفارين يوميا.",
"أعط 20 mL من المحلول.","تشبع الأكسجين 92%.","ضغط الدم 160/100 mmHg.","معدل النبض 120 bpm.","درجة الحرارة 39.2 °C.",
"سكر الدم 45 mg/dL.","جرعة الأنسولين 10 وحدات قبل العشاء.","أعط 2.5 mg كل 12 ساعة.","بدأ الألم قبل ساعتين.","حدث القيء بعد تناول الدواء.",
"يؤخذ الدواء قبل الطعام.","يؤخذ الدواء بعد الطعام.","ظهرت الأعراض بعد الجراحة بيومين.","أوقف الدواء قبل العملية بثلاثة أيام.",
"لا تعط الدواء قبل استبعاد الحمل.","لا تعط جرعة إضافية بعد 6 ساعات.","ضغط الدم 90/60 mmHg ولا توجد دوخة.","تشبع الأكسجين 88% في الهواء المحيط.",
"المريض يتناول 1000 mg ميتفورمين مرتين يوميا.","المريضة حامل في الأسبوع 32.","الهيموغلوبين 7.5 g/dL.","الكرياتينين 2.1 mg/dL.",
"البوتاسيوم 6.2 mmol/L.","الصوديوم 128 mmol/L.","لا يوجد نزيف في العين اليمنى.","لا توجد كتلة في الثدي الأيسر.",
"ألم في الجانب الأيمن بدأ بعد السقوط.","ضعف الجانب الأيسر بدأ قبل ساعة.","أعط 0.5 mL في الذراع اليسرى.","لا تتجاوز الجرعة 4 g خلال 24 ساعة.",
"الهدف إبقاء الضغط أقل من 130/80 mmHg.","السكر التراكمي 8.4% والهدف أقل من 7%."
]

def lock(text):
 spans=[]
 for m in VAL.finditer(text):spans.append((m.start(),m.end(),m.group(0)))
 for ar,en in GLOSS:
  for m in re.finditer(re.escape(ar),text):spans.append((m.start(),m.end(),en))
 spans.sort(key=lambda x:(x[0],-(x[1]-x[0])));sel=[]
 for x in spans:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];p=0;mp={}
 for i,(s,e,val) in enumerate(sel):
  key=str(970000003+i*149);o.append(text[p:s]);o.append(key);mp[key]=val;p=e
 o.append(text[p:]);return "".join(o),mp

tok=AutoTokenizer.from_pretrained(MT,trust_remote_code=True);mt=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);mt.eval()
@torch.no_grad()
def trans(texts):
 locked=[];maps=[]
 for t in texts:
  a,b=lock(t);locked.append(a);maps.append(b)
 out=[]
 for i in range(0,len(locked),12):
  x=tok(locked[i:i+12],return_tensors="pt",padding=True,truncation=True,max_length=256)
  g=mt.generate(**x,max_new_tokens=220,num_beams=1);out+=tok.batch_decode(g,skip_special_tokens=True)
 ans=[]
 for src,s,mp in zip(texts,out,maps):
  ok=True
  for key,val in mp.items():
   if key not in s:ok=False;break
   s=s.replace(key,val)
  ans.append((s if ok else src,ok))
 return ans

def canon_val(v):
 x=re.sub(r"\s+","",v.lower());x=x.replace("وحدات","unit").replace("وحدة","unit").replace("units","unit")
 return x
def facts(t):
 s=" "+t.lower()+" ";f=set()
 if NEG_RE.search(t) or any(x in s for x in [" no "," not "," without "," denies ","does not","did not"]):f.add("NEG")
 if LEFT_RE.search(t):f.add("LEFT")
 if RIGHT_RE.search(t):f.add("RIGHT")
 groups={"PREG":["حامل","الحمل","pregnant","pregnancy"],"ALLERGY":["حساسية","allergy"],"RULEOUT":["استبعاد","rule out","ruling out"],
 "FLANK":["الخاصرة","flank"],"DIZZY":["دوخة","dizziness"],"CREAT":["الكرياتينين","creatinine"],"AMBIENT":["الهواء المحيط","ambient air","room air"],
 "BP":["ضغط الدم","blood pressure"," bp "],"SPO2":["تشبع الأكسجين","oxygen saturation","spo2"],"GLU":["سكر الدم","blood glucose","blood sugar"],
 "HBA1C":["السكر التراكمي","hba1c"],"INS":["الأنسولين","الانسولين","insulin"],"FEVER":["حمى","الحمى","الحمّى","fever"]}
 for k,vs in groups.items():
  if any(v in s for v in vs):f.add(k)
 for m in VAL.finditer(t):f.add("VAL:"+canon_val(m.group(0)))
 return f

def cc(tk,t):
 try:return len(tk.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True))
 except:return len(tk(t,add_special_tokens=False)["input_ids"])
def canonicalize(t,tk):
 cur=t
 for old,new in EN_CANON:
  for m in list(re.finditer(re.escape(old),cur,re.I))[::-1]:
   cand=cur[:m.start()]+new+cur[m.end():]
   if cc(tk,cand)<cc(tk,cur) and facts(cand)==facts(cur):cur=cand
 return cur

stress_t=trans(STRESS)
stress=[]
for src,(candidate,sok) in zip(STRESS,stress_t):
 safe=sok and facts(src)==facts(candidate)
 final=candidate if safe else src
 stress.append({"source":src,"candidate":candidate,"sentinels_ok":sok,"facts_equal":facts(src)==facts(candidate),"accepted":safe,"final":final})
safety=sum(facts(x["source"])==facts(x["final"]) for x in stress)/len(stress)

raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace");rows=list(csv.DictReader(io.StringIO(raw)));random.Random(SEED).shuffle(rows);rows=rows[:100]
segs=[];slot=[]
for i,r in enumerate(rows):
 segs.append(r["Question"]);slot.append((i,"q"))
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:segs.append(v);slot.append((i,L))
trs=trans(segs);valid=[True]*len(rows)
for (cand,sok),(i,k),src in zip(trs,slot,segs):
 if not sok or facts(src)!=facts(cand):cand=src;valid[i]=False
 rows[i]["_"+k]=cand
def ap(r):
 z=["السؤال: "+r["Question"]]
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:z.append(f"{L}) {v}")
 z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"];return "\n".join(z)
def ep(r):
 z=["Q:"+r["_q"]]
 for L in "ABCDEF":
  if "_"+L in r:z.append(f"{L}:{r['_'+L]}")
 z+=["Answer:"];return "\n".join(z)

res={"version":"U18 sentinel + clinical canonicalization","stress_final_fact_integrity":safety,"stress_translation_accept_rate":sum(x["accepted"] for x in stress)/len(stress),"stress":stress,"models":{}}
for name,mid in MODELS:
 try:
  tk2=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=used=0
  for i,r in enumerate(rows):
   a=ap(r);e=ep(r);e=canonicalize(e,tk2)
   # Final whole-prompt fact equality; otherwise Arabic fallback.
   if valid[i] and facts(a)==facts(e) and cc(tk2,e)<cc(tk2,a):g=e;used+=1
   else:g=a
   B+=cc(tk2,a);T+=cc(tk2,g)
  res["models"][name]={"chat_reduction_pct":100*(B-T)/B,"accepted_cases":used,"n":len(rows),"passes30":100*(B-T)/B>=30}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u18_hybrid.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U18="+json.dumps(res,ensure_ascii=False),flush=True)
