#!/usr/bin/env python3
import csv,io,json,os,re,urllib.request,random,gc
import torch
from transformers import AutoTokenizer,AutoModelForCausalLM

SEED=111
random.seed(SEED);torch.manual_seed(SEED)
MEDARA="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MEDARABIQ_MCQ="https://raw.githubusercontent.com/nyuad-cai/MedArabiQ/main/datasets/multiple-choice-questions.csv"
MEDARABIQ_PD="https://raw.githubusercontent.com/nyuad-cai/MedArabiQ/main/datasets/patient-doctor-qa.csv"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4-mini","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
BEH=[("Qwen3","Qwen/Qwen3-0.6B",32),("Llama3.2","unsloth/Llama-3.2-1B-Instruct",24),("Gemma3","unsloth/gemma-3-1b-it",24)]

# Exact, manually reviewed phrase-level semantics only.
PHRASES=[
("كل ما يلي صحيح ما عدا","All true EXCEPT"),("كل ما يلي صحيح عدا","All true EXCEPT"),
("كل ما هو آت صحيح عن","All true about"),("كل ما هو آت صحيح","All true"),
("كل مما يلي صحيح ما عدا","All true EXCEPT"),("ما يلي صحيح ما عدا","All true EXCEPT"),
("ما يلي صحيح عدا","All true EXCEPT"),("أي مما يلي","Which"),("اي مما يلي","Which"),
("اختر الإجابة الصحيحة","Choose correct"),("اختر الاجابة الصحيحة","Choose correct"),
("اختر الإجابة الخاطئة","Choose false"),("اختر الاجابة الخاطئة","Choose false"),
("كل ما سبق","all above"),("لا شيء مما سبق","none above"),("لا شئ مما سبق","none above"),
("ما سبق صحيح","above true"),("ما سبق خطأ","above false"),("ما سبق خاطئ","above false"),
("من عوامل الخطورة","RF:"),("عوامل الخطورة","RF:"),("عوامل الخطر","RF:"),
("تشمل الأعراض","Sx:"),("تشمل أعراض","Sx:"),("من الأعراض","Sx:"),
("التاريخ المرضي السابق","PMH:"),("التاريخ المرضي","Hx:"),("التاريخ الطبي","Hx:"),
("الأدوية الحالية","Meds:"),("العلاجات الحالية","Meds:"),
("نتائج المختبر","Labs:"),("نتائج التحاليل","Labs:"),("التحاليل المخبرية","Labs:"),
("يعاني المريض من","Pt has"),("يعاني من","has"),("تعاني المريضة من","Pt has"),
("يشكو المريض من","Pt c/o"),("يشكو من","c/o"),("تشكو المريضة من","Pt c/o"),
("لا يعاني المريض من","Pt no"),("لا يعاني من","no"),("لا توجد","no"),("لا يوجد","no"),
("وجود تاريخ عائلي","FHx"),("تاريخ عائلي","FHx"),
("يؤدي إلى","causes"),("يؤدي الى","causes"),("مما يؤدي إلى","→"),("مما يؤدي الى","→"),
("بسبب","due to"),("نتيجة","due to"),("بهدف","to"),("من خلال","via"),
("على مدار الساعة","24/7"),("في الوقت الحالي","now"),
("ارتفاع ضغط الدم","HTN"),("فرط ضغط الدم","HTN"),("ضغط الدم","BP"),
("داء السكري من النوع الأول","T1DM"),("السكري من النوع الأول","T1DM"),
("داء السكري من النوع الثاني","T2DM"),("السكري من النوع الثاني","T2DM"),
("مرض السكري","diabetes"),("داء السكري","diabetes"),("السكري","diabetes"),
("الهيموغلوبين السكري","HbA1c"),("السكر التراكمي","HbA1c"),
("الحماض الكيتوني السكري","DKA"),("مرض الكلى المزمن","CKD"),("إصابة الكلى الحادة","AKI"),
("التهاب المسالك البولية","UTI"),("عدوى المسالك البولية","UTI"),
("تعداد الدم الكامل","CBC"),("تخطيط القلب الكهربائي","ECG"),("تخطيط القلب","ECG"),
("أشعة الصدر","CXR"),("التصوير المقطعي المحوسب","CT"),("الأشعة المقطعية","CT"),
("التصوير بالرنين المغناطيسي","MRI"),("الرنين المغناطيسي","MRI"),
("تشبع الأكسجين","SpO2"),("مؤشر كتلة الجسم","BMI"),
("مرض الانسداد الرئوي المزمن","COPD"),("احتشاء عضلة القلب","MI"),
("الرجفان الأذيني","AF"),("مرض الشرايين التاجية","CAD"),("الخثار الوريدي العميق","DVT"),("الانصمام الرئوي","PE"),
("فيروس نقص المناعة البشرية","HIV"),("التهاب الكبد الوبائي ب","HBV"),("التهاب الكبد الوبائي سي","HCV"),
("التهاب الكبد بي","HBV"),("التهاب الكبد سي","HCV"),("سكري الحمل","GDM"),
("البروتين الدهني مرتفع الكثافة","HDL"),("البروتين الدهني منخفض الكثافة","LDL"),("الدهون الثلاثية","TG"),
("مرض الشرايين التاجية","CAD"),("النوبة القلبية","MI"),
("ضيق التنفس","dyspnea"),("صعوبة التنفس","dyspnea"),("ألم الصدر","chest pain"),
("العلامات الحيوية","vitals"),("الرعاية الصحية الأولية","primary care"),
("فقدان الوزن","weight loss"),("التهاب البنكرياس","pancreatitis"),
("تليف الكبد","cirrhosis"),("تشمع الكبد","cirrhosis"),
("فقر الدم","anemia"),("الأنيميا","anemia"),
]
WORDS={
"القلب":"heart","قلب":"heart","الكبد":"liver","كبد":"liver","الكلية":"kidney","كلية":"kidney","الكلى":"kidneys",
"الرئة":"lung","رئة":"lung","البنكرياس":"pancreas","بنكرياس":"pancreas","الطحال":"spleen","طحال":"spleen",
"الرحم":"uterus","رحم":"uterus","المثانة":"bladder","مثانة":"bladder","المبيض":"ovary","مبيض":"ovary",
"الشريان":"artery","شريان":"artery","الوريد":"vein","وريد":"vein","العصب":"nerve","عصب":"nerve",
"العضلة":"muscle","عضلة":"muscle","العظم":"bone","عظم":"bone","المفصل":"joint","مفصل":"joint",
"الرباط":"ligament","رباط":"ligament","الوتر":"tendon","وتر":"tendon","الغضروف":"cartilage","غضروف":"cartilage",
"الظهارة":"epithelium","ظهارة":"epithelium","النسيج":"tissue","نسيج":"tissue","الخلية":"cell","خلية":"cell",
"الغدة":"gland","غدة":"gland","الهرمون":"hormone","هرمون":"hormone","الصمام":"valve","صمام":"valve",
"البطين":"ventricle","بطين":"ventricle","الأذين":"atrium","أذين":"atrium",
"السرطان":"cancer","سرطان":"cancer","الورم":"tumor","ورم":"tumor","العدوى":"infection","عدوى":"infection",
"السمنة":"obesity","البدانة":"obesity","الحمى":"fever","الحمّى":"fever","الغثيان":"nausea","غثيان":"nausea",
"القيء":"vomiting","قيء":"vomiting","الصداع":"headache","صداع":"headache","الأنسولين":"insulin","الانسولين":"insulin",
"الكوليسترول":"cholesterol","كوليسترول":"cholesterol","دوخة":"dizziness","الدوخة":"dizziness",
"الخاصرة":"flank","خاصرة":"flank","الكرياتينين":"creatinine","كرياتينين":"creatinine","الهواء المحيط":"ambient air"
}
# Critical modifiers remain Arabic exactly and block nearby word-level replacement.
CRIT=set("""لا ليس ليست لم لن دون بدون ينفي تنفي نفي عدم قبل بعد منذ خلال الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار جرعة جرعات حامل الحمل حساسية تحسس استبعاد أقل اقل أكثر اكثر فوق تحت""".split())
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]+");DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
def fetch(url):
 raw=urllib.request.urlopen(url,timeout=120).read().decode("utf-8-sig","replace");return list(csv.DictReader(io.StringIO(raw)))
