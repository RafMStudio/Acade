#!/usr/bin/env python3
import csv,io,json,os,re,urllib.request
from transformers import AutoTokenizer
URL="https://raw.githubusercontent.com/nyuad-cai/MedAraBench/main/medarabench-test_split.csv"
DICT="e2e/acp_u8_dictionary.json"
MODELS=[("Qwen3","Qwen/Qwen3-0.6B"),("Qwen2.5","Qwen/Qwen2.5-0.5B-Instruct"),("Llama3.2","unsloth/Llama-3.2-1B-Instruct"),("Gemma3","unsloth/gemma-3-1b-it"),("Mistral","mistralai/Mistral-7B-Instruct-v0.3"),("Phi4-mini","microsoft/Phi-4-mini-instruct"),("Falcon3","tiiuae/Falcon3-1B-Instruct"),("DeepSeek","deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B")]
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]+");DIAC=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
RISK=set("""السؤال الاجابة الإجابة اختر الصحيحة الصحيح الخاطئة الخاطئ خطأ خطا صح صحيح خاطئ الخيارات أعلاه اعلاه جواب ما ماذا يلي سبق عدا سوى باستثناء استثناء جميع كل أي ايا أيا لا شيء شئ مما
ليس ليست لم لن دون بدون ينفي تنفي نفي عدم غير قبل بعد منذ خلال فور فورا الآن حاليا اليوم غدا أمس ساعة ساعات يوم أيام اسبوع أسبوع اسابيع أسابيع شهر شهور سنة سنوات
الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار
جرعة جرعات وحدة وحدات ملغ ملغم مليغرام مليلتر ملل يوميا مرتين ثلاث مرات
حامل الحمل حمل حوامل رضاعة مرضعة حساسية تحسس استبعاد يستبعد منع ممنوع يحظر
أقل اقل أكثر اكثر فوق تحت نحو تقريبا حوالي""".split())
MANUAL={"ارتفاع ضغط الدم":"HTN","ضغط الدم":"BP","مرض السكري":"diabetes","داء السكري":"diabetes","السكري من النوع الأول":"T1DM","السكري من النوع الثاني":"T2DM","مرض الكلى المزمن":"CKD","تخطيط القلب الكهربائي":"ECG","التصوير بالرنين المغناطيسي":"MRI","التصوير المقطعي المحوسب":"CT","مرض الانسداد الرئوي المزمن":"COPD","احتشاء عضلة القلب":"MI","الرجفان الأذيني":"AF","مؤشر كتلة الجسم":"BMI","تشبع الأكسجين":"SpO2","تعداد الدم الكامل":"CBC","الحماض الكيتوني السكري":"DKA","فيروس نقص المناعة البشرية":"HIV","التهاب المسالك البولية":"UTI"}
def n(s):
 s=DIAC.sub("",s).replace("ـ","").replace("أ","ا").replace("إ","ا").replace("آ","ا").replace("ى","ي");return " ".join(re.sub(r"[^\u0621-\u063A\u0641-\u064A ]+"," ",s).split())
rn={n(x) for x in RISK}
d=json.load(open(DICT,encoding="utf8"))["rules"];rules={}
rej=0
for x in d:
 a=" ".join(x["ar"].split());e=x["en"];w=set(n(a).split())
 if re.search(r"\d",a) or w&rn:rej+=1;continue
 rules[tuple(a.split())]=e
for a,e in MANUAL.items():rules[tuple(a.split())]=e
def rows():
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
def transform(t,tk):
 ms=list(AR.finditer(t));w=[m.group(0) for m in ms];prot=set()
 for i,x in enumerate(w):
  if n(x) in rn:
   prot.update(range(max(0,i-2),min(len(w),i+3)))
 raw=[]
 for i in range(len(w)):
  for L in (4,3,2,1):
   if i+L>len(w) or set(range(i,i+L))&prot:continue
   k=tuple(w[i:i+L])
   if k not in rules:continue
   s,e=ms[i].start(),ms[i+L-1].end();new=rules[k];a=max(0,s-40);b=min(len(t),e+40)
   sv=tc(tk,t[a:b])-tc(tk,t[a:s]+new+t[e:b])
   if sv>0:raw.append((s,e,new,sv,L))
 raw.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
 for x in raw:
  if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
 sel.sort();o=[];p=0
 for s,e,new,_,_ in sel:o += [t[p:s],new];p=e
 o.append(t[p:]);v="".join(o)
 return min([t,v],key=lambda s:(cc(tk,s),tc(tk,s))),len(sel)
rs=rows();res={"version":"U10 risk-filter frontier","rules":len(rules),"rejected":rej,"models":{}}
for name,mid in MODELS:
 try:
  tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);B=T=CB=CT=rep=0
  for r in rs[:1200]:
   p=prompt(r);v,k=transform(p,tk);B+=tc(tk,p);T+=tc(tk,v);CB+=cc(tk,p);CT+=cc(tk,v);rep+=k
  res["models"][name]={"content_pct":100*(B-T)/B,"chat_pct":100*(CB-CT)/CB,"replacements":rep,"no_regression":T<=B and CT<=CB}
 except Exception as e:res["models"][name]={"error":repr(e)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u10_frontier.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U10_FRONTIER="+json.dumps(res,ensure_ascii=False),flush=True)
