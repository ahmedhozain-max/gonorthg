from flask import Flask, render_template, request

app = Flask(__name__)

# ----------------- 1. قاعدة بيانات استراتيجية الدول (المنطق الاستشاري) -----------------
VISA_STRATEGY = {
    "weak": {
        "range": (0, 39),
        "status": "الملف يحتاج تحسين (ضعيف حالياً)",
        "countries": [],
        "evidence": "بناءً على المعايير الحالية، يفتقر الملف للروابط الكافية بالوطن. التقديم الآن قد يمنحك رفضاً يصعب الأمور مستقبلاً في نظام الشنجن.",
        "why_no": "السفارات ترفض حالياً الملفات التي لا تظهر استقراراً مالياً ووظيفياً واضحاً (المادة 32 من قانون الفيزا)."
    },
    "medium": {
        "range": (40, 59),
        "status": "ملف متوسط (مقبول لدول سياحية مرنة)",
        "countries": ["اليونان", "إسبانيا", "إيطاليا", "ليتوانيا", "كرواتيا"],
        "evidence": "هذه الدول تعتمد اقتصادياً على السياحة، لذا فإن قناصلها يميلون للمرونة مع الملفات المتوسطة لدعم تدفق السياح.",
        "why_no": "تجنب دول الشمال (الدنمارك/النرويج) وألمانيا حالياً، لأنها تتطلب سجل سفر أقوى وملاءة مالية أدق."
    },
    "good": {
        "range": (60, 79),
        "status": "ملف جيد جداً (فرص قبول عالية)",
        "countries": ["فرنسا", "هولندا", "البرتغال", "التشيك", "المجر"],
        "evidence": "توازن ملفك بين التعليم واللغة والحساب البنكي يجعلك مسافراً موثوقاً. فرنسا وهولندا تمنحان تأشيرات متعددة لهذه الملفات.",
        "why_no": "فرصك قوية، ولكن تأكد من دقة المستندات؛ فالدول مثل هولندا لا تتسامح مع أي تناقض في الحجوزات."
    },
    "strong": {
        "range": (80, 100),
        "status": "ملف ممتاز (نخبة المسافرين)",
        "countries": ["ألمانيا", "سويسرا", "النمسا", "النرويج", "بلجيكا"],
        "evidence": "ملفك مستوفي لأعلى المعايير القانونية. يمكنك التقديم على أكثر السفارات تشدداً وأنت مطمئن لنسبة القبول العالية.",
        "why_no": "لا توجد موانع تقنية؛ أنت مؤهل للحصول على فيزا طويلة الأمد مباشرة (Circulation Visa)."
    }
}

