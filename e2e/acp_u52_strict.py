#!/usr/bin/env python3
import csv, io, json, os, re, random, statistics as st, time, urllib.request, gc, math
from dataclasses import dataclass
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForCausalLM

SEED=19
random.seed(SEED); torch.manual_seed(SEED)
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

# risk 0 = formatting/orthographic minification
# risk 1 = standard clinical abbreviations / exact medical terms
# risk 2 = broader direct medical interlingua / semantic phrase compaction
BASE_RULES=[
(["داء السكري من النوع الأول","السكري من النوع الأول"],["T1DM"],1),
(["داء السكري من النوع الثاني","السكري من النوع الثاني"],["T2DM"],1),
(["انخفاض سكر الدم","انخفاض السكر في الدم","نقص سكر الدم"],["hypoglycemia"],1),
(["ارتفاع سكر الدم","ارتفاع السكر في الدم"],["hyperglycemia"],1),
(["مستويات السكر في الدم","مستوى السكر في الدم","نسبة السكر في الدم","سكر الدم"],["glucose"],1),
(["الهيموغلوبين السكري","السكر التراكمي"],["HbA1c"],1),
(["الحماض الكيتوني السكري","الحماض الكيتوني"],["DKA"],1),
(["ارتفاع ضغط الدم","فرط ضغط الدم","ضغط الدم المرتفع"],["HTN"],1),
(["ضغط الدم"],["BP"],1),
(["مرض السكري","داء السكري","السكري"],["diabetes"],1),
(["مرض الكلى المزمن","أمراض الكلى المزمنة"],["CKD"],1),
(["الفشل الكلوي","فشل كلوي"],["renal failure"],1),
(["التهاب المسالك البولية","عدوى المسالك البولية"],["UTI"],1),
(["مرض الربو","الربو"],["asthma"],1),
(["ضيق في التنفس","ضيق التنفس","صعوبة التنفس"],["dyspnea"],1),
(["ألم في الصدر","ألم الصدر"],["chest pain"],1),
(["العلامات الحيوية","علامات حيوية"],["vitals"],1),
(["الرعاية الصحية الأولية","الرعاية الأولية"],["primary care"],1),
(["تشبع الأكسجين","إشباع الأكسجين"],["SpO2"],1),
(["تعداد الدم الكامل"],["CBC"],1),
(["تخطيط القلب الكهربائي","تخطيط القلب"],["ECG"],1),
(["أشعة الصدر","الأشعة السينية على الصدر"],["CXR"],1),
(["التصوير المقطعي المحوسب","الأشعة المقطعية"],["CT"],1),
(["التصوير بالرنين المغناطيسي","الرنين المغناطيسي"],["MRI"],1),
(["مرض الانسداد الرئوي المزمن","الانسداد الرئوي المزمن"],["COPD"],1),
(["احتشاء عضلة القلب","النوبة القلبية"],["MI"],1),
(["الرجفان الأذيني"],["AF"],1),
(["مرض الشرايين التاجية","أمراض الشرايين التاجية"],["CAD"],1),
(["الخثار الوريدي العميق","جلطة وريدية عميقة"],["DVT"],1),
(["الانصمام الرئوي","جلطة رئوية"],["PE"],1),
(["التاريخ العائلي","تاريخ عائلي"],["FHx"],1),
(["التاريخ المرضي السابق","الأمراض السابقة"],["PMH"],1),
(["التاريخ المرضي","التاريخ الطبي"],["Hx"],1),
(["عوامل الخطورة","عوامل الخطر"],["risk factors"],1),
(["مؤشر كتلة الجسم","كتلة الجسم"],["BMI"],1),
(["التهاب الكبد بي","فيروس الكبد الوبائي ب"],["HBV"],1),
(["التهاب الكبد سي","فيروس الكبد الوبائي سي"],["HCV"],1),
(["التهاب البنكرياس"],["pancreatitis"],1),
(["متلازمة تكيس المبايض","تكيس المبايض"],["PCOS"],1),
(["فيروس نقص المناعة البشرية"],["HIV"],1),
(["كوفيد 19","كوفيد-19"],["COVID-19"],1),
(["الدهون الثلاثية"],["TG"],1),
(["البروتين الدهني مرتفع الكثافة"],["HDL"],1),
(["البروتين الدهني منخفض الكثافة"],["LDL"],1),
]

