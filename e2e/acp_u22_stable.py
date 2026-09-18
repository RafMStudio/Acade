#!/usr/bin/env python3
import re,json,os,csv,io,urllib.request,random,gc
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
SEED=281
random.seed(SEED);torch.manual_seed(SEED)
MT="HPLT/translate-ar-en-v1.0-hplt_opus"
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
GLOSS=[
("استبعاد الحمل","ruling out pregnancy"),("لا تتجاوز","do not exceed"),("لا يعاني المريض من","patient does not have"),("لا يعاني من","does not have"),
("لا توجد","there is no"),("لا يوجد","there is no"),("ليس لدى","does not have"),("لم يحدث","did not occur"),("ينفي","denies"),("بدون","without"),("دون","without"),("لا تعط","do not give"),
("الجانب الأيسر","left side"),("الجانب الأيمن","right side"),("اليسرى","left"),("اليمنى","right"),("الأيسر","left"),("الأيمن","right"),
("الحمل","pregnancy"),("حامل","pregnant"),("حساسية","allergy"),("الخاصرة","flank"),("دوخة","dizziness"),("الدوخة","dizziness"),
("الهواء المحيط","ambient air"),("الكرياتينين","creatinine"),("تشبع الأكسجين","oxygen saturation"),("ضغط الدم","blood pressure"),
("سكر الدم","blood glucose"),("السكر التراكمي","hemoglobin A1c"),("الهيموغلوبين","hemoglobin"),("البوتاسيوم","potassium"),("الصوديوم","sodium"),
("الأنسولين","insulin"),("الانسولين","insulin"),("الأموكسيسيلين","amoxicillin"),("الوارفارين","warfarin"),("حمى","fever"),("الحمى","fever"),("الحمّى","fever"),
("ارتفاع ضغط الدم","hypertension"),("مرض السكري","diabetes"),("داء السكري","diabetes"),("مرض الكلى المزمن","chronic kidney disease"),
("احتشاء عضلة القلب","myocardial infarction"),("الرجفان الأذيني","atrial fibrillation"),("مرض الانسداد الرئوي المزمن","chronic obstructive pulmonary disease"),
("التهاب المسالك البولية","urinary tract infection"),("التصوير المقطعي المحوسب","computed tomography"),("التصوير بالرنين المغناطيسي","magnetic resonance imaging"),
("تخطيط القلب الكهربائي","electrocardiogram"),("مؤشر كتلة الجسم","body mass index"),("ضعف","weakness"),("الذراع","arm"),("الساق","leg"),
("الركبة","knee"),("نزيف","bleeding"),("ألم","pain"),("الكتلة","mass"),("الثدي","breast"),("السكتة الدماغية","stroke"),("التهاب رئوي","pneumonia"),
("ضيق التنفس","dyspnea"),("القيء","vomiting")
]
GLOSS=sorted(GLOSS,key=lambda x:len(x[0]),reverse=True)
CANON=[
("chronic obstructive pulmonary disease","COPD"),("chronic kidney disease","CKD"),("acute kidney injury","AKI"),
("myocardial infarction","MI"),("atrial fibrillation","AF"),("coronary artery disease","CAD"),("deep vein thrombosis","DVT"),("pulmonary embolism","PE"),
("urinary tract infection","UTI"),("magnetic resonance imaging","MRI"),("computed tomography","CT"),("electrocardiogram","ECG"),
("body mass index","BMI"),("oxygen saturation","SpO2"),("blood pressure","BP"),("hemoglobin a1c","HbA1c"),("complete blood count","CBC"),
("white blood cell count","WBC"),("red blood cell count","RBC"),("heart rate","HR"),("respiratory rate","RR"),("intensive care unit","ICU"),
("emergency department","ED"),("coronary artery bypass graft","CABG"),("cardiopulmonary resuscitation","CPR"),
("gastroesophageal reflux disease","GERD"),("congestive heart failure","CHF"),("left ventricular ejection fraction","LVEF"),
("shortness of breath","dyspnea"),("past medical history","PMH"),("family history","FHx"),("medical history","Hx"),
("risk factors","RF"),("risk factor","RF"),("signs and symptoms","Sx"),("signs","Sx"),("symptoms","Sx"),
("all of the following are true except","All true EXCEPT"),("all of the following except","All EXCEPT"),
("which of the following","Which"),("most likely diagnosis","Dx?"),("treatment of choice","Tx?"),("most appropriate treatment","Tx?")
]
CANON=sorted(CANON,key=lambda x:len(x[0]),reverse=True)
VAL=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?|units?))?(?![A-Za-z])",re.I)
NEG_AR=re.compile(r"(?<![\w\u0600-\u06ff])(?:لا|ليس|ليست|لم|لن|دون|بدون|ينفي)(?![\w\u0600-\u06ff])")
def canon_val(v):return re.sub(r"\s+","",v.lower()).replace("وحدات","unit").replace("وحدة","unit").replace("units","unit")
def facts(t):
 s=" "+t.lower()+" ";f=set()
 if NEG_AR.search(t) or any(x in s for x in [" no "," not "," without "," denies ","does not","did not"]):f.add("NEG")
 groups={"LEFT":["الأيسر","اليسرى"," left"],"RIGHT":["الأيمن","اليمنى"," right"],"PREG":["حامل","الحمل","pregnant","pregnancy"],
 "ALLERGY":["حساسية","allergy"],"RULEOUT":["استبعاد","rule out","ruling out"],"FLANK":["الخاصرة","flank"],"DIZZY":["دوخة","dizziness"],"CREAT":["الكرياتينين","creatinine"],
 "AMBIENT":["الهواء المحيط","ambient air","room air"],"BP":["ضغط الدم","blood pressure"," bp "],"SPO2":["تشبع الأكسجين","oxygen saturation","spo2"],
 "GLU":["سكر الدم","blood glucose","blood sugar"],"HBA1C":["السكر التراكمي","hemoglobin a1c","hba1c"],"INS":["الأنسولين","الانسولين","insulin"],
 "FEVER":["حمى","الحمى","الحمّى","fever"],"WEAK":["ضعف","weakness"],"PAIN":["ألم","pain"],"BLEED":["نزيف","bleeding"],"STROKE":["السكتة الدماغية","stroke"],"VOMIT":["القيء","vomiting"]}
 for k,vs in groups.items():
  if any(v in s for v in vs):f.add(k)
 for m in VAL.finditer(t):f.add("VAL:"+canon_val(m.group(0)))
 return f
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
  key=f"ZXQ{i}QXZ";o.append(text[p:s]);o.append(key);mp[key]=val;p=e
 o.append(text[p:]);return "".join(o),mp
