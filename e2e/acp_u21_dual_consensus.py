#!/usr/bin/env python3
import re,json,os,csv,io,urllib.request,random,difflib,gc
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
SEED=251
random.seed(SEED);torch.manual_seed(SEED)
H="HPLT/translate-ar-en-v1.0-hplt_opus";N="facebook/nllb-200-distilled-600M"
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
MAP=[
("استبعاد الحمل","ruling out pregnancy"),("لا تتجاوز","do not exceed"),("لا يعاني المريض من","patient does not have"),("لا يعاني من","does not have"),
("لا توجد","there is no"),("لا يوجد","there is no"),("ليس لدى","does not have"),("لم يحدث","did not occur"),("ينفي","denies"),("بدون","without"),("دون","without"),("لا تعط","do not give"),
("الجانب الأيسر","left side"),("الجانب الأيمن","right side"),("اليسرى","left"),("اليمنى","right"),("الأيسر","left"),("الأيمن","right"),
("الحمل","pregnancy"),("حامل","pregnant"),("حساسية","allergy"),("الخاصرة","flank"),("دوخة","dizziness"),("الدوخة","dizziness"),
("الهواء المحيط","ambient air"),("الكرياتينين","creatinine"),("تشبع الأكسجين","oxygen saturation"),("ضغط الدم","blood pressure"),
("سكر الدم","blood glucose"),("السكر التراكمي","HbA1c"),("الهيموغلوبين","hemoglobin"),("البوتاسيوم","potassium"),("الصوديوم","sodium"),
("الأنسولين","insulin"),("الانسولين","insulin"),("الأموكسيسيلين","amoxicillin"),("الوارفارين","warfarin"),("حمى","fever"),("الحمى","fever"),("الحمّى","fever"),
("ارتفاع ضغط الدم","hypertension"),("مرض السكري","diabetes"),("داء السكري","diabetes"),("مرض الكلى المزمن","chronic kidney disease"),
("احتشاء عضلة القلب","myocardial infarction"),("الرجفان الأذيني","atrial fibrillation"),("مرض الانسداد الرئوي المزمن","chronic obstructive pulmonary disease"),
("التهاب المسالك البولية","urinary tract infection"),("التصوير المقطعي المحوسب","computed tomography"),("التصوير بالرنين المغناطيسي","magnetic resonance imaging"),
("تخطيط القلب الكهربائي","electrocardiogram"),("مؤشر كتلة الجسم","body mass index"),
("ضعف","weakness"),("الذراع","arm"),("الساق","leg"),("الركبة","knee"),("نزيف","bleeding"),("ألم","pain"),("الكتلة","mass"),("الثدي","breast"),
("السكتة الدماغية","stroke"),("التهاب رئوي","pneumonia"),("ضيق التنفس","shortness of breath"),("القيء","vomiting"),("الجراحة","surgery")
]
MAP=sorted(MAP,key=lambda x:len(x[0]),reverse=True)
VAL=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?|units?))?(?![A-Za-z])",re.I)
NEG_AR=re.compile(r"(?<![\w\u0600-\u06ff])(?:لا|ليس|ليست|لم|لن|دون|بدون|ينفي)(?![\w\u0600-\u06ff])")
STOP=set("the a an is are was were be been being of to in on at for with by as and or but if then than this that these those it its patient patients has have had do does did from into after before during per every each another other there here who which what when where how why one two three can could should would may might".split())
def precanon(t):
 cur=t
 for a,b in MAP:cur=cur.replace(a,b)
 return cur
def canon_val(v):return re.sub(r"\s+","",v.lower()).replace("وحدات","unit").replace("وحدة","unit").replace("units","unit")
def facts(t):
 s=" "+t.lower()+" ";f=set()
 if NEG_AR.search(t) or any(x in s for x in [" no "," not "," without "," denies ","does not","did not"]):f.add("NEG")
 for k,vs in {
 "LEFT":["الأيسر","اليسرى"," left"],"RIGHT":["الأيمن","اليمنى"," right"],"PREG":["حامل","الحمل","pregnant","pregnancy"],
 "ALLERGY":["حساسية","allergy"],"RULEOUT":["استبعاد","rule out","ruling out"],"FLANK":["الخاصرة","flank"],"DIZZY":["دوخة","dizziness"],
 "CREAT":["الكرياتينين","creatinine"],"AMBIENT":["الهواء المحيط","ambient air","room air"],"BP":["ضغط الدم","blood pressure"],
 "SPO2":["تشبع الأكسجين","oxygen saturation","spo2"],"GLU":["سكر الدم","blood glucose","blood sugar"],"HBA1C":["السكر التراكمي","hba1c"],
 "INS":["الأنسولين","الانسولين","insulin"],"FEVER":["حمى","الحمى","الحمّى","fever"],"WEAK":["ضعف","weakness"],"PAIN":["ألم","pain"],
 "BLEED":["نزيف","bleeding"],"STROKE":["السكتة الدماغية","stroke"],"VOMIT":["القيء","vomiting"]}.items():
  if any(v in s for v in vs):f.add(k)
 for m in VAL.finditer(t):f.add("VAL:"+canon_val(m.group(0)))
 return f
