#!/usr/bin/env python3
import csv,io,json,os,re,random,urllib.request,gc,difflib,statistics as st
from collections import defaultdict
import torch
from transformers import AutoTokenizer,AutoModelForSeq2SeqLM

SEED=101
random.seed(SEED);torch.manual_seed(SEED)
TEST_URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
DICT_PATH="e2e/acp_u8_dictionary.json"
NLLB="facebook/nllb-200-distilled-600M"
BACK="Helsinki-NLP/opus-mt-en-ar"
MODELS=[
("Qwen3","Qwen/Qwen3-0.6B"),
("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),
("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),
("Gemma3","unsloth/gemma-3-1b-it"),
("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),
("Phi4-mini","microsoft/Phi-4-mini-instruct"),
("Falcon3","tiiuae/Falcon3-1B-Instruct"),
("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")
]
ARWORD=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
NUMUNIT=re.compile(r"\d|(?:mg|ml|mmhg|bpm|g/dl|mg/dl|mmol/l|°c|%)",re.I)

# Never infer/translate these freely. Exact phrase whitelist below is checked first.
RISK_WORDS=set("""السؤال الاجابة الإجابة اختر الصحيحة الصحيح الخاطئة الخاطئ خطأ خطا صح صحيح خاطئ الخيارات أعلاه اعلاه جواب إجابة اجابة ما ماذا يلي سبق عدا سوى باستثناء استثناء جميع كل أي ايا أيا لا شيء شئ شيء مما\nلا ليس ليست لم لن دون بدون ينفي تنفي نفي عدم غير سوى عدا قبل بعد منذ خلال فور فورا الآن حاليا اليوم غدا أمس ساعة ساعات يوم أيام اسبوع أسبوع اسابيع أسابيع شهر شهور سنة سنوات
الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار
جرعة جرعات وحدة وحدات ملغ ملغم مليغرام مليلتر ملل يوميا يومياً مرتين ثلاث مرات كل
حامل الحمل حمل حوامل رضاعة مرضعة حساسية تحسس تحسساً حساسيةً استبعاد يستبعد منع ممنوع يحظر
أقل اقل أكثر اكثر فوق تحت بين نحو تقريبا تقريباً حوالي
""".split())

# These mappings are clinically conventional and allowed even if a risk-like token occurs.
MANUAL={
"ارتفاع ضغط الدم":"HTN","فرط ضغط الدم":"HTN","ضغط الدم":"BP",
"داء السكري من النوع الأول":"T1DM","السكري من النوع الأول":"T1DM",
"داء السكري من النوع الثاني":"T2DM","السكري من النوع الثاني":"T2DM",
"مرض السكري":"diabetes","داء السكري":"diabetes",
"الهيموغلوبين السكري":"HbA1c","السكر التراكمي":"HbA1c",
"الحماض الكيتوني السكري":"DKA","مرض الكلى المزمن":"CKD",
"التهاب المسالك البولية":"UTI","عدوى المسالك البولية":"UTI",
"تعداد الدم الكامل":"CBC","تخطيط القلب الكهربائي":"ECG","تخطيط القلب":"ECG",
"أشعة الصدر":"CXR","التصوير المقطعي المحوسب":"CT","الأشعة المقطعية":"CT",
"التصوير بالرنين المغناطيسي":"MRI","الرنين المغناطيسي":"MRI",
"تشبع الأكسجين":"SpO2","مؤشر كتلة الجسم":"BMI",
"مرض الانسداد الرئوي المزمن":"COPD","احتشاء عضلة القلب":"MI",
"الرجفان الأذيني":"AF","مرض الشرايين التاجية":"CAD",
"الخثار الوريدي العميق":"DVT","الانصمام الرئوي":"PE",
"فيروس نقص المناعة البشرية":"HIV","التهاب الكبد بي":"HBV","التهاب الكبد سي":"HCV",
"سكري الحمل":"GDM","إصابة الكلى الحادة":"AKI","الفشل الكلوي الحاد":"AKI",
"البروتين الدهني مرتفع الكثافة":"HDL","البروتين الدهني منخفض الكثافة":"LDL",
"الدهون الثلاثية":"TG"
}

def nar(s):
 s=DIAC.sub("",s).replace("ـ","").replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي")
 s=re.sub(r"[^\u0621-\u063A\u0641-\u064A ]+"," ",s);return " ".join(s.split())
def nen(s):
 s=s.lower();s=re.sub(r"\b(the|a|an)\b"," ",s);s=re.sub(r"[^a-z0-9%/]+"," ",s);return " ".join(s.split())
def toks(s):return set(s.split())
def sim(a,b):
 a,b=a.strip(),b.strip()
 if not a or not b:return 0.0
 r=difflib.SequenceMatcher(None,a,b).ratio()
 A,B=toks(a),toks(b);j=len(A&B)/max(1,len(A|B))
 return max(r,j)

def translate_nllb(src):
 tok=AutoTokenizer.from_pretrained(NLLB,src_lang="arb_Arab")
 m=AutoModelForSeq2SeqLM.from_pretrained(NLLB,dtype="auto",low_cpu_mem_usage=True);m.eval()
 bos=tok.convert_tokens_to_ids("eng_Latn");out=[]
 for i in range(0,len(src),24):
  x=tok(src[i:i+24],return_tensors="pt",padding=True,truncation=True,max_length=96)
  with torch.no_grad():g=m.generate(**x,forced_bos_token_id=bos,max_new_tokens=64,num_beams=1)
  out+=tok.batch_decode(g,skip_special_tokens=True)
 del m,tok;gc.collect();return out
def backtranslate(src):
 tok=AutoTokenizer.from_pretrained(BACK)
 m=AutoModelForSeq2SeqLM.from_pretrained(BACK,dtype="auto",low_cpu_mem_usage=True);m.eval();out=[]
 for i in range(0,len(src),32):
  x=tok(src[i:i+32],return_tensors="pt",padding=True,truncation=True,max_length=80)
  with torch.no_grad():g=m.generate(**x,max_new_tokens=64,num_beams=1)
  out+=tok.batch_decode(g,skip_special_tokens=True)
 del m,tok;gc.collect();return out

raw=json.load(open(DICT_PATH,encoding="utf8"))["rules"]
# Deduplicate exact source phrase, shortest target.
by={}
for x in raw:
 ar=" ".join(x["ar"].split());en=" ".join(x["en"].split())
 if ar not in by or len(en)<len(by[ar]):by[ar]=en
items=list(by.items())

# High-risk learned phrases are rejected before expensive validation.
candidate=[];rejected_risk=[]
for ar,en in items:
 ws=set(nar(ar).split())
 if NUMUNIT.search(ar) or (ws & {nar(x) for x in RISK_WORDS}):
  rejected_risk.append((ar,en))
 else:candidate.append((ar,en))

fwd=translate_nllb([x[0] for x in candidate])
back=backtranslate([x[1] for x in candidate])
accepted={};audit=[]
for (ar,en),nllb,bt in zip(candidate,fwd,back):
 fs=sim(nen(en),nen(nllb));bs=sim(nar(ar),nar(bt))
 # Require independent forward agreement AND round-trip recovery.
 ok=(fs>=0.56 and bs>=0.50)
 if ok:accepted[ar]=en
 audit.append({"ar":ar,"en":en,"nllb":nllb,"back":bt,"forward_sim":fs,"back_sim":bs,"accepted":ok})
accepted.update(MANUAL)

def loadrows():
 raw=urllib.request.urlopen(TEST_URL,timeout=120).read().decode("utf-8-sig","replace")
 return list(csv.DictReader(io.StringIO(raw)))
def prompt(r):
 z=["السؤال: "+r["Question"]]
 for L in "ABCDEF":
  v=(r.get("Option "+L) or "").strip()
  if v:z.append(f"{L}) {v}")
 z+=["اختر حرف الإجابة الصحيحة فقط من الخيارات أعلاه.","الإجابة:"]
 return "\n".join(z)
def tc(tok,t):return len(tok(t,add_special_tokens=False)["input_ids"])
def chatids(tok,t):
 try:return tok.apply_chat_template([{"role":"user","content":t}],tokenize=True,add_generation_prompt=True)
 except:return tok(t,add_special_tokens=False)["input_ids"]
def cc(tok,t):return len(chatids(tok,t))
def ortho(t):
 t=DIAC.sub("",t).replace("ـ","")
 t=t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩","0123456789"))
 t=t.replace("،",",").replace("؛",";")
 t=re.sub(r"[ \t]+"," ",t);t=re.sub(r" +([,;:.!?])",r"\1",t);return t

rules={tuple(k.split()):v for k,v in accepted.items()}
risknorm={nar(x) for x in RISK_WORDS}
def wordinfo(t):
 ms=list(ARWORD.finditer(t));w=[m.group(0) for m in ms]
 prot=set()
 for i,x in enumerate(w):
  nx=nar(x)
  if nx in risknorm:
   for j in range(max(0,i-2),min(len(w),i+3)):prot.add(j)
 # protect any word within two tokens of a number/unit span
 for m in re.finditer(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?|\b(?:mg|mL|mmHg|bpm|g/dL|mg/dL|mmol/L)\b|%",t,re.I):
  for i,z in enumerate(ms):
   if abs(z.start()-m.start())<28 or abs(z.end()-m.end())<28:prot.add(i)
 return ms,w,prot
def transform(t,tok):
 basec=tc(tok,t);basechat=cc(tok,t)
 ms,w,prot=wordinfo(t);raw=[]
 for i in range(len(w)):
  for n in (4,3,2,1):
   if i+n>len(w):continue
   idx=set(range(i,i+n))
   if idx & prot:continue
   k=tuple(w[i:i+n])
   if k not in rules:continue
   s,e=ms[i].start(),ms[i+n-1].end();new=rules[k]
   a=max(0,s-48);b=min(len(t),e+48)
   sv=tc(tok,t[a:b])-tc(tok,t[a:s]+new+t[e:b])
   if sv>0:raw.append((s,e,new,sv,n))
 raw.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
 for x in raw:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];p=0
 for s,e,new,sv,n in sel:o += [t[p:s],new];p=e
 o.append(t[p:]);c=ortho("".join(o))
 candidates=[t,ortho(t),c]
 best=min(candidates,key=lambda x:(cc(tok,x),tc(tok,x)))
 if cc(tok,best)>basechat:return t,basec,basec,basechat,basechat,0
 return best,basec,tc(tok,best),basechat,cc(tok,best),len(sel)

rows=loadrows()
res={"version":"ACP-U10 verified clinical semantic compression","source_rules":len(items),"candidate_after_risk_filter":len(candidate),"accepted_verified_rules":len(accepted),"manual_rules":len(MANUAL),"risk_rejected":len(rejected_risk),"models":{}}
for name,mid in MODELS:
 try:
  tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
  B=T=CB=CT=rep=0
  for r in rows[:1200]:
   p=prompt(r);tr,b,n,cb,ct,k=transform(p,tok);B+=b;T+=n;CB+=cb;CT+=ct;rep+=k
  res["models"][name]={"model_id":mid,"content_reduction_pct":100*(B-T)/B,"chat_reduction_pct":100*(CB-CT)/CB,"no_regression":T<=B and CT<=CB,"replacements":rep}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u10_dictionary.json","w",encoding="utf8").write(json.dumps({"rules":[{"ar":k,"en":v} for k,v in accepted.items()]},ensure_ascii=False,indent=2))
open("e2e/acp_u10_rule_audit.json","w",encoding="utf8").write(json.dumps(audit,ensure_ascii=False,indent=2))
open("e2e/acp_u10_results.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2))
print("ACP_U10="+json.dumps(res,ensure_ascii=False),flush=True)
