#!/usr/bin/env python3
import csv,io,json,os,re,random,statistics as st,urllib.request,gc
from collections import Counter
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
SEED=41
random.seed(SEED);torch.manual_seed(SEED)
TRAIN_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-train_split.csv"
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MT="Helsinki-NLP/opus-mt-ar-en"
MODELS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"mistralai/Mistral-7B-Instruct-v0.3",
"microsoft/Phi-3-mini-4k-instruct",
"tiiuae/Falcon3-1B-Instruct"]
ARWORD=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
STOP=set("""من في على إلى الى عن مع ما ماذا هل لا لم لن ليس ليست كان كانت يكون تكون هذا هذه ذلك تلك الذي التي الذين كل أي اى او أو و ثم ف ب ك ل لل ال عند بين بعد قبل خلال ضمن حيث إذا اذا إن ان أن قد كما فقط غير عدا سوى حتى هو هي هم هن نحن انا أنا انت أنت هناك هنا تم يتم لدى له لها لهم بها به فيه فيها منها منه إليها اليها عليه عليها والتي والذين أما اما لأن لان لكن أى يوجد توجد السؤال الإجابة الاجابة اختر الصحيحة الصحيح الخاطئة الخاطئ حرف الخيارات أعلاه اعلاه""".split())
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
MANUAL={
("ارتفاع","ضغط","الدم"):"HTN",("مرض","السكري"):"diabetes",("داء","السكري"):"diabetes",
("السكري","من","النوع","الأول"):"T1DM",("السكري","من","النوع","الثاني"):"T2DM",
("مرض","الكلى","المزمن"):"CKD",("تخطيط","القلب","الكهربائي"):"ECG",
("التصوير","بالرنين","المغناطيسي"):"MRI",("التصوير","المقطعي","المحوسب"):"CT",
("مرض","الانسداد","الرئوي","المزمن"):"COPD",("احتشاء","عضلة","القلب"):"MI",
("الرجفان","الأذيني"):"AF",("مؤشر","كتلة","الجسم"):"BMI",("تشبع","الأكسجين"):"SpO2",
("تعداد","الدم","الكامل"):"CBC",("الحماض","الكيتوني","السكري"):"DKA",
("فيروس","نقص","المناعة","البشرية"):"HIV",("التهاب","المسالك","البولية"):"UTI"}
def getcsv(url):
    raw=urllib.request.urlopen(url,timeout=120).read().decode("utf-8-sig","replace")
    return list(csv.DictReader(io.StringIO(raw)))
def fields(r):
    z=[r.get("Question","")]
    for L in "ABCDEF":
        v=(r.get("Option "+L) or "").strip()
        if v:z.append(v)
    return z
def prompt(r):
    z=["السؤال: "+r["Question"]]
    for L in "ABCDEF":
        v=(r.get("Option "+L) or "").strip()
        if v:z.append(f"{L}) {v}")
    z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
    return "\n".join(z)
def ws(t): return [m.group(0) for m in ARWORD.finditer(t)]
def mine(rows):
    uni=Counter();bi=Counter();tri=Counter();quad=Counter()
    for r in rows:
        for t in fields(r):
            w=ws(t)
            uni.update((x,) for x in w if len(x)>=3 and x not in STOP)
            bi.update(tuple(w[i:i+2]) for i in range(len(w)-1) if not all(x in STOP for x in w[i:i+2]))
            tri.update(tuple(w[i:i+3]) for i in range(len(w)-2) if not all(x in STOP for x in w[i:i+3]))
            quad.update(tuple(w[i:i+4]) for i in range(len(w)-3) if not all(x in STOP for x in w[i:i+4]))
    u=[k for k,v in uni.most_common(3500) if v>=3]
    b=[k for k,v in bi.most_common(1800) if v>=2]
    tr=[k for k,v in tri.most_common(900) if v>=2]
    q=[k for k,v in quad.most_common(400) if v>=2]
    return q+tr+b+u
