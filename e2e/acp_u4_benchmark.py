#!/usr/bin/env python3
import csv, io, json, os, re, random, statistics as st, time, urllib.request, gc
from dataclasses import dataclass
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM

random.seed(17)
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"

HOLDOUT=[
"تقدّم مؤسسة الرعاية الصحية الأولية خدمةً فريدة من نوعها وهي عيادة المدرّب الصحي، بهدف تمكين المرضى الذين يعانون من السمنة والأمراض المزمنة مثل السكري وارتفاع ضغط الدم ومتلازمة التمثيل الغذائي من تحسين نوعية حياتهم من خلال اتباع عادات وسلوكيات صحية.",
"ويأتي الربو الشعبي على شكل نوبات بين الحين والآخر، وهذه النوبات تحصل بسبب تهيج في الشعب والشعيبات الهوائية نتيجة التعرض لمهيجات، ويؤدي هذا التهيج إلى تورم الطبقة المبطنة لهذه الشعب مما يؤدي إلى تضيقها الأمر الذي يظهر بصورة صعوبة في التنفس وكحة وضيق في الصدر وصفير مصاحب للتنفس.",
"إن علاج الربو يعتمد أساسا على مبدأ الوقاية خير من العلاج، أي انه يعتمد على الوقاية من نوبات الربو وتجنب حدوثها، وإن مجرد حدوث نوبة أو حتى بعض أعراض الربو يعتبر فشل وعدم كفاية العلاج أو الاجراءات المستخدمة.",
"خدمة الفحص الصحي الدوري هي عبارة عن فحص طبي للبالغين من عمر 18 عاماً وما فوق، وهي مصممة لاكتشاف العلامات المبكرة للمرض وتقديم الدعم والمشورة اللازمة حول كيفية الحد من مخاطر الإصابة بالأمراض بما في ذلك مرض السكري وأمراض القلب.",
"وتشمل هذه المؤشرات ضغط الدم والكوليسترول وسكر الدم ومؤشر كتلة الجسم. ويتم تقديم الخدمة من خلال زيارتين، الزيارة الأولى هي موعد التقييم الدوري والزيارة الثانية هي موعد الاستشارة الدورية التي تتم مع الطبيب.",
"تواصل دبي الصحية تحديث منظومتها وتقديم برامج ومبادرات مبتكرة ومستدامة تدعم إدارة المرض والحد من مضاعفاته، أبرزها تطبيق تقنيات الذكاء الاصطناعي في رعاية ومتابعة المرضى عن بعد على مدار الساعة، وقياس مستويات السكر في الدم.",
"وتشمل مبادرات دبي الصحية برنامج للكشف المبكر عن مرض السكري، بهدف تحديد الحالات الجديدة في مراحلها الأولى، والتدخل السريع لتجنب تطوره، فضلاً عن توفير خطة شاملة لرعايتهم في كافة مستشفياتها ومراكزها الطبية.",
"الإصابة بعدوى فيروس الكبد الوبائي ب أو فيروس الكبد الوبائي سي، وتليّف الكبد، والبدانة، والسكري، وأمراض القولون مثل التهاب القولون التقرّحي من عوامل الخطورة للإصابة بسرطان الكبد.",
"تشمل أعراض سرطان الكبد اليرقان وألم الجانب العلوي الأيمن من البطن وانتفاخ الجزء العلوي من البطن وفقدان الشهية والغثيان والإرهاق وفقدان الوزن دون سبب.",
"سرطان البنكرياس هو السرطان الذي يبدأ في البنكرياس أي في الغدّة التي تقع بين المعدة والعمود الفقري، والتي تفرز الأنسولين وهرمونات أخرى، وتساعد الجسم على استخدام الطاقة التي تنتج عن الطعام أو تخزينه.",
"تشمل عوامل الخطورة التي تزيد فرص الإصابة بسرطان البنكرياس البدانة والتدخين والسكري ووجود تاريخ عائلي للإصابة بسرطان البنكرياس والتهاب البنكرياس المزمن.",
"من عوامل الخطورة التي تزيد فرص الإصابة بسرطان الرحم البدانة والسكري وارتفاع ضغط الدم وتضخم غير طبيعي لبطانة الرحم ووجود تاريخ عائلي للإصابة بسرطان الرحم.",
"تشمل أعراض سرطان الكلى وجود دم في البول وألم في الخاصرة وكتلة ملموسة في الخاصرة أو البطن وفقدان وزن غير مفسر والحمّى وارتفاع ضغط الدم وفرط كالسيوم الدم وتعرق ليلي.",
"تشمل الخبرة إدارة حالات الربو ومرض الانسداد الرئوي المزمن وارتفاع ضغط الدم وإدارة أمراض القلب الإقفارية وعدم انتظام ضربات القلب ومرض السكري.",
"يتم إجراء فحوصات المختبر اللازمة لدراسة كل مريض بشكل أوسع، الأمر الذي سيتيح التشخيص والمراقبة المستمرة للحالة الصحية، مثل ارتفاع ضغط الدم ومرض السكري واضطرابات دهون الدم وأمراض التهاب المفاصل وغيرها من الأمراض."
]