tok=AutoTokenizer.from_pretrained(MT,trust_remote_code=True);mt=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);mt.eval()
@torch.no_grad()
def trans(texts):
 locked=[];maps=[]
 for t in texts:
  a,b=lock(t);locked.append(a);maps.append(b)
 out=[]
 for i in range(0,len(locked),12):
  x=tok(locked[i:i+12],return_tensors="pt",padding=True,truncation=True,max_length=256);g=mt.generate(**x,max_new_tokens=220,num_beams=1);out+=tok.batch_decode(g,skip_special_tokens=True)
 ans=[]
 for src,s,mp in zip(texts,out,maps):
  ok=True
  for k,v in mp.items():
   if k not in s:ok=False;break
   s=s.replace(k,v)
  if not ok or facts(src)!=facts(s):s=src;ok=False
  ans.append((s,ok))
 return ans
def cc(tk,s):
 try:return len(tk.apply_chat_template([{"role":"user","content":s}],tokenize=True,add_generation_prompt=True))
 except:return len(tk(s,add_special_tokens=False)["input_ids"])
def compact(s,tk):
 cur=s
 for old,new in CANON:
  for m in list(re.finditer(re.escape(old),cur,re.I))[::-1]:
   cand=cur[:m.start()]+new+cur[m.end():]
   if facts(cand)==facts(cur) and cc(tk,cand)<cc(tk,cur):cur=cand
 return cur
STRESS=["لا يوجد ضعف في الطرف الأيمن.","ضعف في الذراع اليسرى بعد السكتة.","ألم في الخاصرة اليمنى دون حمى.","ضغط الدم 90/60 mmHg ولا توجد دوخة.","لا تعط الدواء قبل استبعاد الحمل.","تشبع الأكسجين 88% في الهواء المحيط.","الكرياتينين 2.1 mg/dL.","السكر التراكمي 8.4% والهدف أقل من 7%."]
tt=trans(STRESS);audit=[{"src":a,"out":b,"accepted":ok,"facts_equal":facts(a)==facts(b)} for a,(b,ok) in zip(STRESS,tt)]
raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace");rows=list(csv.DictReader(io.StringIO(raw)));random.Random(SEED).shuffle(rows);rows=rows[:100]
segs=[];slot=[]
for i,r in enumerate(rows):
 segs.append(r["Question"]);slot.append((i,"q",r["Question"]))
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:segs.append(v);slot.append((i,L,v))
tr=trans(segs);valid=[True]*len(rows)
for (out,ok),(i,k,orig) in zip(tr,slot):
 if not ok:valid[i]=False
 rows[i]["_"+k]=out
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
 z+=["Answer letter only:"];return "\n".join(z)
res={"version":"U22 stable sentinel + clinical shorthand","stress":audit,"stress_integrity":sum(x["facts_equal"] for x in audit)/len(audit),"models":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=used=0
  for i,r in enumerate(rows):
   a=ap(r);e=compact(ep(r),tk)
   if valid[i] and facts(a)==facts(e) and cc(tk,e)<cc(tk,a):g=e;used+=1
   else:g=a
   B+=cc(tk,a);T+=cc(tk,g)
  res["models"][name]={"chat_reduction_pct":100*(B-T)/B,"accepted_cases":used,"n":len(rows),"passes30":100*(B-T)/B>=30}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u22_stable.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U22="+json.dumps(res,ensure_ascii=False),flush=True)
