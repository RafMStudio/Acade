#!/usr/bin/env python3
import re,json,os,torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
MODEL="HPLT/translate-ar-en-v1.0-hplt_opus"
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
VAL=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?))?(?![A-Za-z])",re.I)
def facts(t):
 s=" "+t.lower()+" ";f=set()
 groups={
"NEG":[" لا ","ليس","ليست","لم ","لن ","دون","بدون","ينفي"," no ","not ","without","denies","does not","did not"],
"LEFT":["الأيسر","اليسرى"," left"],"RIGHT":["الأيمن","اليمنى"," right"],
"PREG":["حامل","الحمل","pregnant","pregnancy"],"ALLERGY":["حساسية","allergy"],"RULEOUT":["استبعاد","rule out","ruling out","exclude pregnancy"],
"FLANK":["الخاصرة","flank"],"DIZZY":["دوخة","dizziness"],"CREAT":["الكرياتينين","creatinine"],"AMBIENT":["الهواء المحيط","ambient air","room air"],
"BP":["ضغط الدم","blood pressure"],"SPO2":["تشبع الأكسجين","oxygen saturation"],"GLU":["سكر الدم","blood sugar","blood glucose"],
"HBA1C":["السكر التراكمي","hba1c"],"INS":["الأنسولين","الانسولين","insulin"],"FEVER":["حمى","الحمى","الحمّى","fever"]}
 for k,vs in groups.items():
  if any(v in s for v in vs):f.add(k)
 for m in VAL.finditer(t):f.add("VAL:"+re.sub(r"\s+","",m.group(0).lower()))
 return f
tok=AutoTokenizer.from_pretrained(MODEL,trust_remote_code=True);m=AutoModelForSeq2SeqLM.from_pretrained(MODEL,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);m.eval()
out=[]
for i in range(0,len(CASES),12):
 x=tok(CASES[i:i+12],return_tensors="pt",padding=True,truncation=True,max_length=160)
 with torch.no_grad():g=m.generate(**x,max_new_tokens=160,num_beams=1)
 out+=tok.batch_decode(g,skip_special_tokens=True)
audit=[];p=0
for a,b in zip(CASES,out):
 fa,fb=facts(a),facts(b);ok=fa==fb;p+=ok
 audit.append({"source":a,"output":b,"fact_ok":ok,"missing":sorted(fa-fb),"added":sorted(fb-fa)})
res={"model":MODEL,"n":len(CASES),"fact_integrity_rate":p/len(CASES),"audit":audit}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u15_hplt.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U15="+json.dumps(res,ensure_ascii=False),flush=True)