# Curated semantic aliases only. No opaque private codes.
RULES=[
(["داء السكري من النوع الأول","السكري من النوع الأول"],["T1DM","type 1 diabetes"]),
(["داء السكري من النوع الثاني","السكري من النوع الثاني"],["T2DM","type 2 diabetes"]),
(["انخفاض سكر الدم","انخفاض السكر في الدم","نقص سكر الدم"],["hypoglycemia"]),
(["ارتفاع سكر الدم","ارتفاع السكر في الدم"],["hyperglycemia"]),
(["مستويات السكر في الدم","مستوى السكر في الدم","نسبة السكر في الدم","سكر الدم"],["blood glucose"]),
(["الهيموغلوبين السكري","السكر التراكمي"],["HbA1c"]),
(["الحماض الكيتوني السكري","الحماض الكيتوني"],["DKA"]),
(["ارتفاع ضغط الدم","فرط ضغط الدم","ضغط الدم المرتفع"],["HTN","hypertension"]),
(["ضغط الدم","قياس الضغط"],["BP","blood pressure"]),
(["مرض السكري","داء السكري","السكري"],["diabetes"]),
(["مرض الكلى المزمن","أمراض الكلى المزمنة"],["CKD"]),
(["الفشل الكلوي","فشل كلوي"],["renal failure"]),
(["غسيل الكلى","الغسيل الكلوي"],["dialysis"]),
(["التهاب المسالك البولية","عدوى المسالك البولية"],["UTI"]),
(["مضادات الالتهاب غير الستيرويدية"],["NSAID"]),
(["مرض الربو","الربو"],["asthma"]),
(["ضيق في التنفس","ضيق التنفس","صعوبة التنفس"],["dyspnea"]),
(["الصفير أثناء التنفس","أزيز أثناء التنفس"],["wheeze"]),
(["ألم في الصدر","ألم الصدر"],["chest pain"]),
(["العلامات الحيوية","علامات حيوية"],["vitals"]),
(["الرعاية الصحية الأولية","الرعاية الأولية"],["primary care"]),
(["تشبع الأكسجين","إشباع الأكسجين"],["SpO2"]),
(["تعداد الدم الكامل"],["CBC"]),
(["تخطيط القلب الكهربائي","تخطيط القلب"],["ECG"]),
(["أشعة الصدر","الأشعة السينية على الصدر"],["CXR"]),
(["التصوير المقطعي المحوسب","الأشعة المقطعية"],["CT"]),
(["التصوير بالرنين المغناطيسي","الرنين المغناطيسي"],["MRI"]),
(["التهاب رئوي","الالتهاب الرئوي"],["pneumonia"]),
(["السوائل الوريدية","سوائل وريدية"],["IV fluids"]),
(["المضادات الحيوية","المضاد الحيوي","مضاد حيوي"],["antibiotic"]),
(["مرض الانسداد الرئوي المزمن","الانسداد الرئوي المزمن"],["COPD"]),
(["السكتة الدماغية الإقفارية","السكتة الإقفارية"],["ischemic stroke"]),
(["السكتة الدماغية النزفية","السكتة النزفية"],["hemorrhagic stroke"]),
(["نوبة نقص تروية عابرة"],["TIA"]),
(["احتشاء عضلة القلب","النوبة القلبية"],["MI"]),
(["الرجفان الأذيني"],["AF"]),
(["مرض الشرايين التاجية","أمراض الشرايين التاجية"],["CAD"]),
(["الخثار الوريدي العميق","جلطة وريدية عميقة"],["DVT"]),
(["الانصمام الرئوي","جلطة رئوية"],["PE"]),
(["ارتفاع الكوليسترول","الكوليسترول المرتفع"],["high cholesterol"]),
(["الكوليسترول","كولسترول"],["cholesterol"]),
(["التاريخ العائلي","تاريخ عائلي"],["FHx","family history"]),
(["التاريخ المرضي","التاريخ الطبي"],["Hx","medical history"]),
(["عوامل الخطورة","عوامل الخطر"],["risk factors"]),
(["فقدان الوزن","إنقاص الوزن"],["weight loss"]),
(["السمنة","البدانة"],["obesity"]),
(["ارتفاع درجة الحرارة","الحمى","الحمّى"],["fever"]),
(["الصداع النصفي","الشقيقة"],["migraine"]),
(["الغثيان"],["nausea"]),
(["القيء","الاستفراغ"],["vomiting"]),
(["ألم البطن","آلام البطن"],["abdominal pain"]),
(["التهاب الكبد بي","فيروس الكبد الوبائي ب"],["HBV","hepatitis B"]),
(["التهاب الكبد سي","فيروس الكبد الوبائي سي"],["HCV","hepatitis C"]),
(["البروتين في البول","وجود بروتين في البول"],["proteinuria"]),
(["الدم في البول","وجود دم في البول"],["hematuria"]),
(["مراقبة ضغط الدم","متابعة ضغط الدم"],["BP monitoring"]),
(["مراقبة سكر الدم"],["glucose monitoring"]),
(["سكري الحمل","السكري الحملي"],["GDM"]),
(["العلاج الكيميائي"],["chemotherapy"]),
(["العلاج الإشعاعي"],["radiotherapy"]),
(["فقر الدم","الأنيميا"],["anemia"]),
(["إصابة الكلى الحادة","الفشل الكلوي الحاد"],["AKI"]),
(["ملخص الخروج","ملخص خروج المريض"],["discharge summary"]),
(["التاريخ المرضي السابق","الأمراض السابقة"],["PMH"]),
(["الأدوية الحالية","العلاجات الحالية"],["current meds"]),
(["نتائج المختبر","نتائج التحاليل","التحاليل المخبرية"],["labs"]),
(["خلايا الدم الحمراء","كريات الدم الحمراء"],["RBC"]),
(["خلايا الدم البيضاء","كريات الدم البيضاء"],["WBC"]),
(["الهيموغلوبين","الهيموجلوبين"],["Hb","hemoglobin"]),
(["تليف الكبد","تشمع الكبد","تليّف الكبد"],["cirrhosis"]),
(["سرطان الكبد"],["liver cancer"]),
(["الموجات فوق الصوتية","الأشعة فوق الصوتية"],["ultrasound"]),
(["الخزعة","أخذ عينة"],["biopsy"]),
(["التهاب المفاصل الروماتويدي","الروماتويد"],["rheumatoid arthritis"]),
(["النقرس"],["gout"]),
(["الصداع"],["headache"]),
(["الصرع"],["epilepsy"]),
(["الارتجاع المعدي المريئي","ارتجاع المريء"],["GERD"]),
(["متلازمة القولون العصبي","القولون العصبي"],["IBS"]),
(["مرض الأمعاء الالتهابي"],["IBD"]),
(["التهاب البنكرياس"],["pancreatitis"]),
(["متلازمة تكيس المبايض","تكيس المبايض"],["PCOS"]),
(["فيروس نقص المناعة البشرية"],["HIV"]),
(["السل","الدرن"],["TB","tuberculosis"]),
(["كوفيد 19","كوفيد-19"],["COVID-19"]),
(["مؤشر كتلة الجسم","كتلة الجسم"],["BMI"]),
(["الدهون الثلاثية"],["TG","triglycerides"]),
(["البروتين الدهني مرتفع الكثافة"],["HDL"]),
(["البروتين الدهني منخفض الكثافة"],["LDL"]),
(["الأمراض المزمنة","امراض مزمنة"],["chronic diseases"]),
(["التشخيص"],["Dx","diagnosis"]),
(["العلاج"],["Tx","treatment"]),
(["الأعراض","أعراض"],["Sx","symptoms"]),
(["الأنسولين","الانسولين"],["insulin"]),
(["التدخين"],["smoking"])
]
UNIT_RULES=[
(re.compile(r"(?:مليغرام|ملليغرام|ميليغرام|ملغم)",re.I),"mg"),
(re.compile(r"(?:مليمتر زئبق|ملم زئبق)",re.I),"mmHg"),
(re.compile(r"(?:نبضة في الدقيقة|نبضات في الدقيقة)",re.I),"bpm"),
]