def medara_prompt(r):
 z=["السؤال: "+r["Question"]]
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:z.append(f"{L}) {v}")
 z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"];return "\n".join(z)
def medarabiq_mcq(r):return r.get("Question","")
def pd_text(r):return r.get("Question_description","")
def tc(tk,s):return len(tk(s,add_special_tokens=False)["input_ids"])
def cc(tk,s):
 try:return len(tk.apply_chat_template([{"role":"user","content":s}],tokenize=True,add_generation_prompt=True))
 except:return tc(tk,s)
def protected(t):
 ms=list(AR.finditer(t));w=[m.group(0) for m in ms];p=set()
 for i,x in enumerate(w):
  if x in CRIT:
   p.update(range(max(0,i-2),min(len(w),i+3)))
 for m in re.finditer(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?|\b(?:mg|mL|mmHg|bpm|g/dL|mg/dL|mmol/L)\b|%",t,re.I):
  for i,z in enumerate(ms):
   if abs(z.start()-m.start())<24:p.add(i)
 return ms,w,p
def transform(t,tk):
 base=tc(tk,t);cands=[]
 # phrase exact matches, longest first
 for old,new in PHRASES:
  for m in re.finditer(re.escape(old),t):
   a=max(0,m.start()-40);b=min(len(t),m.end()+40);sv=tc(tk,t[a:b])-tc(tk,t[a:m.start()]+new+t[m.end():b])
   if sv>0:cands.append((m.start(),m.end(),new,sv,len(old),True))
 ms,w,p=protected(t)
 for i,x in enumerate(w):
  if i in p or x not in WORDS:continue
  m=ms[i];new=WORDS[x];a=max(0,m.start()-40);b=min(len(t),m.end()+40);sv=tc(tk,t[a:b])-tc(tk,t[a:m.start()]+new+t[m.end():b])
  if sv>0:cands.append((m.start(),m.end(),new,sv,len(x),False))
 cands.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
 for x in cands:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];q=0
 for s,e,new,_,_,_ in sel:o += [t[q:s],new];q=e
 o.append(t[q:]);v="".join(o)
 if tc(tk,v)>base:return t,0
 return v,len(sel)