LEX = [
(["عضلة","العضلة"],["muscle"],2),(["عضلات","العضلات"],["muscles"],2),
(["عصب","العصب"],["nerve"],2),(["أعصاب","الأعصاب"],["nerves"],2),
(["شريان","الشريان"],["artery"],2),(["شرايين","الشرايين"],["arteries"],2),
(["وريد","الوريد"],["vein"],2),(["أوردة","الأوردة"],["veins"],2),
(["عظم","العظم"],["bone"],2),(["عظام","العظام"],["bones"],2),
(["دم","الدم"],["blood"],2),(["قلب","القلب"],["heart"],2),
(["كبد","الكبد"],["liver"],2),(["كلية","الكلية","الكلى"],["kidney"],2),
(["رئة","الرئة"],["lung"],2),(["رئتين","الرئتين"],["lungs"],2),
(["دماغ","الدماغ"],["brain"],2),(["مخ","المخ"],["brain"],2),
(["جلد","الجلد"],["skin"],2),(["معدة","المعدة"],["stomach"],2),
(["بنكرياس","البنكرياس"],["pancreas"],2),(["طحال","الطحال"],["spleen"],2),
(["رحم","الرحم"],["uterus"],2),(["مبيض","المبيض"],["ovary"],2),
(["مبايض","المبايض"],["ovaries"],2),(["مثانة","المثانة"],["bladder"],2),
(["كلية","الكلية"],["kidney"],2),(["إحليل","الإحليل"],["urethra"],2),
(["حالب","الحالب"],["ureter"],2),(["بلعوم","البلعوم"],["pharynx"],2),
(["حنجرة","الحنجرة"],["larynx"],2),(["قصبة هوائية","القصبة الهوائية"],["trachea"],2),
(["رغامى","الرغامى"],["trachea"],2),(["مريء","المريء"],["esophagus"],2),
(["قولون","القولون"],["colon"],2),(["أمعاء","الأمعاء"],["intestine"],2),
(["مفصل","المفصل"],["joint"],2),(["مفاصل","المفاصل"],["joints"],2),
(["خلية","الخلية"],["cell"],2),(["خلايا","الخلايا"],["cells"],2),
(["نسيج","النسيج"],["tissue"],2),(["أنسجة","الأنسجة"],["tissues"],2),
(["غدة","الغدة"],["gland"],2),(["غدد","الغدد"],["glands"],2),
(["هرمون","الهرمون"],["hormone"],2),(["هرمونات","الهرمونات"],["hormones"],2),
(["سرطان","السرطان"],["cancer"],2),(["ورم","الورم"],["tumor"],2),
(["التهاب","إلتهاب"],["inflammation"],2),(["عدوى","العدوى"],["infection"],2),
(["مريض","المريض"],["patient"],2),(["مرضى","المرضى"],["patients"],2),
(["مرض","المرض"],["disease"],2),(["أمراض","الامراض","الأمراض"],["diseases"],2),
(["علاج","العلاج"],["treatment"],2),(["تشخيص","التشخيص"],["diagnosis"],2),
(["أعراض","الأعراض"],["symptoms"],2),(["عرض","العرض"],["symptom"],2),
(["دواء","الدواء"],["drug"],2),(["أدوية","الأدوية"],["drugs"],2),
(["جرعة","الجرعة"],["dose"],2),(["فحص","الفحص"],["test"],2),
(["فحوصات","الفحوصات"],["tests"],2),(["عملية","العملية"],["procedure"],2),
(["جراحة","الجراحة"],["surgery"],2),(["سكر","السكر"],["glucose"],2),
(["أنسولين","الأنسولين","الانسولين"],["insulin"],2),(["كوليسترول","الكوليسترول"],["cholesterol"],2),
(["سمنة","السمنة","البدانة"],["obesity"],2),(["حمى","الحمى","الحمّى"],["fever"],2),
(["غثيان","الغثيان"],["nausea"],2),(["قيء","القيء"],["vomiting"],2),
(["صداع","الصداع"],["headache"],2),(["ألم","الألم"],["pain"],2),
(["تنفس","التنفس"],["breathing"],2),(["بول","البول"],["urine"],2),
(["صدر","الصدر"],["chest"],2),(["بطن","البطن"],["abdomen"],2),
(["قدم","القدم"],["foot"],2),(["يد","اليد"],["hand"],2),
(["ذراع","الذراع"],["arm"],2),(["ساق","الساق"],["leg"],2),
(["كتف","الكتف"],["shoulder"],2),(["ركبة","الركبة"],["knee"],2),
(["فخذ","الفخذ"],["thigh"],2),(["عنق","العنق"],["neck"],2),
(["رأس","الرأس"],["head"],2),(["لسان","اللسان"],["tongue"],2),
(["عين","العين"],["eye"],2),(["أذن","الأذن"],["ear"],2),
(["أنف","الأنف"],["nose"],2),(["فم","الفم"],["mouth"],2),
(["سن","السن"],["tooth"],2),(["أسنان","الأسنان"],["teeth"],2),
]