@dataclass
class C:
    s:int; e:int; old:str; new:str; save:int

def boundary(text,s,e):
    ar=lambda ch: "\u0600"<=ch<="\u06ff"
    return not (s>0 and ar(text[s-1])) and not (e<len(text) and ar(text[e]))

def encode(text,tok):
    count=lambda x: len(tok(x,add_special_tokens=False)["input_ids"])
    base=count(text); cs=[]
    for forms,aliases in RULES:
        for form in forms:
            pos=0
            while True:
                s=text.find(form,pos)
                if s<0: break
                e=s+len(form); pos=s+1
                if not boundary(text,s,e): continue
                best=None
                a=max(0,s-40); b=min(len(text),e+40)
                for alias in aliases:
                    save=count(text[a:b])-count(text[a:s]+alias+text[e:b])
                    if save>0 and (best is None or save>best[0]): best=(save,alias)
                if best: cs.append(C(s,e,text[s:e],best[1],best[0]))
    for rx,alias in UNIT_RULES:
        for m in rx.finditer(text):
            a=max(0,m.start()-40); b=min(len(text),m.end()+40)
            save=count(text[a:b])-count(text[a:m.start()]+alias+text[m.end():b])
            if save>0: cs.append(C(m.start(),m.end(),m.group(),alias,save))
    # greedy by token saving then longer span. A global exact guard follows.
    cs=sorted(cs,key=lambda x:(-x.save,-(x.e-x.s),x.s))
    sel=[]
    for c in cs:
        if all(c.e<=x.s or c.s>=x.e for x in sel): sel.append(c)
    sel=sorted(sel,key=lambda x:x.s)
    def render(xs):
        out=[]; p=0
        for c in xs: out += [text[p:c.s],c.new]; p=c.e
        out.append(text[p:]); return "".join(out)
    tr=render(sel); n=count(tr)
    while sel and n>=base:
        k=min(range(len(sel)),key=lambda i:sel[i].save)
        sel.pop(k); tr=render(sel); n=count(tr)
    if n>base: return text,base,base,0
    return tr,base,n,len(sel)

