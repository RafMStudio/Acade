#!/usr/bin/env python3
import json,re,os,torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
MT="facebook/nllb-200-distilled-600M"
CASES=[
{"t":"لا يعاني المريض من ألم في الصدر.","neg":1},
{"t":"لا توجد علامات لالتهاب رئوي.","neg":1},
{"t":"المريض بدون حساسية معروفة للأدوية.","neg":1},
{"t":"لم يحدث نزيف بعد العملية.","neg":1,"after":1},
{"t":"ليس لدى المريض تاريخ سابق للسكتة الدماغية.","neg":1},
{"t":"ينفي المريض وجود ضيق في التنفس.","neg":1},
{"t":"لا يوجد ألم في الجانب الأيسر من الصدر.","neg":1,"left":1},
{"t":"لا يوجد ضعف في الطرف الأيمن.","neg":1,"right":1},
{"t":"ألم في الركبة اليسرى منذ ثلاثة أيام.","left":1},
{"t":"تورم في الساق اليمنى.","right":1},
{"t":"ضعف في الذراع اليسرى بعد السكتة.","left":1,"after":1},
{"t":"كسر في عظم الفخذ الأيمن.","right":1},
{"t":"ألم في الخاصرة اليمنى دون حمى.","right":1,"neg":1},
{"t":"الكتلة موجودة في الثدي الأيسر.","left":1},
{"t":"أعط المريض 500 mg من الأموكسيسيلين.","nums":["500"],"units":["mg"]},
{"t":"يتناول المريض 5 mg من الوارفارين يوميا.","nums":["5"],"units":["mg"]},
{"t":"أعط 20 mL من المحلول.","nums":["20"],"units":["mL"]},
{"t":"تشبع الأكسجين 92%.","nums":["92"],"units":["%"]},
{"t":"ضغط الدم 160/100 mmHg.","nums":["160","100"],"units":["mmHg"]},
{"t":"معدل النبض 120 bpm.","nums":["120"],"units":["bpm"]},
{"t":"درجة الحرارة 39.2 °C.","nums":["39.2"],"units":["°C"]},
{"t":"سكر الدم 45 mg/dL.","nums":["45"],"units":["mg/dL"]},
{"t":"جرعة الأنسولين 10 وحدات قبل العشاء.","nums":["10"],"before":1},
{"t":"أعط 2.5 mg كل 12 ساعة.","nums":["2.5","12"],"units":["mg"]},
{"t":"بدأ الألم قبل ساعتين.","before":1},
{"t":"حدث القيء بعد تناول الدواء.","after":1},
{"t":"يؤخذ الدواء قبل الطعام.","before":1},
{"t":"يؤخذ الدواء بعد الطعام.","after":1},
{"t":"ظهرت الأعراض بعد الجراحة بيومين.","after":1},
{"t":"أوقف الدواء قبل العملية بثلاثة أيام.","before":1},
{"t":"لا تعط الدواء قبل استبعاد الحمل.","neg":1,"before":1},
{"t":"لا تعط جرعة إضافية بعد 6 ساعات.","neg":1,"after":1,"nums":["6"]},
{"t":"ضغط الدم 90/60 mmHg ولا توجد دوخة.","nums":["90","60"],"units":["mmHg"],"neg":1},
{"t":"تشبع الأكسجين 88% في الهواء المحيط.","nums":["88"],"units":["%"]},
{"t":"المريض يتناول 1000 mg ميتفورمين مرتين يوميا.","nums":["1000"],"units":["mg"]},
{"t":"المريضة حامل في الأسبوع 32.","nums":["32"]},
{"t":"الهيموغلوبين 7.5 g/dL.","nums":["7.5"],"units":["g/dL"]},
{"t":"الكرياتينين 2.1 mg/dL.","nums":["2.1"],"units":["mg/dL"]},
{"t":"البوتاسيوم 6.2 mmol/L.","nums":["6.2"],"units":["mmol/L"]},
{"t":"الصوديوم 128 mmol/L.","nums":["128"],"units":["mmol/L"]},
{"t":"لا يوجد نزيف في العين اليمنى.","neg":1,"right":1},
{"t":"لا توجد كتلة في الثدي الأيسر.","neg":1,"left":1},
{"t":"ألم في الجانب الأيمن بدأ بعد السقوط.","right":1,"after":1},
{"t":"ضعف الجانب الأيسر بدأ قبل ساعة.","left":1,"before":1},
{"t":"أعط 0.5 mL في الذراع اليسرى.","nums":["0.5"],"units":["mL"],"left":1},
{"t":"لا تتجاوز الجرعة 4 g خلال 24 ساعة.","neg":1,"nums":["4","24"],"units":["g"]},
{"t":"الهدف إبقاء الضغط أقل من 130/80 mmHg.","nums":["130","80"],"units":["mmHg"]},
{"t":"السكر التراكمي 8.4% والهدف أقل من 7%.","nums":["8.4","7"],"units":["%"]}
]
def norm(x):return x.lower().replace("℃","°c")
def has_neg(x):return any(w in norm(x) for w in [" no ","not ","without","denies","denied","absence","absent","negative for","doesn't","does not","did not","never","none"])
def tr():
 tok=AutoTokenizer.from_pretrained(MT,src_lang="arb_Arab");m=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True);m.eval();bos=tok.convert_tokens_to_ids("eng_Latn")
 src=[c["t"] for c in CASES];out=[]
 for i in range(0,len(src),12):
  x=tok(src[i:i+12],return_tensors="pt",padding=True,truncation=True,max_length=128)
  with torch.no_grad():g=m.generate(**x,forced_bos_token_id=bos,max_new_tokens=128,num_beams=1)
  out+=tok.batch_decode(g,skip_special_tokens=True)
 return out
outs=tr();checks=[];tot={"numbers":[0,0],"units":[0,0],"negation":[0,0],"laterality":[0,0],"temporal":[0,0]}
for c,o in zip(CASES,outs):
 fail=[];lo=norm(" "+o+" ")
 for n in c.get("nums",[]):
  tot["numbers"][1]+=1
  if n in o:tot["numbers"][0]+=1
  else:fail.append("number:"+n)
 for u in c.get("units",[]):
  tot["units"][1]+=1
  variants={u.lower(),u.lower().replace("°","")}
  if any(v in lo for v in variants):tot["units"][0]+=1
  else:fail.append("unit:"+u)
 if c.get("neg"):
  tot["negation"][1]+=1
  if has_neg(" "+o+" "):tot["negation"][0]+=1
  else:fail.append("negation")
 if c.get("left"):
  tot["laterality"][1]+=1
  if "left" in lo:tot["laterality"][0]+=1
  else:fail.append("left")
 if c.get("right"):
  tot["laterality"][1]+=1
  if "right" in lo:tot["laterality"][0]+=1
  else:fail.append("right")
 if c.get("before"):
  tot["temporal"][1]+=1
  if "before" in lo:tot["temporal"][0]+=1
  else:fail.append("before")
 if c.get("after"):
  tot["temporal"][1]+=1
  if "after" in lo:tot["temporal"][0]+=1
  else:fail.append("after")
 checks.append({"source":c["t"],"translation":o,"failures":fail})
res={"translator":MT,"n_cases":len(CASES),"summary":{k:{"passed":v[0],"total":v[1],"rate":v[0]/v[1] if v[1] else None} for k,v in tot.items()},"failed_cases":[x for x in checks if x["failures"]],"all_cases":checks}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u9_invariants.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U9_INVARIANTS="+json.dumps(res,ensure_ascii=False),flush=True)