def content(s):
 z=[x for x in re.findall(r"[a-zA-Z]+",s.lower()) if x not in STOP and len(x)>2]
 return set(z)
def consensus(a,b):
 A,B=content(a),content(b);j=len(A&B)/max(1,len(A|B));seq=difflib.SequenceMatcher(None," ".join(sorted(A))," ".join(sorted(B))).ratio()
 return max(j,seq)
ht=AutoTokenizer.from_pretrained(H,trust_remote_code=True);hm=AutoModelForSeq2SeqLM.from_pretrained(H,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);hm.eval()
nt=AutoTokenizer.from_pretrained(N,src_lang="arb_Arab");nm=AutoModelForSeq2SeqLM.from_pretrained(N,dtype="auto",low_cpu_mem_usage=True);nm.eval();bos=nt.convert_tokens_to_ids("eng_Latn")
@torch.no_grad()
def dual(texts):
 src=[precanon(x) for x in texts];ho=[];no=[]
 for i in range(0,len(src),10):
  x=ht(src[i:i+10],return_tensors="pt",padding=True,truncation=True,max_length=256);g=hm.generate(**x,max_new_tokens=220,num_beams=1);ho+=ht.batch_decode(g,skip_special_tokens=True)
  y=nt(src[i:i+10],return_tensors="pt",padding=True,truncation=True,max_length=256);q=nm.generate(**y,forced_bos_token_id=bos,max_new_tokens=220,num_beams=1);no+=nt.batch_decode(q,skip_special_tokens=True)
 return list(zip(src,ho,no))
STRESS=[
"ألم في الخاصرة اليمنى دون حمى.","ضغط الدم 90/60 mmHg ولا توجد دوخة.","لا تعط الدواء قبل استبعاد الحمل.","تشبع الأكسجين 88% في الهواء المحيط.",
"الكرياتينين 2.1 mg/dL.","لا يوجد ألم في الجانب الأيسر من الصدر.","جرعة الأنسولين 10 وحدات قبل العشاء.","ضغط الدم 160/100 mmHg.",
"لا يوجد نزيف في العين اليمنى.","المريضة حامل في الأسبوع 32.","ضعف في الذراع اليسرى بعد السكتة.","ضعف الجانب الأيسر بدأ قبل ساعة.",
"المريض بدون حساسية معروفة للأدوية.","تشبع الأكسجين 92%.","سكر الدم 45 mg/dL.","السكر التراكمي 8.4% والهدف أقل من 7%."
]
sd=dual(STRESS);sa=[]
for src,(pre,a,b) in zip(STRESS,sd):
 c=consensus(a,b);ok=(facts(src)==facts(a)==facts(b) and c>=.55);sa.append({"src":src,"pre":pre,"hplt":a,"nllb":b,"consensus":c,"facts_h":facts(src)==facts(a),"facts_n":facts(src)==facts(b),"accepted":ok})
raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace");rows=list(csv.DictReader(io.StringIO(raw)));random.Random(SEED).shuffle(rows);rows=rows[:80]
segs=[];slot=[]
for i,r in enumerate(rows):
 segs.append(r["Question"]);slot.append((i,"q",r["Question"]))
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:segs.append(v);slot.append((i,L,v))
dd=dual(segs);valid=[True]*len(rows)
for (pre,a,b),(i,k,orig) in zip(dd,slot):
 c=consensus(a,b);ok=(facts(orig)==facts(a)==facts(b) and c>=.55)
 if not ok:a=orig;valid[i]=False
 rows[i]["_"+k]=a
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
def cc(tk,s):
 try:return len(tk.apply_chat_template([{"role":"user","content":s}],tokenize=True,add_generation_prompt=True))
 except:return len(tk(s,add_special_tokens=False)["input_ids"])
res={"version":"U21 dual-MT medical-content consensus","stress":sa,"stress_accept_rate":sum(x["accepted"] for x in sa)/len(sa),"models":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=used=0
  for i,r in enumerate(rows):
   a=ap(r);e=ep(r)
   if valid[i] and facts(a)==facts(e) and cc(tk,e)<cc(tk,a):g=e;used+=1
   else:g=a
   B+=cc(tk,a);T+=cc(tk,g)
  res["models"][name]={"chat_reduction_pct":100*(B-T)/B,"accepted_cases":used,"n":len(rows),"passes30":100*(B-T)/B>=30}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u21_dual_consensus.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U21="+json.dumps(res,ensure_ascii=False),flush=True)
