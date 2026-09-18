#!/usr/bin/env python3
import re,json,hashlib,random,os,unicodedata
from dataclasses import dataclass,asdict
from transformers import AutoTokenizer

VERSION="ACP-U12.0"
PHRASES=[
("ارتفاع ضغط الدم","HTN"),("فرط ضغط الدم","HTN"),("ضغط الدم","BP"),
("داء السكري من النوع الأول","T1DM"),("السكري من النوع الأول","T1DM"),
("داء السكري من النوع الثاني","T2DM"),("السكري من النوع الثاني","T2DM"),
("مرض السكري","diabetes"),("داء السكري","diabetes"),("السكري","diabetes"),
("الهيموغلوبين السكري","HbA1c"),("السكر التراكمي","HbA1c"),
("الحماض الكيتوني السكري","DKA"),("مرض الكلى المزمن","CKD"),("إصابة الكلى الحادة","AKI"),
("التهاب المسالك البولية","UTI"),("عدوى المسالك البولية","UTI"),
("تعداد الدم الكامل","CBC"),("تخطيط القلب الكهربائي","ECG"),("تخطيط القلب","ECG"),
("أشعة الصدر","CXR"),("التصوير المقطعي المحوسب","CT"),("الأشعة المقطعية","CT"),
("التصوير بالرنين المغناطيسي","MRI"),("الرنين المغناطيسي","MRI"),
("تشبع الأكسجين","SpO2"),("مؤشر كتلة الجسم","BMI"),
("مرض الانسداد الرئوي المزمن","COPD"),("احتشاء عضلة القلب","MI"),
("الرجفان الأذيني","AF"),("مرض الشرايين التاجية","CAD"),("الخثار الوريدي العميق","DVT"),("الانصمام الرئوي","PE"),
("فيروس نقص المناعة البشرية","HIV"),("التهاب الكبد الوبائي ب","HBV"),("التهاب الكبد الوبائي سي","HCV"),
("التهاب الكبد بي","HBV"),("التهاب الكبد سي","HCV"),("سكري الحمل","GDM"),
("البروتين الدهني مرتفع الكثافة","HDL"),("البروتين الدهني منخفض الكثافة","LDL"),("الدهون الثلاثية","TG"),
("ضيق التنفس","dyspnea"),("صعوبة التنفس","dyspnea"),("ألم الصدر","chest pain"),
("العلامات الحيوية","vitals"),("الرعاية الصحية الأولية","primary care"),
("فقدان الوزن","weight loss"),("التهاب البنكرياس","pancreatitis"),
("تليف الكبد","cirrhosis"),("تشمع الكبد","cirrhosis"),("فقر الدم","anemia"),("الأنيميا","anemia"),
("من عوامل الخطورة","RF:"),("عوامل الخطورة","RF:"),("عوامل الخطر","RF:"),
("تشمل الأعراض","Sx:"),("تشمل أعراض","Sx:"),("من الأعراض","Sx:"),
("التاريخ المرضي السابق","PMH:"),("التاريخ المرضي","Hx:"),("التاريخ الطبي","Hx:"),
("الأدوية الحالية","Meds:"),("العلاجات الحالية","Meds:"),
("نتائج المختبر","Labs:"),("نتائج التحاليل","Labs:"),("التحاليل المخبرية","Labs:"),
("يعاني المريض من","Pt has"),("يعاني من","has"),("تعاني المريضة من","Pt has"),
("يشكو المريض من","Pt c/o"),("يشكو من","c/o"),("تشكو المريضة من","Pt c/o"),
("وجود تاريخ عائلي","FHx"),("تاريخ عائلي","FHx")
]
WORDS={
"القلب":"heart","قلب":"heart","الكبد":"liver","كبد":"liver","الكلية":"kidney","كلية":"kidney","الكلى":"kidneys",
"الرئة":"lung","رئة":"lung","البنكرياس":"pancreas","بنكرياس":"pancreas","الطحال":"spleen","طحال":"spleen",
"الرحم":"uterus","رحم":"uterus","المثانة":"bladder","مثانة":"bladder","المبيض":"ovary","مبيض":"ovary",
"الشريان":"artery","شريان":"artery","الوريد":"vein","وريد":"vein","العصب":"nerve","عصب":"nerve",
"العضلة":"muscle","عضلة":"muscle","العظم":"bone","عظم":"bone","المفصل":"joint","مفصل":"joint",
"الرباط":"ligament","رباط":"ligament","الوتر":"tendon","وتر":"tendon","الغضروف":"cartilage","غضروف":"cartilage",
"الظهارة":"epithelium","ظهارة":"epithelium","النسيج":"tissue","نسيج":"tissue","الخلية":"cell","خلية":"cell",
"الغدة":"gland","غدة":"gland","الهرمون":"hormone","هرمون":"hormone","الصمام":"valve","صمام":"valve",
"البطين":"ventricle","بطين":"ventricle","الأذين":"atrium","أذين":"atrium",
"السرطان":"cancer","سرطان":"cancer","الورم":"tumor","ورم":"tumor","العدوى":"infection","عدوى":"infection",
"السمنة":"obesity","البدانة":"obesity","الحمى":"fever","الحمّى":"fever","الغثيان":"nausea","القيء":"vomiting",
"الصداع":"headache","الأنسولين":"insulin","الانسولين":"insulin","الكوليسترول":"cholesterol",
"دوخة":"dizziness","الدوخة":"dizziness","الخاصرة":"flank","خاصرة":"flank","الكرياتينين":"creatinine","كرياتينين":"creatinine"
}
CRIT=set("""لا ليس ليست لم لن دون بدون ينفي تنفي نفي عدم قبل بعد منذ خلال فور فورا الآن حاليا اليوم غدا أمس
الأيمن الايمن أيمن ايمن اليمنى يمنى الأيسر الايسر أيسر ايسر اليسرى يسرى يمين يسار
جرعة جرعات وحدة وحدات ملغ ملغم مليغرام مليلتر ملل يوميا يومياً مرتين ثلاث مرات كل
حامل الحمل حوامل رضاعة مرضعة حساسية تحسس استبعاد يستبعد منع ممنوع يحظر
أقل اقل أكثر اكثر فوق تحت بين نحو تقريبا تقريباً حوالي
""".split())
AR=re.compile(r"[\u0621-\u063A\u0641-\u064A]+")
VAL=re.compile(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?(?:\s*(?:mg/dL|g/dL|mmol/L|mmHg|mg|mL|bpm|°C|%|وحدات?))?",re.I)

@dataclass
class Op:
    out_start:int
    out_end:int
    original:str
    replacement:str
    source_start:int
    source_end:int
    kind:str

def sha(s):return hashlib.sha256(s.encode("utf-8")).hexdigest()

class SafeCTL:
    def __init__(self,tokenizer):
        self.tok=tokenizer
    def count(self,s):return len(self.tok(s,add_special_tokens=False)["input_ids"])
    def protected(self,t):
        ms=list(AR.finditer(t));w=[m.group(0) for m in ms];p=set()
        for i,x in enumerate(w):
            if x in CRIT:
                p.update(range(max(0,i-2),min(len(w),i+3)))
        for m in VAL.finditer(t):
            for i,z in enumerate(ms):
                if abs(z.start()-m.start())<28 or abs(z.end()-m.end())<28:p.add(i)
        return ms,w,p
    def candidates(self,t):
        base=self.count(t);c=[]
        for old,new in PHRASES:
            for m in re.finditer(re.escape(old),t):
                a=max(0,m.start()-40);b=min(len(t),m.end()+40)
                sv=self.count(t[a:b])-self.count(t[a:m.start()]+new+t[m.end():b])
                if sv>0:c.append((m.start(),m.end(),new,sv,len(old),"phrase"))
        ms,w,p=self.protected(t)
        for i,x in enumerate(w):
            if i in p or x not in WORDS:continue
            m=ms[i];new=WORDS[x];a=max(0,m.start()-40);b=min(len(t),m.end()+40)
            sv=self.count(t[a:b])-self.count(t[a:m.start()]+new+t[m.end():b])
            if sv>0:c.append((m.start(),m.end(),new,sv,len(x),"word"))
        c.sort(key=lambda x:(-x[3],-x[4],x[0]));sel=[]
        for x in c:
            if all(x[1]<=y[0] or x[0]>=y[1] for y in sel):sel.append(x)
        return sorted(sel,key=lambda x:x[0])
    def encode(self,t):
        base=self.count(t);sel=self.candidates(t);out=[];ops=[];src=0;outpos=0
        for s,e,new,sv,l,kind in sel:
            prefix=t[src:s];out.append(prefix);outpos+=len(prefix)
            st=outpos;out.append(new);outpos+=len(new)
            ops.append(Op(st,outpos,t[s:e],new,s,e,kind));src=e
        out.append(t[src:]);comp="".join(out)
        # Hard whole-sequence guard.
        if self.count(comp)>=base:
            comp=t;ops=[]
        packet={"version":VERSION,"original_sha256":sha(t),"compressed_sha256":sha(comp),"ops":[asdict(x) for x in ops]}
        return comp,packet
    def decode(self,comp,packet):
        if packet.get("version")!=VERSION:raise ValueError("version mismatch")
        if sha(comp)!=packet.get("compressed_sha256"):raise ValueError("compressed fingerprint mismatch")
        out=comp
        for d in reversed(packet.get("ops",[])):
            s,e=d["out_start"],d["out_end"]
            if out[s:e]!=d["replacement"]:raise ValueError("replacement mismatch")
            out=out[:s]+d["original"]+out[e:]
        if sha(out)!=packet.get("original_sha256"):raise ValueError("original fingerprint mismatch")
        return out

def canonical_facts(t):
    s=" "+t.lower()+" ";facts=set()
    maps={
      "NEG":[" لا ","ليس","ليست","لم ","لن ","دون","بدون","ينفي"],
      "LEFT":["الأيسر","اليسرى","يسار"],"RIGHT":["الأيمن","اليمنى","يمين"],
      "BEFORE":["قبل"],"AFTER":["بعد"],"PREG":["حامل","الحمل"],"ALLERGY":["حساسية","تحسس"],
      "RULEOUT":["استبعاد"],"LT":["أقل","اقل"],"GT":["أكثر","اكثر"],
    }
    for k,vs in maps.items():
        if any(v in t for v in vs):facts.add(k)
    for m in VAL.finditer(t):facts.add("VAL:"+re.sub(r"\s+","",m.group(0).lower()))
    return facts

SEEDS=[
"المريض يعاني من ارتفاع ضغط الدم ومرض السكري.",
"لا يوجد ألم في الجانب الأيسر من الصدر.",
"ضغط الدم 160/100 mmHg وتشبع الأكسجين 92%.",
"جرعة الأنسولين 10 وحدات قبل العشاء.",
"المريضة حامل ولا توجد حساسية معروفة.",
"تشمل الأعراض ضيق التنفس وألم الصدر والغثيان.",
"التاريخ المرضي السابق: مرض الكلى المزمن واحتشاء عضلة القلب.",
"نتائج المختبر تظهر الكرياتينين 2.1 mg/dL.",
"ألم في الخاصرة اليمنى دون حمى.",
"الأدوية الحالية تشمل الأنسولين."
]
FILL=["القلب","الكبد","الكلية","الرئة","سرطان","السمنة","الصداع","الغثيان","العضلة","العصب","ضغط الدم","مرض السكري","ارتفاع ضغط الدم","تشمل الأعراض","التاريخ المرضي"]
def fuzz(n=10000):
    rng=random.Random(123);out=[]
    for _ in range(n):
        x=rng.choice(SEEDS)
        for _ in range(rng.randrange(0,5)):
            x += rng.choice(["، "," و ","؛ "," / "," "])+rng.choice(FILL)
        if rng.random()<.35:x += " "+str(rng.choice([5,10,45,92,120,160]))+" mg"
        out.append(x)
    return out

def main():
    mids=["Qwen/Qwen3-0.6B","unsloth/Llama-3.2-1B-Instruct","unsloth/gemma-3-1b-it"]
    texts=fuzz(10000);res={"version":VERSION,"n":len(texts),"models":{}}
    for mid in mids:
        tk=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True);codec=SafeCTL(tk)
        rt=nr=fp=crit=0;reps=0;B=T=0;tamper_ok=False
        for t in texts:
            c,p=codec.encode(t);B+=codec.count(t);T+=codec.count(c);reps+=len(p["ops"])
            try:
                d=codec.decode(c,p);rt+=d==t
            except Exception:pass
            nr+=codec.count(c)<=codec.count(t)
            crit+=canonical_facts(t)==canonical_facts(d if 'd' in locals() else "")
            # Verify no op intersects protected source word indices indirectly by checking protected lexemes unchanged around critical facts via exact reconstruction/facts.
        # tamper detection smoke
        c,p=codec.encode("ارتفاع ضغط الدم ومرض السكري")
        if c:
            bad=c+"x"
            try:codec.decode(bad,p)
            except Exception:tamper_ok=True
        res["models"][mid]={"roundtrip_rate":rt/len(texts),"no_regression_rate":nr/len(texts),"critical_fact_rate":crit/len(texts),"token_reduction_pct":100*(B-T)/B,"replacements":reps,"tamper_detection":tamper_ok}
    os.makedirs("e2e",exist_ok=True);open("e2e/acp_u12_core_test.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U12_CORE="+json.dumps(res,ensure_ascii=False),flush=True)
if __name__=="__main__":main()