def translate(ph):
    tok=AutoTokenizer.from_pretrained(MT)
    m=AutoModelForSeq2SeqLM.from_pretrained(MT,torch_dtype=torch.float32);m.eval()
    src=[" ".join(x) for x in ph];outs=[]
    for i in range(0,len(src),48):
        inp=tok(src[i:i+48],return_tensors="pt",padding=True,truncation=True,max_length=64)
        with torch.no_grad():g=m.generate(**inp,max_new_tokens=32,num_beams=1)
        outs+=tok.batch_decode(g,skip_special_tokens=True)
    del m,tok;gc.collect()
    d=dict(MANUAL)
    for k,v in zip(ph,outs):
        v=re.sub(r"\s+"," ",v.strip());v=re.sub(r"^[Tt]he\s+","",v).strip(" .,:;!?")
        if not v or any("\u0600"<=c<="\u06ff" for c in v):continue
        if len(v)>70 or len(v.split())>max(5,len(k)+1):continue
        if not re.search(r"[A-Za-z]",v):continue
        d.setdefault(k,v)
    return d
def tc(tok,t): return len(tok(t,add_special_tokens=False)["input_ids"])
def cc(tok,t):
    try:return len(tok.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True))
    except:return tc(tok,t)
def ortho(t):
    t=DIAC.sub("",t).replace("ـ","")
    t=t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩","0123456789"))
    t=t.replace("،",",").replace("؛",";")
    t=re.sub(r"[ \t]+"," ",t);t=re.sub(r" +([,;:.!?])",r"\1",t)
    return t
def spans(t,rules):
    ms=list(ARWORD.finditer(t));w=[m.group(0) for m in ms];out=[]
    for i in range(len(w)):
        for n in (4,3,2,1):
            if i+n<=len(w):
                k=tuple(w[i:i+n])
                if k in rules:out.append((ms[i].start(),ms[i+n-1].end(),rules[k],n))
    return out
def transform(t,tok,rules):
    base=tc(tok,t);raw=[]
    for s,e,new,nw in spans(t,rules):
        a=max(0,s-40);b=min(len(t),e+40)
        sv=tc(tok,t[a:b])-tc(tok,t[a:s]+new+t[e:b])
        if sv>0:raw.append((s,e,new,sv,nw))
    raw.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
    for x in raw:
        if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
    sel.sort()
    o=[];p=0
    for s,e,new,sv,nw in sel:o += [t[p:s],new];p=e
    o.append(t[p:]);tr=ortho("".join(o));n=tc(tok,tr)
    oo=ortho(t);on=tc(tok,oo)
    choices=[(base,t,0),(on,oo,0),(n,tr,len(sel))]
    best=min(choices,key=lambda x:x[0])
    return best[1],base,best[0],best[2]
train=getcsv(TRAIN_URL);test=getcsv(TEST_URL);phrases=mine(train);rules=translate(phrases)
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u8_dictionary.json","w",encoding="utf-8").write(json.dumps({"source":"MedAraBench train only","rules":[{"ar":" ".join(k),"en":v} for k,v in rules.items()]},ensure_ascii=False,indent=2))
res={"version":"ACP-U8 high-coverage phrase interlingua","mined":len(phrases),"rules":len(rules),"models":{}}
for mid in MODELS:
    try:
        tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
        hb=ht=0
        for x in HOLDOUT:
            _,b,n,_=transform(x,tok,rules);hb+=b;ht+=n
        mb=mt=cb=ct=rep=0
        for r in test[:1200]:
            p=prompt(r);tr,b,n,k=transform(p,tok,rules);mb+=b;mt+=n;cb+=cc(tok,p);ct+=cc(tok,tr);rep+=k
        cr=100*(mb-mt)/mb;chr=100*(cb-ct)/cb
        res["models"][mid]={"holdout_reduction_pct":100*(hb-ht)/hb,"test1200_content_reduction_pct":cr,"test1200_chat_reduction_pct":chr,"replacements":rep,"passes30_content":cr>=30,"passes30_chat":chr>=30,"no_regression":ht<=hb and mt<=mb and ct<=cb}
    except Exception as e:res["models"][mid]={"error":repr(e)}
open("e2e/acp_u8_results.json","w",encoding="utf-8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U8="+json.dumps(res,ensure_ascii=False),flush=True)
