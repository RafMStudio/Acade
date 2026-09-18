#!/usr/bin/env python3
import csv, io, json, os, re, math, random, statistics as st, urllib.request, gc
from collections import Counter
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

SEED=31
random.seed(SEED); torch.manual_seed(SEED)
TRAIN_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-train_split.csv"
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MT_ID="Helsinki-NLP/opus-mt-ar-en"
MODELS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"mistralai/Mistral-7B-Instruct-v0.3",
"microsoft/Phi-3-mini-4k-instruct",
"tiiuae/Falcon3-1B-Instruct"
]
ARWORD=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
STOP=set("""من في على إلى الى عن مع ما ماذا هل لا لم لن ليس ليست كان كانت يكون تكون هذا هذه ذلك تلك الذي التي الذين كل أي اى او أو و ثم ف ب ك ل لل ال عند بين بعد قبل خلال ضمن حيث إذا اذا إن ان أن قد كما فقط غير عدا سوى حتى هو هي هم هن نحن انا أنا انت أنت بعد قبل هناك هنا تم يتم لدى له لها لهم بها به فيه فيها منها منه إليها اليها عليه عليها والتي والذين أما اما لأن لان لكن أو الى على في من ما كل""".split())

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

def get_csv(url):
    raw=urllib.request.urlopen(url,timeout=120).read().decode("utf-8-sig","replace")
    return list(csv.DictReader(io.StringIO(raw)))

def fields(row):
    out=[row.get("Question","")]
    for L in "ABCDEF":
        v=(row.get("Option "+L) or "").strip()
        if v: out.append(v)
    return out

def prompt(row):
    x=["السؤال: "+row["Question"]]
    for L in "ABCDEF":
        v=(row.get("Option "+L) or "").strip()
        if v:x.append(f"{L}) {v}")
    x+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
    return "\n".join(x)

def words(text):
    return [m.group(0) for m in ARWORD.finditer(text)]

def mine(rows,limit=900):
    c=Counter()
    # Build strictly from TRAIN rows.
    for row in rows:
        for text in fields(row):
            w=words(text)
            for n in (1,2,3,4):
                for i in range(len(w)-n+1):
                    ng=tuple(w[i:i+n])
                    if n==1 and (ng[0] in STOP or len(ng[0])<4): continue
                    if all(z in STOP for z in ng):continue
                    c[ng]+=1
    scored=[]
    for ng,f in c.items():
        n=len(ng); chars=sum(map(len,ng))
        minf={1:18,2:7,3:4,4:3}[n]
        if f<minf:continue
        score=f*(chars+4*(n-1))*math.sqrt(n)
        scored.append((score,f,ng))
    scored.sort(reverse=True)
    # Diversity: cap near-duplicates by exact surface.
    return [x[2] for x in scored[:limit]]

def translate_phrases(phrases):
    tok=AutoTokenizer.from_pretrained(MT_ID)
    model=AutoModelForSeq2SeqLM.from_pretrained(MT_ID,torch_dtype=torch.float32)
    model.eval()
    src=[" ".join(x) for x in phrases]
    out=[]
    for i in range(0,len(src),32):
        b=src[i:i+32]
        inp=tok(b,return_tensors="pt",padding=True,truncation=True,max_length=64)
        with torch.no_grad():g=model.generate(**inp,max_new_tokens=40,num_beams=1)
        out += tok.batch_decode(g,skip_special_tokens=True)
    del model,tok;gc.collect()
    rules={}
    for ng,en in zip(phrases,out):
        en=re.sub(r"\s+"," ",en.strip())
        en=re.sub(r"^[Tt]he\s+","",en)
        en=en.strip(" .,:;!?")
        # reject malformed or suspiciously verbose translations
        if not en or any("\u0600"<=c<="\u06ff" for c in en):continue
        if len(en.split())>max(6,len(ng)+2):continue
        if len(en)>80:continue
        rules[ng]=en
    return rules

def tokcount(tok,text):return len(tok(text,add_special_tokens=False)["input_ids"])

