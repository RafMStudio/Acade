#!/usr/bin/env python3
import csv,io,json,os,re,random,statistics as st,urllib.request,gc
from collections import Counter
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM,AutoModelForCausalLM
SEED=41
random.seed(SEED);torch.manual_seed(SEED)
TRAIN_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-train_split.csv"
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
MT="Helsinki-NLP/opus-mt-ar-en"
TOKS=["Qwen/Qwen2.5-0.5B-Instruct","HuggingFaceTB/SmolLM2-360M-Instruct","TinyLlama/TinyLlama-1.1B-Chat-v1.0","mistralai/Mistral-7B-Instruct-v0.3","microsoft/Phi-3-mini-4k-instruct","tiiuae/Falcon3-1B-Instruct"]
BEH=[("Qwen/Qwen2.5-0.5B-Instruct",24),("HuggingFaceTB/SmolLM2-360M-Instruct",24),("TinyLlama/TinyLlama-1.1B-Chat-v1.0",8)]
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]{3,}")
STOP=set("""السؤال الإجابة الاجابة اختر الصحيحة الصحيح الخاطئة الخاطئ حرف الخيارات أعلاه اعلاه من في على إلى الى عن مع ما ماذا هل لا لم لن ليس ليست كان كانت يكون تكون هذا هذه ذلك تلك الذي التي الذين كل أي اى او أو و ثم ف ب ك ل لل ال عند بين بعد قبل خلال ضمن حيث إذا اذا إن ان أن قد كما فقط غير عدا سوى حتى هو هي هم هن نحن انا أنا انت أنت هناك هنا تم يتم لدى له لها لهم بها به فيه فيها منها منه إليها اليها عليه عليها والتي والذين أما اما لأن لان لكن الأول الاول الثاني الثالثة الثالث الرابع الخامسة الخامس التالي التالية يلي حول صحيح خطأ خطا""".split())
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
def load(url):
 raw=urllib.request.urlopen(url,timeout=120).read().decode("utf-8-sig","replace");return list(csv.DictReader(io.StringIO(raw)))
def texts(r):
 a=[r.get("Question","")];a += [(r.get("Option "+x) or "") for x in "ABCDEF"];return a
def prompt(r):
 a=["السؤال: "+r["Question"]]
 for x in "ABCDEF":
  v=(r.get("Option "+x) or "").strip()
  if v:a.append(f"{x}) {v}")
 a+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"];return "\n".join(a)
def mine(rows,n=2200):
 c=Counter()
 for r in rows:
  for t in texts(r):
   for m in AR.finditer(t):
    w=m.group(0)
    if w not in STOP:c[w]+=1
 # favor frequent and long Arabic words
 return [w for w,f in sorted(c.items(),key=lambda kv:kv[1]*len(kv[0]),reverse=True)[:n]]
def translate(words):
 tok=AutoTokenizer.from_pretrained(MT);mod=AutoModelForSeq2SeqLM.from_pretrained(MT,torch_dtype=torch.float32);mod.eval();out={}
 for i in range(0,len(words),64):
  b=words[i:i+64];inp=tok(b,return_tensors="pt",padding=True,truncation=True,max_length=32)
  with torch.no_grad():g=mod.generate(**inp,max_new_tokens=16,num_beams=1)
  en=tok.batch_decode(g,skip_special_tokens=True)
  for ar,x in zip(b,en):
   x=re.sub(r"\s+"," ",x.strip());x=re.sub(r"^[Tt]he\s+","",x).strip(" .,:;!?")
   if x and len(x.split())<=3 and len(x)<=28 and not any("\u0600"<=z<="\u06ff" for z in x):out[ar]=x
 del mod,tok;gc.collect();return out
def tc(tok,t):return len(tok(t,add_special_tokens=False)["input_ids"])
def chatids(tok,t):
 try:return tok.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True)
 except:return tok(t,add_special_tokens=False)["input_ids"]
def cc(tok,t):return len(chatids(tok,t))
def transform(text,tok,d):
 base=tc(tok,text);ms=list(AR.finditer(text));cand=[]
 for m in ms:
  ar=m.group(0);en=d.get(ar)
  if not en:continue
  a=max(0,m.start()-36);b=min(len(text),m.end()+36)
  sv=tc(tok,text[a:b])-tc(tok,text[a:m.start()]+en+text[m.end():b])
  if sv>0:cand.append((m.start(),m.end(),en,sv))
 # nonoverlap naturally word-level
 cand.sort()
 def render(xs):
  o=[];p=0
  for s,e,en,sv in xs:o += [text[p:s],en];p=e
  o.append(text[p:]);return "".join(o)
 tr=render(cand);n=tc(tok,tr)
 if n>base:return text,base,base,0
 return tr,base,n,len(cand)
def answer(mod,tok,t,labels):
 ids=torch.tensor([chatids(tok,t)])
 with torch.no_grad():z=mod(input_ids=ids,use_cache=False).logits[0,-1].float()
 sc={}
 for L in labels:
  vals=[]
  for q in (L," "+L):
   ii=tok(q,add_special_tokens=False)["input_ids"]
   if len(ii)==1:vals.append(float(z[ii[0]]))
  sc[L]=max(vals) if vals else -1e9
 return max(sc,key=sc.get)
train=load(TRAIN_URL);test=load(TEST_URL);words=mine(train);d=translate(words)
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u8_dictionary.json","w",encoding="utf8").write(json.dumps(d,ensure_ascii=False,indent=2))
res={"version":"ACP-U8 mixed-language word interlingua","mined_words":len(words),"translated_words":len(d),"tokenizers":{},"behavior":{}}
for mid in TOKS:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
  B=T=0
  for x in HOLDOUT:
   _,b,n,_=transform(x,tok,d);B+=b;T+=n
  mb=mt=cb=ct=0
  for r in test[:1200]:
   p=prompt(r);tr,b,n,_=transform(p,tok,d);mb+=b;mt+=n;cb+=cc(tok,p);ct+=cc(tok,tr)
  res["tokenizers"][mid]={"holdout_pct":100*(B-T)/B,"mcq_content_pct":100*(mb-mt)/mb,"mcq_chat_pct":100*(cb-ct)/cb,"no_regression":T<=B and mt<=mb and ct<=cb}
 except Exception as e:res["tokenizers"][mid]={"error":repr(e)}
random.Random(SEED).shuffle(test)
for mid,ncase in BEH:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);mod=AutoModelForCausalLM.from_pretrained(mid,torch_dtype=torch.float32,low_cpu_mem_usage=True,trust_remote_code=True);mod.eval()
  sample=test[:ncase];agree=0;bacc=0;tacc=0;B=T=0
  dif=[]
  for r in sample:
   p=prompt(r);tr,b,n,_=transform(p,tok,d);labels=[x for x in "ABCDEF" if (r.get("Option "+x) or "").strip()]
   a=answer(mod,tok,p,labels);q=answer(mod,tok,tr,labels);g=(r.get("Correct Answer") or "").strip().upper()[:1]
   agree+=a==q;bacc+=a==g;tacc+=q==g;B+=b;T+=n
   if a!=q:dif.append({"q":r.get("Question Number"),"base":a,"new":q,"gold":g})
  res["behavior"][mid]={"n":ncase,"agreement":agree/ncase,"baseline_acc":bacc/ncase,"compressed_acc":tacc/ncase,"content_pct":100*(B-T)/B,"changed":dif}
  del mod;gc.collect()
 except Exception as e:res["behavior"][mid]={"error":repr(e)}
open("e2e/acp_u8_results.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U8="+json.dumps(res,ensure_ascii=False),flush=True)