LEX += [
(["أمامي","الأمامي","الامامي"],["anterior"],2),(["خلفي","الخلفي"],["posterior"],2),
(["علوي","العلوي"],["superior"],2),(["سفلي","السفلي"],["inferior"],2),
(["إنسي","الإنسي","الانسي"],["medial"],2),(["وحشي","الوحشي"],["lateral"],2),
(["قريب","القريب"],["proximal"],2),(["بعيد","البعيد"],["distal"],2),
(["سطحي","السطحي"],["superficial"],2),(["عميق","العميق"],["deep"],2),
(["داخلي","الداخلي","باطن","الباطن"],["internal"],2),(["خارجي","الخارجي"],["external"],2),
(["أيمن","الأيمن"],["right"],2),(["أيسر","الأيسر"],["left"],2),
(["حسي","الحسي"],["sensory"],2),(["حركي","الحركي"],["motor"],2),
(["عضلي","العضلي"],["muscular"],2),(["عصبي","العصبي"],["neural"],2),
(["ظهارة","الظهارة"],["epithelium"],2),(["ظهاري","الظهاري"],["epithelial"],2),
(["مخاطية","المخاطية"],["mucosa"],2),(["غضروف","الغضروف"],["cartilage"],2),
(["رباط","الرباط"],["ligament"],2),(["أربطة","الأربطة"],["ligaments"],2),
(["وتر","الوتر"],["tendon"],2),(["أوتار","الأوتار"],["tendons"],2),
(["مفصل","المفصل"],["joint"],2),(["مفاصل","المفاصل"],["joints"],2),
(["قناة","القناة"],["duct"],2),(["قنوات","القنوات"],["ducts"],2),
(["سطح","السطح"],["surface"],2),(["أسطح","الأسطح"],["surfaces"],2),
(["حافة","الحافة"],["border"],2),(["حواف","الحواف"],["borders"],2),
(["فرع","الفرع"],["branch"],2),(["فروع","الفروع"],["branches"],2),
(["جزء","الجزء"],["part"],2),(["أجزاء","الأجزاء"],["parts"],2),
(["طبقة","الطبقة"],["layer"],2),(["طبقات","الطبقات"],["layers"],2),
(["نسيج","النسيج"],["tissue"],2),(["أنسجة","الأنسجة"],["tissues"],2),
(["خلية","الخلية"],["cell"],2),(["خلايا","الخلايا"],["cells"],2),
(["شعيرة","الشعيرة"],["capillary"],2),(["شعيرات","الشعيرات"],["capillaries"],2),
(["وعاء","الوعاء"],["vessel"],2),(["أوعية","الأوعية"],["vessels"],2),
(["جدار","الجدار"],["wall"],2),(["جدران","الجدران"],["walls"],2),
(["تجويف","التجويف"],["cavity"],2),(["فتحة","الفتحة"],["opening"],2),
(["ثقب","الثقب"],["foramen"],2),(["قوس","القوس"],["arch"],2),
(["جذر","الجذر"],["root"],2),(["جسم","الجسم"],["body"],2),
(["رأس","الرأس"],["head"],2),(["عنق","العنق"],["neck"],2),
(["وجه","الوجه"],["face"],2),(["قاعدة","القاعدة"],["base"],2),
(["قمة","القمة"],["apex"],2),(["فص","الفص"],["lobe"],2),
(["ألياف","الألياف"],["fibers"],2),(["ليف","الليف"],["fiber"],2),
(["نسيج ضام","النسيج الضام"],["connective tissue"],2),
(["نخاع","النخاع"],["medulla"],2),(["قشرة","القشرة"],["cortex"],2),
(["بطين","البطين"],["ventricle"],2),(["أذين","الأذين"],["atrium"],2),
(["صمام","الصمام"],["valve"],2),(["حجرة","الحجرة"],["chamber"],2),
(["محيطي","المحيطي"],["peripheral"],2),(["مركزي","المركزي"],["central"],2),
(["نسيجي","النسيجي"],["histologic"],2),(["تشريحي","التشريحي"],["anatomic"],2),
(["وظيفة","الوظيفة"],["function"],2),(["وظائف","الوظائف"],["functions"],2),
(["إفراز","الإفراز"],["secretion"],2),(["يمتص","امتصاص","الامتصاص"],["absorption"],2),
(["يتصل","متصل","المتصل"],["connects"],2),(["يمتد","تمتد"],["extends"],2),
(["ينفتح","تنفتح"],["opens"],2),(["يفرز","تفرز"],["secretes"],2),
(["يتكون","تتكون"],["consists"],2),(["يتشكل","تتشكل"],["forms"],2),
(["يتعصب","تتعصب"],["innervated"],2),(["تعصيب","التعصيب"],["innervation"],2),
(["دموي","الدموي"],["vascular"],2),(["لمفاوي","اللمفاوي"],["lymphatic"],2),
(["وريدي","الوريدي"],["venous"],2),(["شرياني","الشرياني"],["arterial"],2),
(["هيكل","الهيكل"],["skeleton"],2),(["فقرة","الفقرة"],["vertebra"],2),
(["فقرات","الفقرات"],["vertebrae"],2),(["جمجمة","الجمجمة"],["skull"],2),
(["حوض","الحوض"],["pelvis"],2),(["عمود فقري","العمود الفقري"],["spine"],2),
(["الإحساس","إحساس"],["sensation"],2),(["الذوق","ذوق"],["taste"],2),
(["حركة","الحركة"],["movement"],2),(["ثني","الثني"],["flexion"],2),
(["بسط","البسط"],["extension"],2),(["دوران","الدوران"],["rotation"],2),
(["وحشية","الوحشية"],["lateral"],2),(["إنسية","الإنسية"],["medial"],2),
(["أمامية","الأمامية"],["anterior"],2),(["خلفية","الخلفية"],["posterior"],2),
(["علوية","العلوية"],["superior"],2),(["سفلية","السفلية"],["inferior"],2)
]

