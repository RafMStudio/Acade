#!/usr/bin/env python3
import re,json,os
from transformers import AutoTokenizer

MODELS=[
("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),
("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),
("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4-mini","microsoft/Phi-4-mini-instruct"),
("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
CASES=[
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
PHRASES=[
("ارتفاع ضغط الدم","HTN"),("ضغط الدم","BP"),("مرض السكري","diabetes"),("داء السكري","diabetes"),("السكري","diabetes"),
("الهيموغلوبين السكري","HbA1c"),("السكر التراكمي","HbA1c"),("تشبع الأكسجين","SpO2"),("سكر الدم","glucose"),
("تخطيط القلب الكهربائي","ECG"),("التصوير المقطعي المحوسب","CT"),("التصوير بالرنين المغناطيسي","MRI"),
("لا يعاني المريض من","Pt no"),("لا يعاني من","no"),("لا توجد","no"),("لا يوجد","no"),
("يعاني المريض من","Pt has"),("يعاني من","has"),("يشكو المريض من","Pt c/o"),("يشكو من","c/o"),
("ضيق التنفس","dyspnea"),("صعوبة التنفس","dyspnea"),("ألم الصدر","chest pain"),
("من عوامل الخطورة","RF:"),("عوامل الخطورة","RF:"),("تشمل الأعراض","Sx:"),("تشمل أعراض","Sx:"),
("التاريخ المرضي","Hx:"),("التاريخ الطبي","Hx:"),("الأدوية الحالية","Meds:"),("نتائج المختبر","Labs:")
]
WORDS={"القلب":"heart","الكبد":"liver","الكلية":"kidney","الكلى":"kidneys","الرئة":"lung","البنكرياس":"pancreas","الرحم":"uterus",
"الشريان":"artery","الوريد":"vein","العصب":"nerve","العضلة":"muscle","العظم":"bone","السرطان":"cancer","السمنة":"obesity",
"البدانة":"obesity","الحمى":"fever","الحمّى":"fever","الغثيان":"nausea","القيء":"vomiting","الأنسولين":"insulin",
"دوخة":"dizziness","الدوخة":"dizziness","الخاصرة":"flank","الكرياتينين":"creatinine","الهواء":"air"}
CRIT=set("""لا ليس ليست لم لن دون بدون ينفي تنفي نفي عدم قبل بعد منذ خلال الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار جرعة جرعات حامل الحمل حساسية تحسس استبعاد أقل اقل أكثر اكثر فوق تحت""".split())
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
NUMUNIT=re.compile(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?))?",re.I)

def tc(tk,s):return len(tk(s,add_special_tokens=False)["input_ids"])
def protected(t):
 ms=list(AR.finditer(t));w=[m.group(0) for m in ms];p=set()
 for i,x in enumerate(w):
  if x in CRIT:p.update(range(max(0,i-2),min(len(w),i+3)))
 for m in NUMUNIT.finditer(t):
  for i,z in enumerate(ms):
   if abs(z.start()-m.start())<24:p.add(i)
 return ms,w,p
def transform(t,tk):
 base=tc(tk,t);c=[]
 for old,new in PHRASES:
  for m in re.finditer(re.escape(old),t):
   a=max(0,m.start()-35);b=min(len(t),m.end()+35)
   sv=tc(tk,t[a:b])-tc(tk,t[a:m.start()]+new+t[m.end():b])
   if sv>0:c.append((m.start(),m.end(),new,sv,len(old)))
 ms,w,p=protected(t)
 for i,x in enumerate(w):
  if i in p or x not in WORDS:continue
  m=ms[i];new=WORDS[x];a=max(0,m.start()-35);b=min(len(t),m.end()+35)
  sv=tc(tk,t[a:b])-tc(tk,t[a:m.start()]+new+t[m.end():b])
  if sv>0:c.append((m.start(),m.end(),new,sv,len(x)))
 c.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
 for x in c:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];p0=0
 for s,e,new,_,_ in sel:o += [t[p0:s],new];p0=e
 o.append(t[p0:]);v="".join(o)
 return (v if tc(tk,v)<=base else t),len(sel)

# Canonical fact extractor recognizes both Arabic source and compressed English forms.
CANON={
"NEG":[" لا ","ليس","ليست","لم ","لن ","دون","بدون","ينفي"," no ","pt no"],
"LEFT":["الأيسر","اليسرى","يسار"," left"],"RIGHT":["الأيمن","اليمنى","يمين"," right"],
"BEFORE":["قبل"," before"],"AFTER":["بعد"," after"],"PREG":["حامل","الحمل"," pregnant","pregnancy"],
"ALLERGY":["حساسية","تحسس"," allergy"],"RULEOUT":["استبعاد","ruling out","rule out"],
"FLANK":["الخاصرة"," flank"],"DIZZY":["دوخة"," dizziness"],"CREAT":["الكرياتينين"," creatinine"],
"AMBIENT":["الهواء المحيط","ambient air"],"BP":["ضغط الدم"," bp","blood pressure"],"SPO2":["تشبع الأكسجين","spo2","oxygen saturation"],
"GLUCOSE":["سكر الدم"," glucose","blood glucose"],"HBA1C":["السكر التراكمي","hba1c"],
"INSULIN":["الأنسولين","الانسولين"," insulin"],"FEVER":["حمى","الحمى","الحمّى"," fever"]
}
def facts(t):
 s=" "+t.lower()+" ";f=set()
 for k,vs in CANON.items():
  if any(v.lower() in s for v in vs):f.add(k)
 for m in NUMUNIT.finditer(t):f.add("VAL:"+re.sub(r"\s+","",m.group(0).lower()))
 # explicit comparator meaning
 if "أقل" in t or "اقل" in t or " less " in s or "below" in s:f.add("LT")
 if "أكثر" in t or "اكثر" in t or " more " in s or "above" in s:f.add("GT")
 return f

res={"version":"U12 deterministic CTL fact-equality audit","models":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);passes=0;details=[];B=T=0
  for src in CASES:
   out,k=transform(src,tk);a,b=facts(src),facts(out);ok=a==b;passes+=ok;B+=tc(tk,src);T+=tc(tk,out)
   if not ok:details.append({"source":src,"output":out,"before":sorted(a),"after":sorted(b),"missing":sorted(a-b),"added":sorted(b-a)})
  res["models"][name]={"fact_integrity_rate":passes/len(CASES),"failed":len(CASES)-passes,"reduction_pct":100*(B-T)/B,"failures":details}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u12_fact_audit.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U12_FACTS="+json.dumps(res,ensure_ascii=False),flush=True)
