#!/usr/bin/env python3
import csv, io, json, os, random, statistics as st, time, urllib.request, gc
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoModelForSeq2SeqLM

SEED=23
random.seed(SEED); torch.manual_seed(SEED)
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MT_ID="Helsinki-NLP/opus-mt-ar-en"
TARGETS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"mistralai/Mistral-7B-Instruct-v0.3",
"microsoft/Phi-3-mini-4k-instruct",
"tiiuae/Falcon3-1B-Instruct"
]
BEHAVIOR=[
("Qwen/Qwen2.5-0.5B-Instruct",24),
("HuggingFaceTB/SmolLM2-360M-Instruct",24),
("TinyLlama/TinyLlama-1.1B-Chat-v1.0",8)
]
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

def fetch_rows():
    raw=urllib.request.urlopen(TEST_URL,timeout=120).read().decode("utf-8-sig","replace")
    rows=list(csv.DictReader(io.StringIO(raw)))
    rng=random.Random(SEED); rng.shuffle(rows)
    return rows

def ar_prompt(r):
    L=["السؤال: "+r["Question"]]
    for x in "ABCDEF":
        v=(r.get("Option "+x) or "").strip()
        if v:L.append(f"{x}) {v}")
    L+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
    return "\n".join(L)

def en_prompt(r,compact=False):
    q=r["_en_q"]
    if compact:L=["Q:"+q]
    else:L=["Question: "+q]
    for x in "ABCDEF":
        v=r.get("_en_"+x,"").strip()
        if v:L.append(f"{x}:{v}" if compact else f"{x}) {v}")
    L += ["Answer letter:" if compact else "Select the correct option letter only.\nAnswer:"]
    return "\n".join(L)

def chat_ids(tok,text):
    try:return tok.apply_chat_template([{"role":"user","content":text}],tokenize=True,add_generation_prompt=True)
    except Exception:return tok(text,add_special_tokens=False)["input_ids"]

def count(tok,text):return len(tok(text,add_special_tokens=False)["input_ids"])
def ccount(tok,text):return len(chat_ids(tok,text))

def translate_all(rows):
    mtok=AutoTokenizer.from_pretrained(MT_ID)
    mt=AutoModelForSeq2SeqLM.from_pretrained(MT_ID,torch_dtype=torch.float32)
    mt.eval()
    segments=[]; slots=[]
    for i,r in enumerate(rows):
        segments.append(r["Question"]);slots.append((i,"_en_q"))
        for x in "ABCDEF":
            v=(r.get("Option "+x) or "").strip()
            if v:segments.append(v);slots.append((i,"_en_"+x))
    for start in range(0,len(segments),16):
        batch=segments[start:start+16]
        inp=mtok(batch,return_tensors="pt",padding=True,truncation=True,max_length=256)
        with torch.no_grad():gen=mt.generate(**inp,max_new_tokens=256,num_beams=1)
        outs=mtok.batch_decode(gen,skip_special_tokens=True)
        for j,out in enumerate(outs):
            i,k=slots[start+j];rows[i][k]=out.strip()
    h=[]
    for start in range(0,len(HOLDOUT),8):
        batch=HOLDOUT[start:start+8]
        inp=mtok(batch,return_tensors="pt",padding=True,truncation=True,max_length=256)
        with torch.no_grad():gen=mt.generate(**inp,max_new_tokens=300,num_beams=1)
        h.extend([x.strip() for x in mtok.batch_decode(gen,skip_special_tokens=True)])
    del mt,mtok;gc.collect()
    return h

def score_choice(model,tok,text,labels):
    ids=torch.tensor([chat_ids(tok,text)],dtype=torch.long)
    with torch.no_grad():z=model(input_ids=ids,use_cache=False).logits[0,-1].float()
    sc={}
    for L in labels:
        ids1=tok(L,add_special_tokens=False)["input_ids"]
        ids2=tok(" "+L,add_special_tokens=False)["input_ids"]
        vals=[]
        if len(ids1)==1:vals.append(float(z[ids1[0]]))
        if len(ids2)==1:vals.append(float(z[ids2[0]]))
        sc[L]=max(vals) if vals else float(z[ids1[0]])
    return max(sc,key=sc.get)

def guarded(tok,orig,cand):
    return cand if ccount(tok,cand)<ccount(tok,orig) else orig

