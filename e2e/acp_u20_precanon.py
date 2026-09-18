#!/usr/bin/env python3
import re,json,os,csv,io,urllib.request,random,gc
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM

SEED=211
random.seed(SEED);torch.manual_seed(SEED)
MT="HPLT/translate-ar-en-v1.0-hplt_opus"
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
MAP=[
("استبعاد الحمل","ruling out pregnancy"),("لا تتجاوز","do not exceed"),("لا يعاني المريض من","patient does not have"),("لا يعاني من","does not have"),
("لا توجد","there is no"),("لا يوجد","there is no"),("ليس لدى","does not have"),("لم يحدث","did not occur"),("ينفي","denies"),
("بدون","without"),("دون","without"),("لا تعط","do not give"),
("الجانب الأيسر","left side"),("الجانب الأيمن","right side"),("اليسرى","left"),("اليمنى","right"),("الأيسر","left"),("الأيمن","right"),
("الحمل","pregnancy"),("حامل","pregnant"),("حساسية","allergy"),("الخاصرة","flank"),("دوخة","dizziness"),("الدوخة","dizziness"),
("الهواء المحيط","ambient air"),("الكرياتينين","creatinine"),("تشبع الأكسجين","SpO2"),("ضغط الدم","BP"),
("سكر الدم","blood glucose"),("السكر التراكمي","HbA1c"),("الهيموغلوبين","hemoglobin"),("البوتاسيوم","potassium"),("الصوديوم","sodium"),
("الأنسولين","insulin"),("الانسولين","insulin"),("الأموكسيسيلين","amoxicillin"),("الوارفارين","warfarin"),("حمى","fever"),("الحمى","fever"),("الحمّى","fever"),
("ارتفاع ضغط الدم","HTN"),("مرض السكري","diabetes"),("داء السكري","diabetes"),("مرض الكلى المزمن","CKD"),
("احتشاء عضلة القلب","MI"),("الرجفان الأذيني","AF"),("مرض الانسداد الرئوي المزمن","COPD"),
("التهاب المسالك البولية","UTI"),("التصوير المقطعي المحوسب","CT"),("التصوير بالرنين المغناطيسي","MRI"),
("تخطيط القلب الكهربائي","ECG"),("مؤشر كتلة الجسم","BMI")
]
MAP=sorted(MAP,key=lambda x:len(x[0]),reverse=True)
VAL=re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?|units?))?(?![A-Za-z])",re.I)
NEG_AR=re.compile(r"(?<![\w\u0600-\u06ff])(?:لا|ليس|ليست|لم|لن|دون|بدون|ينفي)(?![\w\u0600-\u06ff])")
LEFT_RE=re.compile(r"(?:الأيسر|اليسرى|يسار|\bleft\b)",re.I);RIGHT_RE=re.compile(r"(?:الأيمن|اليمنى|يمين|\bright\b)",re.I)
def precanon(t):
    cur=t
    occupied=[]
    # literal replacement longest first naturally prevents most overlap
    for a,b in MAP:
        cur=cur.replace(a,b)
    return cur
def canon_val(v):
    x=re.sub(r"\s+","",v.lower()).replace("وحدات","unit").replace("وحدة","unit").replace("units","unit")
    return x
def facts(t):
    s=" "+t.lower()+" ";f=set()
    if NEG_AR.search(t) or any(x in s for x in [" no "," not "," without "," denies ","does not","did not"]):f.add("NEG")
    if LEFT_RE.search(t):f.add("LEFT")
    if RIGHT_RE.search(t):f.add("RIGHT")
    groups={"PREG":["حامل","الحمل","pregnant","pregnancy"],"ALLERGY":["حساسية","allergy"],"RULEOUT":["استبعاد","rule out","ruling out"],
    "FLANK":["الخاصرة","flank"],"DIZZY":["دوخة","dizziness"],"CREAT":["الكرياتينين","creatinine"],"AMBIENT":["الهواء المحيط","ambient air","room air"],
    "BP":["ضغط الدم"," bp "],"SPO2":["تشبع الأكسجين","spo2"],"GLU":["سكر الدم","blood glucose","blood sugar"],
    "HBA1C":["السكر التراكمي","hba1c"],"INS":["الأنسولين","الانسولين","insulin"],"FEVER":["حمى","الحمى","الحمّى","fever"]}
    for k,vs in groups.items():
        if any(v in s for v in vs):f.add(k)
    for m in VAL.finditer(t):f.add("VAL:"+canon_val(m.group(0)))
    return f
tok=AutoTokenizer.from_pretrained(MT,trust_remote_code=True);mt=AutoModelForSeq2SeqLM.from_pretrained(MT,dtype="auto",low_cpu_mem_usage=True,trust_remote_code=True);mt.eval()
@torch.no_grad()
def translate(texts):
    src=[precanon(x) for x in texts];out=[]
    for i in range(0,len(src),12):
        x=tok(src[i:i+12],return_tensors="pt",padding=True,truncation=True,max_length=256)
        g=mt.generate(**x,max_new_tokens=220,num_beams=1);out+=tok.batch_decode(g,skip_special_tokens=True)
    return list(zip(src,out))
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
st=translate(STRESS);audit=[];okn=0
for src,(pre,out) in zip(STRESS,st):
    ok=facts(src)==facts(out);okn+=ok
    audit.append({"source":src,"precanonical":pre,"output":out,"fact_ok":ok,"missing":sorted(facts(src)-facts(out)),"added":sorted(facts(out)-facts(src))})

raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace");rows=list(csv.DictReader(io.StringIO(raw)));random.Random(SEED).shuffle(rows);rows=rows[:100]
segs=[];slot=[]
for i,r in enumerate(rows):
    segs.append(r["Question"]);slot.append((i,"q",r["Question"]))
    for L in "ABCDEF":
        v=(r.get("Option "+L) or "").strip()
        if v:segs.append(v);slot.append((i,L,v))
tr=translate(segs);valid=[True]*len(rows)
for (pre,out),(i,k,orig) in zip(tr,slot):
    if facts(orig)!=facts(out):out=orig;valid[i]=False
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
def cc(tk,s):
    try:return len(tk.apply_chat_template([{"role":"user","content":s}],tokenize=True,add_generation_prompt=True))
    except:return len(tk(s,add_special_tokens=False)["input_ids"])

res={"version":"U20 pre-canonicalized clinical MT","stress_fact_integrity":okn/len(STRESS),"stress":audit,"models":{}}
for name,mid in MODELS:
    try:
        tk2=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=used=0
        for i,r in enumerate(rows):
            a=ap(r);e=ep(r)
            if valid[i] and facts(a)==facts(e) and cc(tk2,e)<cc(tk2,a):g=e;used+=1
            else:g=a
            B+=cc(tk2,a);T+=cc(tk2,g)
        res["models"][name]={"chat_reduction_pct":100*(B-T)/B,"accepted_cases":used,"n":len(rows),"passes30":100*(B-T)/B>=30}
    except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u20_precanon.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U20="+json.dumps(res,ensure_ascii=False),flush=True)