# ----------------- 2. دالة التقييم الذكية (المحرك الرئيسي) -----------------
def evaluate_client(data):
    score = 0
    reasons = []
    improvement = []
    
    # استلام اسم العميل (أهم إضافة)
    client_name = data.get("client_name", "العميل العزيز")

    # --- أ. الملاءة المالية (30 نقطة) ---
    balance = int(data.get("bank_balance", 0))
    if balance >= 150000:
        score += 30
        reasons.append("رصيد بنكي ممتاز (أعلى من 150 ألف جنيه)")
    elif balance >= 70000:
        score += 20
        reasons.append("رصيد بنكي جيد ومناسب للسفر")
    elif balance >= 30000:
        score += 10
        improvement.append("حاول رفع الرصيد ليتجاوز 70 ألفاً لتعزيز قوة الملف")
    else:
        improvement.append("الرصيد الحالي ضعيف؛ السفارة قد تشك في قدرتك على تغطية التكاليف")

    # --- ب. الاستقرار الوظيفي والدخل (25 نقطة) ---
    job_type = data.get("job_type")
    job_scores = {"government": 20, "private": 15, "freelance": 10, "none": 0}
    score += job_scores.get(job_type, 0)
    
    # إضافة نقاط الراتب (جديد)
    salary = int(data.get("salary", 0))
    if salary >= 15000:
        score += 5
        reasons.append("راتب شهري مرتفع يثبت القدرة المالية")

    if data.get("has_hr_letter") == "yes":
        score += 5
        reasons.append("توفر خطاب HR Letter يعزز مصداقية الوظيفة")
    elif job_type != "none":
        improvement.append("ضرورة توفير خطاب موارد بشرية (HR Letter) مختوم")

    # --- ج. تحليل السن (عامل الأمان - 10 نقاط) ---
    age = int(data.get("age", 0))
    if age > 0:
        if age < 25:
            score -= 5
            improvement.append("بسبب السن الصغير، يفضل إرفاق إثباتات أملاك أو قيد دراسي")
        elif age > 55:
            score += 10
            reasons.append("الفئة العمرية (فوق 55) تعطي انطباعاً عالياً بالعودة")
        else:
            score += 5
            reasons.append("السن في نطاق الاستقرار المهني والاجتماعي")

    # --- د. الحالة الاجتماعية والأطفال (عامل الربط بالوطن) ---
    marital = data.get("marital_status")
    if marital == "married":
        score += 5
        reasons.append("الحالة الاجتماعية (متزوج) تعتبر رابطاً قوياً للعودة")
    
    # إضافة نقاط الأطفال (جديد)
    children = int(data.get("children", 0))
    if children > 0:
        score += 5
        reasons.append(f"وجود أطفال ({children}) يعزز الروابط الأسرية في الوطن")

    # --- هـ. التعليم والمؤهل الدراسي (10 نقاط) ---
    edu = data.get("education")
    edu_mapping = {"post_grad": 10, "bachelor": 7, "high_school": 3}
    score += edu_mapping.get(edu, 0)
    if edu in ["bachelor", "post_grad"]:
        reasons.append(f"المؤهل الدراسي العالي يعزز الثقة في خلفيتك المهنية")

    # --- و. مستوى اللغة (10 نقاط) ---
    lang = data.get("language")
    lang_mapping = {"fluent": 10, "intermediate": 7, "basic": 3, "none": 0}
    score += lang_mapping.get(lang, 0)
    if lang in ["intermediate", "fluent"]:
        reasons.append("إتقان اللغة يسهل التواصل ويقلل من شكوك القنصل")

    # --- ز. تاريخ السفر السابق (10 نقاط) ---
    travel = data.get("travel_history_level")
    travel_mapping = {"schengen": 10, "asia": 7, "arab": 4, "none": 0}
    score += travel_mapping.get(travel, 0)

    # --- ح. الخصومات (الرفض / مدة الرحلة) ---
    if data.get("previous_refusal") == "yes":
        score -= 10
        improvement.append("يجب إرفاق خطاب توضيحي (Cover Letter) لمعالجة الرفض السابق")
    
    trip_days = int(data.get("trip_duration_days", 7))
    if trip_days > 15:
        score -= 5
        improvement.append("تقليل مدة الرحلة الأولى لأقل من 10 أيام يزيد من منطقية الطلب")

    # --- ط. تحديد النتيجة النهائية والاستراتيجية ---
    score = max(0, min(100, score))

    final_strategy = {}
    for key, val in VISA_STRATEGY.items():
        low, high = val["range"]
        if low <= score <= high:
            final_strategy = val
            break
    
    # تحليل الدولة المختارة
    trip_country = data.get("target_country", "").strip().lower()
    chosen_message = ""
    if trip_country:
        if score < 40:
            chosen_message = f"❌ دولة {trip_country.capitalize()} سترفض ملف {client_name} بنسبة كبيرة حالياً."
        elif trip_country in ["germany", "switzerland", "austria", "belgium"] and score < 65:
            chosen_message = f"⚠️ {trip_country.capitalize()} دولة متشددة؛ ملف {client_name} يحتاج تقوية قبل مراسلتهم."
        else:
            chosen_message = f"✅ {trip_country.capitalize()} اختيار موفق ومناسب لقوة ملف {client_name}."

    return {
        "client_name": client_name, # إرجاع الاسم لصفحة النتيجة
        "score": score,
        "suggestion": " / ".join(final_strategy["countries"]) if final_strategy["countries"] else "لا ننصح بالتقديم حالياً",
        "main_reason": final_strategy["status"],
        "reasons": reasons,
        "improvement": improvement,
        "chosen_message": chosen_message,
        "evidence": final_strategy["evidence"],
        "why_no": final_strategy["why_no"]
    }

# ----------------- 3. مسارات Flask (Routes) -----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        form_data = request.form.to_dict()
        results = evaluate_client(form_data)
        return render_template("result.html", **results)
    
    return render_template("form.html")

if __name__ == "__main__":
    app.run(debug=True)