def token_bench(rows,h_en):
    out={}
    for mid in TARGETS:
        try:
            tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
            hb=sum(count(tok,x) for x in HOLDOUT); ht=sum(count(tok,x) for x in h_en)
            # paired first 100 translated rows
            stats={}
            for mode in ("full","compact"):
                ob=ot=cb=ct=0;fallback=0
                for r in rows[:100]:
                    a=ar_prompt(r);e=en_prompt(r,compact=(mode=="compact"));g=guarded(tok,a,e)
                    ob+=count(tok,a);ot+=count(tok,g);cb+=ccount(tok,a);ct+=ccount(tok,g);fallback+=int(g==a)
                stats[mode]={
                    "content_reduction_pct":100*(ob-ot)/ob,
                    "chat_reduction_pct":100*(cb-ct)/cb,
                    "fallback_cases":fallback
                }
            out[mid]={
                "clinical_holdout_translation_reduction_pct":100*(hb-ht)/hb,
                **stats
            }
        except Exception as e:out[mid]={"error":repr(e)}
    try:
        import tiktoken
        for encname in ("cl100k_base","o200k_base"):
            enc=tiktoken.get_encoding(encname)
            hb=sum(len(enc.encode(x)) for x in HOLDOUT);ht=sum(len(enc.encode(x)) for x in h_en)
            out["tiktoken/"+encname]={"clinical_holdout_translation_reduction_pct":100*(hb-ht)/hb}
    except Exception as e:out["tiktoken"]={"error":repr(e)}
    return out

def behavior(rows):
    out={}
    for mid,ncase in BEHAVIOR:
        try:
            tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
            model=AutoModelForCausalLM.from_pretrained(mid,torch_dtype=torch.float32,low_cpu_mem_usage=True,trust_remote_code=True)
            model.eval()
            for p in model.parameters():p.requires_grad_(False)
            sample=rows[:ncase];base=[];gold=[]
            t0=time.perf_counter()
            for r in sample:
                labels=[x for x in "ABCDEF" if (r.get("Option "+x) or "").strip()]
                base.append(score_choice(model,tok,ar_prompt(r),labels))
                gold.append((r.get("Correct Answer") or "").strip().upper()[:1])
            res={}
            for mode in ("full","compact"):
                ans=[];ob=ot=cb=ct=0;fallback=0
                for r in sample:
                    a=ar_prompt(r);e=en_prompt(r,compact=(mode=="compact"));g=guarded(tok,a,e)
                    labels=[x for x in "ABCDEF" if (r.get("Option "+x) or "").strip()]
                    ans.append(score_choice(model,tok,g,labels))
                    ob+=count(tok,a);ot+=count(tok,g);cb+=ccount(tok,a);ct+=ccount(tok,g);fallback+=int(g==a)
                agree=sum(x==y for x,y in zip(base,ans))/ncase
                bacc=sum(x==y for x,y in zip(base,gold))/ncase
                aacc=sum(x==y for x,y in zip(ans,gold))/ncase
                res[mode]={
                    "n":ncase,"agreement_with_arabic":agree,
                    "arabic_accuracy":bacc,"interlingua_accuracy":aacc,
                    "accuracy_delta":aacc-bacc,
                    "content_reduction_pct":100*(ob-ot)/ob,
                    "chat_reduction_pct":100*(cb-ct)/cb,
                    "fallback_cases":fallback,
                    "changed_answers":[{"q":sample[i].get("Question Number"),"gold":gold[i],"arabic":base[i],"interlingua":ans[i]} for i in range(ncase) if base[i]!=ans[i]]
                }
            res["seconds"]=time.perf_counter()-t0
            out[mid]=res
            del model;gc.collect()
        except Exception as e:out[mid]={"error":repr(e)}
    return out

rows=fetch_rows()[:120]
h_en=translate_all(rows)
result={"version":"ACP-U6 clinical English interlingua","translator":MT_ID,"tokenizers":token_bench(rows,h_en),"behavior":behavior(rows)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u6_results.json","w",encoding="utf-8").write(json.dumps(result,ensure_ascii=False,indent=2))
print("ACP_U6_TOKENIZERS="+json.dumps(result["tokenizers"],ensure_ascii=False),flush=True)
print("ACP_U6_BEHAVIOR="+json.dumps(result["behavior"],ensure_ascii=False),flush=True)