def load_rows():
    raw=urllib.request.urlopen(TEST_URL,timeout=120).read().decode("utf-8-sig","replace")
    return list(csv.DictReader(io.StringIO(raw)))

def make_prompt(r):
    lines=["السؤال: "+r["Question"]]
    for L in "ABCDEF":
        v=(r.get("Option "+L) or "").strip()
        if v: lines.append(f"{L}) {v}")
    lines += ["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
    return "\n".join(lines)

def next_choice(model,tok,prompt,labels):
    # Fast path: score the next token for each label; works when a leading-space label is one token.
    ids=tok(prompt,return_tensors="pt",add_special_tokens=False)["input_ids"]
    with torch.no_grad(): logits=model(input_ids=ids,use_cache=False).logits[0,-1].float()
    scores={}
    for L in labels:
        li=tok(" "+L,add_special_tokens=False)["input_ids"]
        if len(li)==1: scores[L]=float(logits[li[0]])
        else:
            # Rare fallback: exact autoregressive suffix score.
            cur=ids; total=0.0
            for tid in li:
                with torch.no_grad(): z=model(input_ids=cur,use_cache=False).logits[0,-1].float()
                total += float(F.log_softmax(z,dim=-1)[tid])
                cur=torch.cat([cur,torch.tensor([[tid]])],dim=1)
            scores[L]=total
    return max(scores,key=scores.get)

TOKENIZER_MODELS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"mistralai/Mistral-7B-Instruct-v0.3",
"microsoft/Phi-3-mini-4k-instruct",
"tiiuae/Falcon3-1B-Instruct"
]
BEHAVIOR_MODELS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0"
]