PHRASES = [
(re.compile(r"اختر\s+(?:الإجابة|الاجابة)\s+الصحيحة\s*:?"),"الصحيح:",1,"P_CORRECT"),
(re.compile(r"اختر\s+(?:الإجابة|الاجابة)\s+الخاطئة\s*:?"),"الخاطئ:",1,"P_WRONG"),
(re.compile(r"كل\s+ما\s+يلي\s+صحيح\s+(?:ما\s*عدا|عدا)\s*:?"),"الخاطئ:",1,"P_ALL_EXCEPT"),
(re.compile(r"تشمل\s+أعراض\s+"),"أعراض ",1,"P_SYMPTOMS"),
(re.compile(r"(?:تشمل\s+)?عوامل\s+(?:الخطورة|الخطر)\s+التي\s+تزيد\s+فرص\s+الإصابة\s+ب"),"عوامل خطر ",1,"P_RISK"),
(re.compile(r"من\s+عوامل\s+(?:الخطورة|الخطر)\s+(?:التي\s+تزيد\s+فرص\s+الإصابة\s+ب)?"),"عوامل خطر ",1,"P_RISK2"),
]

AR_LETTER=re.compile(r"[\u0621-\u063A\u0641-\u064A\u066E-\u06D3\u06FA-\u06FC]")
DIACRITICS=re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
AR_DIGITS=str.maketrans("٠١٢٣٤٥٦٧٨٩","0123456789")