def build_spans(text,rules):
    ms=list(ARWORD.finditer(text)); ws=[m.group(0) for m in ms]
    spans=[]
    for i in range(len(ws)):
        for n in (4,3,2,1):
            if i+n>len(ws):continue
            ng=tuple(ws[i:i+n])
            if ng in rules:
                spans.append((ms[i].start(),ms[i+n-1].end(),rules[ng],n))
    return spans

def transform(text,tok,rules):
    base=tokcount(tok,text)
    raw=[]
    for s,e,new,nw in build_spans(text,rules):
        a=max(0,s-48);b=min(len(text),e+48)
        sv=tokcount(tok,text[a:b])-tokcount(tok,text[a:s]+new+text[e:b])
        if sv>0:raw.append((s,e,new,sv,nw))
    raw.sort(key=lambda x:(-x[3],-x[4],x[0]))
    sel=[]
    for x in raw:
        if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
    sel.sort()
    def rend(xs):
        o=[];p=0
        for s,e,new,sv,nw in xs:o += [text[p:s],new];p=e
        o.append(text[p:]);return "".join(o)
    tr=rend(sel);n=tokcount(tok,tr)
    while sel and n>=base:
        k=min(range(len(sel)),key=lambda i:(sel[i][3],sel[i][4]))
        sel.pop(k);tr=rend(sel);n=tokcount(tok,tr)
    if n>base:return text,base,base,0
    return tr,base,n,len(sel)

def chat_count(tok,text):
    try:return len(tok.apply_chat_template([{"role":"user","content":text}],tokenize=True,add_generation_prompt=True))
    except Exception:return tokcount(tok,text)

train=get_csv(TRAIN_URL)
test=get_csv(TEST_URL)
phrases=mine(train,900)
rules=translate_phrases(phrases)
# Save learned dictionary for audit/reuse.
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u7_dictionary.json","w",encoding="utf-8").write(json.dumps({"source":"MedAraBench train only","rules":[{"ar":" ".join(k),"en":v} for k,v in rules.items()]},ensure_ascii=False,indent=2))
res={"version":"ACP-U7 train-mined phrase interlingua","train_phrases":len(phrases),"accepted_translations":len(rules),"models":{}}
for mid in MODELS:
    try:
        tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
        hb=ht=hk=0
        for x in HOLDOUT:
            _,b,n,k=transform(x,tok,rules);hb+=b;ht+=n;hk+=k
        mb=mt=cb=ct=rep=0
        for row in test[:1200]:
            p=prompt(row);tr,b,n,k=transform(p,tok,rules)
            mb+=b;mt+=n;cb+=chat_count(tok,p);ct+=chat_count(tok,tr);rep+=k
        res["models"][mid]={
          "holdout_reduction_pct":100*(hb-ht)/hb,
          "holdout_replacements":hk,
          "test1200_content_reduction_pct":100*(mb-mt)/mb,
          "test1200_chat_reduction_pct":100*(cb-ct)/cb,
          "test1200_replacements":rep,
          "passes_30_content":(mb-mt)/mb>=.30,
          "passes_30_chat":(cb-ct)/cb>=.30,
          "no_regression":ht<=hb and mt<=mb and ct<=cb
        }
    except Exception as e:res["models"][mid]={"error":repr(e)}
try:
    import tiktoken
    for encn in ("cl100k_base","o200k_base"):
        enc=tiktoken.get_encoding(encn)
        class W:
            def __call__(self,text,add_special_tokens=False):return {"input_ids":enc.encode(text)}
        tok=W();B=T=0
        for x in HOLDOUT:
            _,b,n,_=transform(x,tok,rules);B+=b;T+=n
        res["models"]["tiktoken/"+encn]={"holdout_reduction_pct":100*(B-T)/B,"passes_30_holdout":(B-T)/B>=.30,"no_regression":T<=B}
except Exception as e:res["tiktoken_error"]=repr(e)
open("e2e/acp_u7_results.json","w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U7="+json.dumps(res,ensure_ascii=False),flush=True)