def tokenizer_benchmark(rows):
    out={}
    for mid in TOKENIZER_MODELS:
        try:
            tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
            B=T=rep=0; case=[]
            for text in HOLDOUT:
                tr,b,n,k=encode(text,tok); B+=b; T+=n; rep+=k; case.append((b-n)/b*100 if b else 0)
            # scan MCQ corpus too
            mb=mt=changed=0
            for r in rows[:1200]:
                p=make_prompt(r); tr,b,n,k=encode(p,tok); mb+=b; mt+=n; changed+=int(tr!=p)
            out[mid]={
                "holdout_baseline":B,"holdout_transformed":T,
                "holdout_reduction_pct":100*(B-T)/B if B else 0,
                "holdout_median_case_pct":st.median(case),"holdout_replacements":rep,
                "mcq_1200_baseline":mb,"mcq_1200_transformed":mt,
                "mcq_1200_reduction_pct":100*(mb-mt)/mb if mb else 0,
                "mcq_changed_cases":changed,"no_regression":T<=B and mt<=mb
            }
        except Exception as e:
            out[mid]={"error":repr(e)}
    return out

def behavior_benchmark(rows):
    out={}
    for mid in BEHAVIOR_MODELS:
        try:
            tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
            # choose changed cases across the complete test set; deterministic and then shuffled.
            pool=[]
            for r in rows:
                p=make_prompt(r); tr,b,n,k=encode(p,tok)
                if tr!=p and n<b:
                    pool.append((r,p,tr,b,n,k))
            random.Random(17).shuffle(pool)
            sample=pool[:24]
            model=AutoModelForCausalLM.from_pretrained(mid,torch_dtype=torch.float32,low_cpu_mem_usage=True,trust_remote_code=True)
            model.eval()
            for p in model.parameters(): p.requires_grad_(False)
            agree=baseok=compok=0; B=T=0; details=[]; times=[]
            for r,p,tr,b,n,k in sample:
                labels=[L for L in "ABCDEF" if (r.get("Option "+L) or "").strip()]
                t=time.perf_counter(); a=next_choice(model,tok,p,labels); c=next_choice(model,tok,tr,labels); times.append(time.perf_counter()-t)
                gold=(r.get("Correct Answer") or "").strip()[:1]
                agree+=int(a==c); baseok+=int(a==gold); compok+=int(c==gold); B+=b; T+=n
                details.append({"q":r.get("Question Number"),"gold":gold,"baseline":a,"compressed":c,"tokens":[b,n],"replacements":k})
            out[mid]={
                "available_changed_cases":len(pool),"n":len(sample),
                "agreement":agree/len(sample) if sample else None,
                "baseline_accuracy":baseok/len(sample) if sample else None,
                "compressed_accuracy":compok/len(sample) if sample else None,
                "token_reduction_pct":100*(B-T)/B if B else 0,
                "baseline_tokens":B,"transformed_tokens":T,
                "mean_pair_eval_seconds":sum(times)/len(times) if times else None,
                "details":details
            }
            del model; gc.collect()
        except Exception as e:
            out[mid]={"error":repr(e)}
    return out

rows=load_rows()
result={"architecture":"ACP-U4 plain-text clinical transcoder","tokenizers":tokenizer_benchmark(rows),"behavior":behavior_benchmark(rows)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u4_results.json","w",encoding="utf-8").write(json.dumps(result,ensure_ascii=False,indent=2))
print("ACP_U4_SUMMARY="+json.dumps({k:v for k,v in result.items() if k!="behavior"},ensure_ascii=False),flush=True)
print("ACP_U4_BEHAVIOR="+json.dumps(result["behavior"],ensure_ascii=False),flush=True)