@dataclass
class Cand:
    s:int; e:int; old:str; new:str; save:int; risk:int; kind:str

def boundary(text,s,e):
    return not (s>0 and AR_LETTER.match(text[s-1])) and not (e<len(text) and AR_LETTER.match(text[e]))

def tokcount(tok,text):
    return len(tok(text,add_special_tokens=False)["input_ids"])

def local_save(tok,text,s,e,new,window=56):
    a=max(0,s-window); b=min(len(text),e+window)
    return tokcount(tok,text[a:b])-tokcount(tok,text[a:s]+new+text[e:b])

def add_exact(cands,text,tok,forms,aliases,risk,kind):
    for form in forms:
        pos=0
        while True:
            s=text.find(form,pos)
            if s<0: break
            e=s+len(form); pos=s+1
            if not boundary(text,s,e): continue
            best=None
            for alias in aliases:
                sv=local_save(tok,text,s,e,alias)
                if sv>0 and (best is None or sv>best[0] or (sv==best[0] and len(alias)<len(best[1]))):
                    best=(sv,alias)
            if best: cands.append(Cand(s,e,text[s:e],best[1],best[0],risk,kind))

def candidates(text,tok,mode):
    maxrisk=1 if mode=="safe" else 2
    out=[]
    for forms,aliases,risk in BASE_RULES:
        if risk<=maxrisk: add_exact(out,text,tok,forms,aliases,risk,"clinical")
    if maxrisk>=2:
        for forms,aliases,risk in LEX: add_exact(out,text,tok,forms,aliases,risk,"lexicon")
    # Semantically equivalent phrase compaction.
    for rx,new,risk,kind in PHRASES:
        if risk<=maxrisk:
            for m in rx.finditer(text):
                sv=local_save(tok,text,m.start(),m.end(),new)
                if sv>0: out.append(Cand(m.start(),m.end(),m.group(),new,sv,risk,kind))
    # Prompt structure: standardized compact MCQ surface.
    structural=[]
    for rx,repl,risk,kind in structural:
        for m in rx.finditer(text):
            new=m.expand(repl); sv=local_save(tok,text,m.start(),m.end(),new)
            if sv>0: out.append(Cand(m.start(),m.end(),m.group(),new,sv,risk,kind))
    # Exact-value unit compaction.
    unit_specs=[
      (re.compile(r"(?:مليغرام|ملليغرام|ميليغرام|ملغم)"),"mg"),
      (re.compile(r"(?:مليمتر زئبق|ملم زئبق)"),"mmHg"),
      (re.compile(r"(?:نبضة في الدقيقة|نبضات في الدقيقة)"),"bpm"),
      (re.compile(r"(?:درجة مئوية|درجات مئوية)"),"°C"),
    ]
    for rx,new in unit_specs:
        for m in rx.finditer(text):
            sv=local_save(tok,text,m.start(),m.end(),new)
            if sv>0: out.append(Cand(m.start(),m.end(),m.group(),new,sv,0,"unit"))
    return out

