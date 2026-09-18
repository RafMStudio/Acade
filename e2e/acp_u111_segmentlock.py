#!/usr/bin/env python3
import re,json,os,torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM,AutoTokenizer as AT
MT="facebook/nllb-200-distilled-600M"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct")]
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
LOCK=[
("استبعاد الحمل","ruling out pregnancy"),("لا يعاني","does not have"),("لا توجد","there is no"),("لا يوجد","there is no"),("ليس لدى","does not have"),("لم يحدث","did not occur"),
("ينفي","denies"),("بدون","without"),("دون","without"),("لا تعط","do not give"),("لا تتجاوز","do not exceed"),
("الجانب الأيسر","left side"),("الجانب الأيمن","right side"),("اليسرى","left"),("اليمنى","right"),("الأيسر","left"),("الأيمن","right"),
("قبل","before"),("بعد","after"),("منذ","for"),("حامل","pregnant"),("الحمل","pregnancy"),("حساسية","allergy"),
("الخاصرة","flank"),("دوخة","dizziness"),("الهواء المحيط","ambient air"),("الكرياتينين","creatinine"),
("تشبع الأكسجين","oxygen saturation"),("ضغط الدم","blood pressure"),("سكر الدم","blood glucose"),("السكر التراكمي","HbA1c"),
("الأنسولين","insulin"),("الأموكسيسيلين","amoxicillin"),("الوارفارين","warfarin"),("الهيموغلوبين","hemoglobin"),
("البوتاسيوم","potassium"),("الصوديوم","sodium"),("حمى","fever"),("الحمى","fever"),("الحمّى","fever")
]
LOCK=sorted(LOCK,key=lambda x:len(x[0]),reverse=True)
NUM=re.compile(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?))?",re.I)
def spans(text):
 c=[]
 for m in NUM.finditer(text):c.append((m.start(),m.end(),m.group(0)))
 for ar,en in LOCK:
  for m in re.finditer(re.escape(ar),text):c.append((m.start(),m.end(),en))
 c.sort(key=lambda x:(x[0],-(x[1]-x[0])));sel=[]
 for x in c:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 return sorted(sel)
tok=AutoTokenizer.from_pretrained(MT,src_lang="arb_Arab");mod=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True);mod.eval();bos=tok.convert_tokens_to_ids("eng_Latn")
def translate_segments(text):
 sp=spans(text);parts=[];p=0;to_translate=[];slots=[]
 for s,e,val in sp:
  seg=text[p:s].strip()
  if seg:slots.append(len(parts));parts.append(None);to_translate.append(seg)
  parts.append(val);p=e
 seg=text[p:].strip()
 if seg:slots.append(len(parts));parts.append(None);to_translate.append(seg)
 outs=[]
 for i in range(0,len(to_translate),16):
  x=tok(to_translate[i:i+16],return_tensors="pt",padding=True,truncation=True,max_length=100)
  with torch.no_grad():g=mod.generate(**x,forced_bos_token_id=bos,max_new_tokens=100,num_beams=1)
  outs+=tok.batch_decode(g,skip_special_tokens=True)
 for idx,out in zip(slots,outs):parts[idx]=out.strip()
 return " ".join(x for x in parts if x).replace(" .",".")
outs=[translate_segments(x) for x in CASES]
audit=[];passed=0
for src,out in zip(CASES,outs):
 vals=[v for _,_,v in spans(src)];missing=[v for v in vals if v.lower() not in out.lower()];ok=not missing;passed+=ok;audit.append({"source":src,"output":out,"locked":vals,"missing":missing,"pass":ok})
res={"version":"U11.1 segmented slot-lock","cases":len(CASES),"slot_integrity_rate":passed/len(CASES),"audit":audit,"tokenizers":{}}
for name,mid in MODELS:
 try:
  tk=AT.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=0
  for a,b in zip(CASES,outs):B+=len(tk(a,add_special_tokens=False)["input_ids"]);T+=len(tk(b,add_special_tokens=False)["input_ids"])
  res["tokenizers"][name]={"reduction_pct":100*(B-T)/B,"baseline":B,"segmented":T}
 except Exception as e:res["tokenizers"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u111_segmentlock.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U111="+json.dumps(res,ensure_ascii=False),flush=True)
