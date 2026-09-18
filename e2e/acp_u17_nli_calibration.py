#!/usr/bin/env python3
import json,os,torch
import torch.nn.functional as F
from transformers import AutoTokenizer,AutoModelForSequenceClassification
MODEL="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
PAIRS=[
("ألم في الخاصرة اليمنى دون حمى.","Pain in the right flank without fever.",1,"good_flank"),
("ألم في الخاصرة اليمنى دون حمى.","Pain in the right ventricle without fever.",0,"bad_flank"),
("ضغط الدم 90/60 mmHg ولا توجد دوخة.","Blood pressure is 90/60 mmHg and there is no dizziness.",1,"good_dizziness"),
("ضغط الدم 90/60 mmHg ولا توجد دوخة.","Blood pressure is 90/60 mmHg and there is no duct.",0,"bad_dizziness"),
("لا تعط الدواء قبل استبعاد الحمل.","Do not give the drug before ruling out pregnancy.",1,"good_pregnancy"),
("لا تعط الدواء قبل استبعاد الحمل.","Do not give the drug before the pregnancy is terminated.",0,"bad_pregnancy"),
("تشبع الأكسجين 88% في الهواء المحيط.","Oxygen saturation is 88% on room air.",1,"good_ambient"),
("تشبع الأكسجين 88% في الهواء المحيط.","Oxygen is 88% in ocean air.",0,"bad_ambient"),
("الكرياتينين 2.1 mg/dL.","Creatinine is 2.1 mg/dL.",1,"good_creatinine"),
("الكرياتينين 2.1 mg/dL.","Creatine is 2.1 mg/dL.",0,"bad_creatinine"),
("لا يوجد ألم في الجانب الأيسر من الصدر.","There is no pain on the left side of the chest.",1,"good_neg_left"),
("لا يوجد ألم في الجانب الأيسر من الصدر.","There is pain on the right side of the chest.",0,"bad_neg_left"),
("جرعة الأنسولين 10 وحدات قبل العشاء.","The insulin dose is 10 units before dinner.",1,"good_dose"),
("جرعة الأنسولين 10 وحدات قبل العشاء.","The insulin dose is 100 units after dinner.",0,"bad_dose"),
("ضغط الدم 160/100 mmHg.","Blood pressure is 160/100 mmHg.",1,"good_bp"),
("ضغط الدم 160/100 mmHg.","Blood pressure is 100/60 mmHg.",0,"bad_bp"),
("لا يوجد نزيف في العين اليمنى.","There is no bleeding in the right eye.",1,"good_eye"),
("لا يوجد نزيف في العين اليمنى.","There is bleeding in the left eye.",0,"bad_eye"),
("المريضة حامل في الأسبوع 32.","The patient is 32 weeks pregnant.",1,"good_gestation"),
("المريضة حامل في الأسبوع 32.","The patient is not pregnant.",0,"bad_gestation")
]
tok=AutoTokenizer.from_pretrained(MODEL);m=AutoModelForSequenceClassification.from_pretrained(MODEL,dtype="auto");m.eval()
labels={k.lower():v for k,v in m.config.label2id.items()}
eid=labels.get("entailment",labels.get("entails",0))
@torch.no_grad()
def score(a,b):
 x=tok(a,b,return_tensors="pt",truncation=True,max_length=256);p=F.softmax(m(**x).logits[0].float(),dim=-1);return float(p[eid])
rows=[]
for a,b,y,n in PAIRS:
 ab=score(a,b);ba=score(b,a);bi=min(ab,ba);rows.append({"name":n,"expected_safe":bool(y),"ar_to_en":ab,"en_to_ar":ba,"bidirectional":bi})
good=[x["bidirectional"] for x in rows if x["expected_safe"]];bad=[x["bidirectional"] for x in rows if not x["expected_safe"]]
best=None
for th in sorted(set([0.0,1.0]+[(x+y)/2 for x in good+bad for y in good+bad if x!=y])):
 tp=sum(x>=th for x in good);tn=sum(x<th for x in bad);acc=(tp+tn)/(len(good)+len(bad))
 if best is None or acc>best[0]:best=(acc,th,tp,tn)
res={"model":MODEL,"rows":rows,"good_min":min(good),"good_median":sorted(good)[len(good)//2],"bad_max":max(bad),"bad_median":sorted(bad)[len(bad)//2],"best_calibration":{"accuracy":best[0],"threshold":best[1],"good_accepted":best[2],"bad_rejected":best[3]},"separable":min(good)>max(bad)}
os.makedirs("e2e",exist_ok=True);open("e2e/acp_u17_nli_calibration.json","w",encoding="utf8").write(json.dumps(res,ensure_ascii=False,indent=2));print("ACP_U17="+json.dumps(res,ensure_ascii=False),flush=True)