def weighted(cands):
    if not cands:return []
    xs=sorted(cands,key=lambda c:(c.e,c.s,-c.save,c.risk))
    ends=[x.e for x in xs]
    import bisect
    p=[bisect.bisect_right(ends,x.s)-1 for x in xs]
    dp=[0]*(len(xs)+1)
    # Favor token savings; small risk penalty only breaks near-ties.
    w=[x.save*1000-x.risk*3 for x in xs]
    for i in range(1,len(xs)+1):
        dp[i]=max(dp[i-1],w[i-1]+dp[p[i-1]+1])
    ans=[]; i=len(xs)
    while i:
        yes=w[i-1]+dp[p[i-1]+1]
        if yes>dp[i-1]: ans.append(xs[i-1]); i=p[i-1]+1
        else:i-=1
    return sorted(ans,key=lambda c:c.s)

def render(text,sel):
    o=[]; p=0
    for c in sel:o.extend([text[p:c.s],c.new]);p=c.e
    o.append(text[p:]);return "".join(o)

def transform(text,tok,mode):
    base=tokcount(tok,text)
    sel=weighted(candidates(text,tok,mode))
    tr=render(text,sel); n=tokcount(tok,tr)
    while sel and n>=base:
        # Drop weakest token saver first, then riskier transform.
        k=min(range(len(sel)),key=lambda i:(sel[i].save,-sel[i].risk))
        sel.pop(k); tr=render(text,sel); n=tokcount(tok,tr)
    if n>base:return text,base,base,0,{}
    kinds={}
    for c in sel:kinds[c.kind]=kinds.get(c.kind,0)+1
    return tr,base,n,len(sel),kinds

def chat_ids(tok,text):
    msgs=[{"role":"user","content":text}]
    try:
        return tok.apply_chat_template(msgs,tokenize=True,add_generation_prompt=True)
    except Exception:
        return tok(text,add_special_tokens=False)["input_ids"]

def chat_count(tok,text): return len(chat_ids(tok,text))

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

def next_choice(model,tok,text,labels):
    ids=torch.tensor([chat_ids(tok,text)],dtype=torch.long)
    with torch.no_grad(): logits=model(input_ids=ids,use_cache=False).logits[0,-1].float()
    scores={}
    for L in labels:
        candidates_lbl=[L," "+L]
        best=-1e30
        for surf in candidates_lbl:
            li=tok(surf,add_special_tokens=False)["input_ids"]
            if len(li)==1: best=max(best,float(logits[li[0]]))
        if best>-1e29:scores[L]=best
        else:
            li=tok(L,add_special_tokens=False)["input_ids"]; scores[L]=float(logits[li[0]])
    return max(scores,key=scores.get)

TOKENIZERS=[
"Qwen/Qwen2.5-0.5B-Instruct",
"HuggingFaceTB/SmolLM2-360M-Instruct",
"TinyLlama/TinyLlama-1.1B-Chat-v1.0",
"mistralai/Mistral-7B-Instruct-v0.3",
"microsoft/Phi-3-mini-4k-instruct",
"tiiuae/Falcon3-1B-Instruct"
]
BEHAVIOR=[]

def token_bench(rows):
    out={}
    for mid in TOKENIZERS:
        try:
            tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
            modelout={}
            for mode in ("safe","aggressive"):
                hb=ht=0; hcase=[]; hk=0
                for t in HOLDOUT:
                    tr,b,n,k,_=transform(t,tok,mode);hb+=b;ht+=n;hk+=k;hcase.append(100*(b-n)/b if b else 0)
                mb=mt=cb=ct=changed=rep=0
                for r in rows[:1200]:
                    p=make_prompt(r); tr,b,n,k,_=transform(p,tok,mode)
                    mb+=b;mt+=n;cb+=chat_count(tok,p);ct+=chat_count(tok,tr);changed+=int(tr!=p);rep+=k
                modelout[mode]={
                    "holdout_reduction_pct":100*(hb-ht)/hb,"holdout_median_pct":st.median(hcase),
                    "mcq_content_reduction_pct":100*(mb-mt)/mb,
                    "mcq_chat_reduction_pct":100*(cb-ct)/cb,
                    "mcq_changed_cases":changed,"mcq_replacements":rep,
                    "no_regression":ht<=hb and mt<=mb and ct<=cb
                }
            out[mid]=modelout
        except Exception as e: out[mid]={"error":repr(e)}
    # OpenAI-style tokenizer compatibility without needing model access.
    try:
        import tiktoken
        for encname in ("cl100k_base","o200k_base"):
            enc=tiktoken.get_encoding(encname)
            class W:
                def __call__(self,text,add_special_tokens=False):return {"input_ids":enc.encode(text)}
            tok=W(); mo={}
            for mode in ("safe","aggressive"):
                B=T=0
                for t in HOLDOUT:
                    _,b,n,_,_=transform(t,tok,mode);B+=b;T+=n
                mo[mode]={"holdout_reduction_pct":100*(B-T)/B,"no_regression":T<=B}
            out["tiktoken/"+encname]=mo
    except Exception as e: out["tiktoken"]={"error":repr(e)}
    return out

