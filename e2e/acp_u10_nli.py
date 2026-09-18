#!/usr/bin/env python3
import csv,io,json,os,re,random,urllib.request,math
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer,AutoModelForSequenceClassification,AutoTokenizer as AT

URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
DICT="e2e/acp_u8_dictionary.json"
NLI="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4-mini","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]+");DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
RISK=set("""السؤال الاجابة الإجابة اختر الصحيحة الصحيح الخاطئة الخاطئ خطأ خطا صح صحيح خاطئ الخيارات أعلاه اعلاه جواب ما ماذا يلي سبق عدا سوى باستثناء استثناء جميع كل أي ايا أيا لا شيء شئ مما
ليس ليست لم لن دون بدون ينفي تنفي نفي عدم غير قبل بعد منذ خلال فور فورا الآن حاليا اليوم غدا أمس ساعة ساعات يوم أيام اسبوع أسبوع اسابيع أسابيع شهر شهور سنة سنوات
الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار
جرعة جرعات وحدة وحدات ملغ ملغم مليغرام مليلتر ملل يوميا مرتين ثلاث مرات
حامل الحمل حمل حوامل رضاعة مرضعة حساسية تحسس استبعاد يستبعد منع ممنوع يحظر
أقل اقل أكثر اكثر فوق تحت نحو تقريبا حوالي""".split())
MANUAL={"ارتفاع ضغط الدم":"HTN","ضغط الدم":"BP","مرض السكري":"diabetes","داء السكري":"diabetes","السكري من النوع الأول":"T1DM","السكري من النوع الثاني":"T2DM","مرض الكلى المزمن":"CKD","تخطيط القلب الكهربائي":"ECG","التصوير بالرنين المغناطيسي":"MRI","التصوير المقطعي المحوسب":"CT","مرض الانسداد الرئوي المزمن":"COPD","احتشاء عضلة القلب":"MI","الرجفان الأذيني":"AF","مؤشر كتلة الجسم":"BMI","تشبع الأكسجين":"SpO2","تعداد الدم الكامل":"CBC","الحماض الكيتوني السكري":"DKA","فيروس نقص المناعة البشرية":"HIV","التهاب المسالك البولية":"UTI"}
def norm(s):
 s=DIAC.sub("",s).replace("ـ","").replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي");return " ".join(re.sub(r"[^\u0621-\u063A\u0641-\u064A ]+"," ",s).split())
rn={norm(x) for x in RISK}
raw=json.load(open(DICT,encoding="utf8"))["rules"];rules={}
for x in raw:
 a=" ".join(x["ar"].split())
 if re.search(r"\d",a) or set(norm(a).split())&rn:continue
 rules[tuple(a.split())]=x["en"]
for a,e in MANUAL.items():rules[tuple(a.split())]=e

nli_tok=AutoTokenizer.from_pretrained(NLI);nli=AutoModelForSequenceClassification.from_pretrained(NLI,dtype="auto");nli.eval()
ent_id=nli.config.label2id.get("entailment",0)
@torch.no_grad()
def entail(a,b):
 x=nli_tok(a,b,return_tensors="pt",truncation=True,max_length=512)
 z=nli(**x).logits[0].float();return float(F.softmax(z,dim=-1)[ent_id])
def safe_pair(a,b):
 # manual-only abbreviation lines get structural checks but skip NLI if the entire change is a manual alias.
 return min(entail(a,b),entail(b,a))

CAL=[
("ألم في الخاصرة اليمنى دون حمى.","Pain in the right ventricle without fever.",False),
("ضغط الدم 90/60 mmHg ولا توجد دوخة.","Blood pressure is 90/60 mmHg and there's no duct.",False),
("لا تعط الدواء قبل استبعاد الحمل.","Do not give the medicine before the pregnancy is terminated.",False),
("تشبع الأكسجين 88% في الهواء المحيط.","88% of oxygen is saturated in the ocean air.",False),
("ألم في الركبة اليسرى منذ ثلاثة أيام.","Left knee pain for three days.",True),
("يتناول المريض 5 mg من الوارفارين يوميا.","The patient takes 5 mg of warfarin daily.",True),
("تشبع الأكسجين 92%.","Oxygen saturation is 92%.",True),
("ضغط الدم 160/100 mmHg.","Blood pressure is 160/100 mmHg.",True)
]
cal=[{"a":a,"b":b,"expected_safe":y,"bidirectional_entail":safe_pair(a,b)} for a,b,y in CAL]
good=[x["bidirectional_entail"] for x in cal if x["expected_safe"]];bad=[x["bidirectional_entail"] for x in cal if not x["expected_safe"]]
# Conservative threshold: halfway between weakest known-good and strongest known-bad when separable; else fixed high.
if good and bad and min(good)>max(bad):TH=(min(good)+max(bad))/2
else:TH=0.68

def load():
 raw=urllib.request.urlopen(URL,timeout=120).read().decode("utf-8-sig","replace");return list(csv.DictReader(io.StringIO(raw)))
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
def candidate_line(line,tk):
 ms=list(AR.finditer(line));w=[m.group(0) for m in ms];prot=set()
 for i,x in enumerate(w):
  if norm(x) in rn:prot.update(range(max(0,i-2),min(len(w),i+3)))
 raw=[]
 for i in range(len(w)):
  for L in (4,3,2,1):
   if i+L>len(w) or set(range(i,i+L))&prot:continue
   k=tuple(w[i:i+L])
   if k not in rules:continue
   s,e=ms[i].start(),ms[i+L-1].end();new=rules[k];a=max(0,s-40);b=min(len(line),e+40)
   sv=tc(tk,line[a:b])-tc(tk,line[a:s]+new+line[e:b])
   if sv>0:raw.append((s,e,new,sv,L,k))
 raw.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
 for x in raw:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];p=0;only_manual=True
 for s,e,new,_,_,k in sel:
  o += [line[p:s],new];p=e
  if " ".join(k) not in MANUAL:only_manual=False
 o.append(line[p:]);v="".join(o)
 return v,len(sel),only_manual
def transform(text,tk):
 out=[];accepted=0;rejected=0;scores=[]
 for line in text.splitlines():
  v,k,manual=candidate_line(line,tk)
  if not k or v==line:out.append(line);continue
  if manual:ok=True;score=1.0
  else:
   score=safe_pair(line,v);ok=score>=TH
  scores.append(score)
  if ok:out.append(v);accepted+=k
  else:out.append(line);rejected+=k
 v="\n".join(out)
 if cc(tk,v)>cc(tk,text):return text,0,rejected,scores
 return v,accepted,rejected,scores
rs=load();res={"version":"U10 bidirectional NLI safety gate","nli":NLI,"threshold":TH,"calibration":cal,"models":{}}
for name,mid in MODELS:
 try:
  tk=AT.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=CB=CT=ac=rj=0;ss=[]
  for r in rs[:200]:
   p=prompt(r);v,a,b,s=transform(p,tk);B+=tc(tk,p);T+=tc(tk,v);CB+=cc(tk,p);CT+=cc(tk,v);ac+=a;rj+=b;ss+=s
  res["models"][name]={"content_pct":100*(B-T)/B,"chat_pct":100*(CB-CT)/CB,"accepted_replacements":ac,"rejected_replacements":rj,"mean_entail_score":sum(ss)/len(ss) if ss else None,"no_regression":T<=B and CT<=CB}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u10_nli.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U10_NLI="+json.dumps(res,ensure_ascii=False),flush=True)