def choice(model,tk,p,labels):
 ids=torch.tensor([tk.apply_chat_template([{"role":"user","content":p}],tokenize=True,add_generation_prompt=True) if hasattr(tk,"apply_chat_template") else tk(p,return_tensors="pt")["input_ids"][0].tolist()])
 with torch.no_grad():z=model(input_ids=ids,use_cache=False).logits[0,-1].float()
 sc={}
 for L in labels:
  vals=[]
  for x in (L," "+L):
   ii=tk(x,add_special_tokens=False)["input_ids"]
   if len(ii)==1:vals.append(float(z[ii[0]]))
  sc[L]=max(vals) if vals else -1e9
 return max(sc,key=sc.get)
ma=fetch(MEDARA);mq=fetch(MEDARABIQ_MCQ);pd=fetch(MEDARABIQ_PD)
res={"version":"U10 Clinical Telegraph Language","models":{},"behavior":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);x={}
  for ds,rows,fn,lim in [("MedAraBench",ma,medara_prompt,1200),("MedArabiQ_MCQ",mq,medarabiq_mcq,1000),("MedArabiQ_patient",pd,pd_text,1000)]:
   B=T=rep=0
   for r in rows[:lim]:
    p=fn(r);v,k=transform(p,tk);B+=tc(tk,p);T+=tc(tk,v);rep+=k
   x[ds]={"content_pct":100*(B-T)/B if B else 0,"replacements":rep}
  res["models"][name]=x
 except Exception as e:res["models"][name]={"error":repr(e)}

os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u10_ctl_tokens.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U10_CTL_TOKENS="+json.dumps(res["models"],ensure_ascii=False),flush=True)