def behavior_bench(rows):
    pool=list(rows)
    random.Random(SEED).shuffle(pool)
    out={}
    for mid,ncase,modes in BEHAVIOR:
        try:
            tok=AutoTokenizer.from_pretrained(mid,use_fast=True,trust_remote_code=True)
            model=AutoModelForCausalLM.from_pretrained(mid,torch_dtype=torch.float32,low_cpu_mem_usage=True,trust_remote_code=True)
            model.eval()
            for p in model.parameters():p.requires_grad_(False)
            sample=pool[:ncase]
            base_answers=[]; golds=[]; base_content=base_chat=0
            prompts=[]
            t0=time.perf_counter()
            for r in sample:
                p=make_prompt(r); labels=[L for L in "ABCDEF" if (r.get("Option "+L) or "").strip()]
                a=next_choice(model,tok,p,labels)
                prompts.append((r,p,labels));base_answers.append(a);golds.append((r.get("Correct Answer") or "").strip().upper()[:1])
                base_content+=tokcount(tok,p);base_chat+=chat_count(tok,p)
            res={}
            for mode in modes:
                agree=ok=0; tc=th=0; diffs=[]; kinds={}
                for idx,(r,p,labels) in enumerate(prompts):
                    tr,b,n,k,ks=transform(p,tok,mode)
                    a=next_choice(model,tok,tr,labels)
                    agree+=int(a==base_answers[idx]);ok+=int(a==golds[idx])
                    tc+=n;th+=chat_count(tok,tr)
                    if a!=base_answers[idx]: diffs.append({"q":r.get("Question Number"),"base":base_answers[idx],"new":a,"gold":golds[idx],"tokens":[b,n]})
                    for kk,v in ks.items():kinds[kk]=kinds.get(kk,0)+v
                res[mode]={
                    "n":ncase,"agreement":agree/ncase,
                    "baseline_accuracy":sum(int(a==g) for a,g in zip(base_answers,golds))/ncase,
                    "transformed_accuracy":ok/ncase,
                    "content_reduction_pct":100*(base_content-tc)/base_content,
                    "chat_reduction_pct":100*(base_chat-th)/base_chat,
                    "changed_answers":diffs,"replacement_kinds":kinds
                }
            res["seconds"]=time.perf_counter()-t0
            out[mid]=res
            del model;gc.collect()
        except Exception as e: out[mid]={"error":repr(e)}
    return out

rows=load_rows()
result={"version":"ACP-U5.2 strict content-only benchmark","seed":SEED,"tokenizers":token_bench(rows),"behavior":behavior_bench(rows)}
os.makedirs("e2e",exist_ok=True)
open("e2e/acp_u52_results.json","w",encoding="utf-8").write(json.dumps(result,ensure_ascii=False,indent=2))
print("ACP_U52="+json.dumps(result["tokenizers"],ensure_ascii=False),flush=True)
print("ACP_U52_BEHAVIOR="+json.dumps(result["behavior"],ensure_ascii=False),flush=True)
