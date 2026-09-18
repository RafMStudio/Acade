#!/usr/bin/env python3
import csv,io,json,os,re,urllib.request,gc,difflib
from collections import Counter
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM
TRAIN="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-train_split.csv"
TEST="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
DICT="e2e/acp_u8_dictionary.json";NLLB="facebook/nllb-200-distilled-600M";BACK="Helsinki-NLP/opus-mt-en-ar"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]+");DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
RISK=set("""السؤال الاجابة الإجابة اختر الصحيحة الصحيح الخاطئة الخاطئ خطأ خطا صح صحيح خاطئ الخيارات أعلاه اعلاه جواب ما ماذا يلي سبق عدا سوى باستثناء استثناء جميع كل أي ايا أيا لا شيء شئ مما
ليس ليست لم لن دون بدون ينفي تنفي نفي عدم غير قبل بعد منذ خلال فور فورا الآن حاليا اليوم غدا أمس ساعة ساعات يوم أيام اسبوع أسبوع اسابيع أسابيع شهر شهور سنة سنوات
الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار
جرعة جرعات وحدة وحدات ملغ ملغم مليغرام مليلتر ملل يوميا مرتين ثلاث مرات حامل الحمل حمل حوامل رضاعة مرضعة حساسية تحسس استبعاد يستبعد منع ممنوع يحظر أقل اقل أكثر اكثر فوق تحت نحو تقريبا حوالي""".split())
MAN={"ارتفاع ضغط الدم":"HTN","ضغط الدم":"BP","مرض السكري":"diabetes","داء السكري":"diabetes","السكري من النوع الأول":"T1DM","السكري من النوع الثاني":"T2DM","مرض الكلى المزمن":"CKD","تخطيط القلب الكهربائي":"ECG","التصوير بالرنين المغناطيسي":"MRI","التصوير المقطعي المحوسب":"CT","مرض الانسداد الرئوي المزمن":"COPD","احتشاء عضلة القلب":"MI","الرجفان الأذيني":"AF","مؤشر كتلة الجسم":"BMI","تشبع الأكسجين":"SpO2","تعداد الدم الكامل":"CBC","الحماض الكيتوني السكري":"DKA","فيروس نقص المناعة البشرية":"HIV","التهاب المسالك البولية":"UTI"}
def norm(s):
 s=DIAC.sub("",s).replace("ـ","").replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي");return " ".join(re.sub(r"[^\u0621-\u063A\u0641-\u064A ]+"," ",s).split())
rn={norm(x) for x in RISK}
def get(url):
 raw=urllib.request.urlopen(url,timeout=120).read().decode("utf-8-sig","replace");return list(csv.DictReader(io.StringIO(raw)))
def textfields(r):
 z=[r.get("Question","")]
 for L in "ABCDEF":z.append((r.get("Option "+L) or ""))
 return z
tr=get(TRAIN);te=get(TEST)
# Ngram frequency once, efficient.
freq=Counter()
for r in tr:
 for t in textfields(r):
  w=AR.findall(t)
  for n in (1,2,3,4):
   freq.update(tuple(w[i:i+n]) for i in range(len(w)-n+1))
raw=json.load(open(DICT,encoding="utf8"))["rules"];cand=[]
for x in raw:
 a=" ".join(x["ar"].split());k=tuple(a.split())
 if re.search(r"\d",a) or set(norm(a).split())&rn:continue
 f=freq.get(k,0)
 if f: cand.append((f*(max(1,len(a)-len(x["en"]))),f,a,x["en"]))
cand.sort(reverse=True);cand=cand[:1200]

def sim(a,b):
 a=a.lower();b=b.lower();r=difflib.SequenceMatcher(None,a,b).ratio();A=set(a.split());B=set(b.split());return max(r,len(A&B)/max(1,len(A|B)))
src=[x[2] for x in cand];eng=[x[3] for x in cand]
t=AutoTokenizer.from_pretrained(NLLB,src_lang="arb_Arab");m=AutoModelForSeq2SeqLM.from_pretrained(NLLB,dtype="auto",low_cpu_mem_usage=True);m.eval();bos=t.convert_tokens_to_ids("eng_Latn");fw=[]
for i in range(0,len(src),32):
 x=t(src[i:i+32],return_tensors="pt",padding=True,truncation=True,max_length=80)
 with torch.no_grad():g=m.generate(**x,forced_bos_token_id=bos,max_new_tokens=64,num_beams=1)
 fw+=t.batch_decode(g,skip_special_tokens=True)
del m,t;gc.collect()
t=AutoTokenizer.from_pretrained(BACK);m=AutoModelForSeq2SeqLM.from_pretrained(BACK,dtype="auto",low_cpu_mem_usage=True);m.eval();bw=[]
for i in range(0,len(eng),48):
 x=t(eng[i:i+48],return_tensors="pt",padding=True,truncation=True,max_length=80)
 with torch.no_grad():g=m.generate(**x,max_new_tokens=64,num_beams=1)
 bw+=t.batch_decode(g,skip_special_tokens=True)
del m,t;gc.collect()
rules={}
audit=[]
for (_,f,a,e),u,v in zip(cand,fw,bw):
 fs=sim(e.lower(),u.lower());bs=sim(norm(a),norm(v));ok=fs>=.56 and bs>=.50
 if ok:rules[tuple(a.split())]=e
 audit.append({"ar":a,"en":e,"freq":f,"forward":u,"back":v,"fs":fs,"bs":bs,"ok":ok})
for a,e in MAN.items():rules[tuple(a.split())]=e
def prompt(r):
 z=["السؤال: "+r["Question"]]
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:z.append(f"{L}) {v}")
 z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"];return "\n".join(z)
def tc(tk,s):return len(tk(s,add_special_tokens=False)["input_ids"])
def cc(tk,s):
 try:return len(tk.apply_chat_template([{"role":"user","content":s}],tokenize=True,add_generation_prompt=True))
 except:return tc(tk,s)
def transform(s,tk):
 ms=list(AR.finditer(s));w=[m.group(0) for m in ms];raw=[]
 for i in range(len(w)):
  for n in (4,3,2,1):
   if i+n>len(w):continue
   k=tuple(w[i:i+n])
   if k not in rules:continue
   a,b=ms[i].start(),ms[i+n-1].end();new=rules[k];x=max(0,a-40);y=min(len(s),b+40);sv=tc(tk,s[x:y])-tc(tk,s[x:a]+new+s[b:y])
   if sv>0:raw.append((a,b,new,sv,n))
 raw.sort(key=lambda z:(-z[3],-z[4],z[0]));sel=[]
 for z in raw:
  if all(z[1]<=q[0] or z[0]>=q[1] for q in sel):sel.append(z)
 sel.sort();o=[];p=0
 for a,b,new,_,_ in sel:o += [s[p:a],new];p=b
 o.append(s[p:]);v="".join(o)
 return min([s,v],key=lambda q:(cc(tk,q),tc(tk,q)))
res={"version":"U10 fast verified top-saving rules","considered":len(cand),"accepted":len(rules),"models":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=CB=CT=0
  for r in te[:1200]:
   p=prompt(r);v=transform(p,tk);B+=tc(tk,p);T+=tc(tk,v);CB+=cc(tk,p);CT+=cc(tk,v)
  res["models"][name]={"content_pct":100*(B-T)/B,"chat_pct":100*(CB-CT)/CB}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u10_fast_verified.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));open("e2e/acp_u10_fast_audit.json","w",encoding="utf8").write(json.dumps(audit,ensure_ascii=False,indent=2));print("ACP_U10_FAST="+json.dumps(res,ensure_ascii=False),flush=True)
