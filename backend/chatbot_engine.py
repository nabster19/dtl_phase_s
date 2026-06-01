# chatbot_engine.py — CuraAI Conversational Medical Chatbot Engine
# Uses: existing ML model, OpenFDA API, RxNorm API, patient history from DB

import re
import json
import requests
from datetime import datetime
from ml_model import HealthcareMLModel, parse_natural_language_symptoms, recommend_specialization, classify_urgency
from database import db

ml = HealthcareMLModel()

# ── Emergency keyword detection ──────────────────────────────────────────────
EMERGENCY_PHRASES = [
    "chest pain", "heart attack", "can't breathe", "cannot breathe", "difficulty breathing",
    "shortness of breath", "stroke", "seizure", "unconscious", "fainted", "fainting",
    "severe bleeding", "coughing blood", "vomiting blood", "paralysis", "sudden numbness",
    "crushing chest", "severe head injury", "anaphylaxis", "allergic shock", "suicide",
    "overdose", "poisoning", "loss of consciousness", "slurred speech sudden"
]

# ── Greeting / small-talk patterns ───────────────────────────────────────────
GREETINGS = ["hello", "hi", "hey", "good morning", "good evening", "good afternoon", "namaste"]
THANKS     = ["thank", "thanks", "thank you", "thx", "appreciate"]
HELP_WORDS = ["help", "what can you do", "how does this work", "features"]

# ── Conversational response builder ──────────────────────────────────────────
def build_response(intent, payload):
    """Returns a dict: { message, type, data }"""
    return {"message": payload.get("message",""), "type": intent, "data": payload}

# ── OpenFDA drug lookup ───────────────────────────────────────────────────────
def lookup_drug_openfda(drug_name: str) -> dict:
    try:
        url = f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{drug_name}&limit=1"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            results = r.json().get("results", [])
            if results:
                info = results[0]
                return {
                    "name": drug_name.title(),
                    "warnings": (info.get("warnings", ["N/A"])[0])[:300] if info.get("warnings") else "No specific warnings found.",
                    "indications": (info.get("indications_and_usage", ["N/A"])[0])[:300] if info.get("indications_and_usage") else "N/A",
                    "dosage": (info.get("dosage_and_administration", ["Consult a doctor for dosage."])[0])[:250] if info.get("dosage_and_administration") else "Consult doctor.",
                    "side_effects": (info.get("adverse_reactions", ["Refer to package insert."])[0])[:250] if info.get("adverse_reactions") else "Refer to package insert.",
                    "source": "OpenFDA"
                }
    except Exception as e:
        print(f"[Chatbot] OpenFDA error: {e}")
    return None

# ── RxNorm drug search ────────────────────────────────────────────────────────
def lookup_rxnorm(drug_name: str) -> dict:
    try:
        url = f"https://rxnav.nlm.nih.gov/REST/drugs.json?name={drug_name}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            groups = data.get("drugGroup", {}).get("conceptGroup", [])
            for grp in groups:
                props = grp.get("conceptProperties", [])
                if props:
                    p = props[0]
                    return {"rxcui": p.get("rxcui",""), "name": p.get("name",""), "synonym": p.get("synonym",""), "source": "RxNorm"}
    except Exception as e:
        print(f"[Chatbot] RxNorm error: {e}")
    return None

# ── Get patient context from DB ───────────────────────────────────────────────
def get_patient_context(user_id: int) -> dict:
    try:
        patient = db.fetch_one("SELECT * FROM patients WHERE user_id = %s", (user_id,))
        if patient:
            return {
                "name": patient.get("name","User"),
                "age": patient.get("age"),
                "gender": patient.get("gender",""),
                "blood_group": patient.get("blood_group",""),
                "medical_history": patient.get("medical_history",""),
                "allergies": patient.get("allergies",""),
                "medications": patient.get("medications",""),
                "weight": patient.get("weight"),
                "height": patient.get("height"),
            }
    except Exception:
        pass
    return {"name": "User"}

# ── Detect intent from user message ──────────────────────────────────────────
def detect_intent(text: str) -> str:
    t = text.lower().strip()
    if any(g in t for g in GREETINGS):               return "greeting"
    if any(k in t for k in THANKS):                  return "thanks"
    if any(k in t for k in HELP_WORDS):              return "help"
    if any(p in t for p in EMERGENCY_PHRASES):       return "emergency"
    if re.search(r"\b(medicine|drug|tablet|capsule|dosage|dose|medication|side effect|rxnorm)\b", t): return "drug_info"
    if re.search(r"\b(report|prescription|scan|ocr|extract|uploaded|my report)\b", t): return "ocr_query"
    if re.search(r"\b(tip|advice|lifestyle|diet|exercise|habit|water|sleep)\b", t): return "health_tip"
    if re.search(r"\b(appoint|book|doctor|specialist|consult|recommend doctor)\b", t): return "doctor_recommend"
    if re.search(r"\b(symptom|feel|pain|ache|fever|cough|cold|nausea|dizzy|headache|tired|weak|vomit|rash|swelling|bleed|burning|itching|breathe)\b", t): return "symptom_analysis"
    return "general"

# ── Extract drug name from query ──────────────────────────────────────────────
def extract_drug_name(text: str) -> str:
    patterns = [
        r"(?:about|info on|what is|tell me about|dosage of|side effects of|medicine called)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
        r"([A-Za-z]+(?:mycin|cillin|mab|tinib|vastatin|pril|sartan|olol|zepam|xacin|zole|prazole|caine|dine|pine|vir|ine|ide|ate))"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    words = text.split()
    for w in words:
        if len(w) > 5 and w[0].isupper():
            return w
    return text.strip()

# ── Core: process a chat message ──────────────────────────────────────────────
def process_message(user_id: int, user_message: str, session_history: list) -> dict:
    text = user_message.strip()
    intent = detect_intent(text)
    ctx = get_patient_context(user_id)
    name = ctx.get("name","User").split()[0]

    # ── EMERGENCY ─────────────────────────────────────────────────────────────
    if intent == "emergency":
        msg = (
            f"🚨 **EMERGENCY ALERT, {name}!**\n\n"
            "Your symptoms may indicate a **life-threatening condition**. "
            "Please take **immediate action**:\n\n"
            "📞 **Call 108 (Ambulance)** or go to the nearest Emergency Room immediately.\n\n"
            "⚠ Do NOT wait or self-medicate for these symptoms.\n\n"
            "_CuraAI recommends immediate professional medical care. This is not a substitute for emergency services._"
        )
        return build_response("emergency", {
            "message": msg, "urgency": "CRITICAL",
            "action": "Call 108 immediately", "color": "red"
        })

    # ── GREETING ──────────────────────────────────────────────────────────────
    if intent == "greeting":
        history_note = ""
        if ctx.get("medical_history"):
            history_note = f" I can see you have a history of **{ctx['medical_history']}** — I'll keep that in mind."
        msg = (
            f"👋 Hello {name}! I'm **CuraAI Assistant**, your personal AI health companion.{history_note}\n\n"
            "I can help you with:\n"
            "• 🩺 Symptom analysis and disease prediction\n"
            "• 💊 Medicine information and dosage guidance\n"
            "• 👨‍⚕️ Doctor specialization recommendations\n"
            "• 📋 Prescription and report analysis\n"
            "• 🌿 Personalized health tips\n\n"
            "Just describe how you're feeling, and I'll assist you!"
        )
        return build_response("greeting", {"message": msg})

    # ── HELP ──────────────────────────────────────────────────────────────────
    if intent == "help":
        msg = (
            "🤖 **CuraAI Assistant — What I Can Do:**\n\n"
            "**Symptom Analysis:** Tell me your symptoms in plain language like *'I have a sharp headache and fever for 3 days'*\n\n"
            "**Medicine Info:** Ask *'What are the side effects of Metformin?'* or *'Tell me about Paracetamol'*\n\n"
            "**Doctor Advice:** Ask *'Which doctor should I see for chest pain?'*\n\n"
            "**Health Tips:** Ask *'Give me diet tips for diabetes'* or *'How can I improve my sleep?'*\n\n"
            "**Emergency:** If you describe critical symptoms, I'll alert you immediately.\n\n"
            "⚕ _All AI responses are for informational purposes only. Always consult a certified doctor._"
        )
        return build_response("help", {"message": msg})

    # ── THANKS ────────────────────────────────────────────────────────────────
    if intent == "thanks":
        return build_response("thanks", {
            "message": f"You're welcome, {name}! 😊 Stay healthy. Feel free to ask anything anytime!\n\n⚕ _Remember: Always verify AI recommendations with your doctor._"
        })

    # ── DRUG INFO ─────────────────────────────────────────────────────────────
    if intent == "drug_info":
        drug_name = extract_drug_name(text)
        fda_data  = lookup_drug_openfda(drug_name)
        rxnorm    = lookup_rxnorm(drug_name)

        if fda_data:
            # Check for patient allergies
            allergy_note = ""
            if ctx.get("allergies") and drug_name.lower() in ctx["allergies"].lower():
                allergy_note = f"\n\n⚠ **ALLERGY ALERT:** Your profile shows an allergy to **{drug_name}**. Do NOT take this without consulting your doctor."

            msg = (
                f"💊 **{fda_data['name']} — Drug Information**\n\n"
                f"**Indications (Uses):**\n{fda_data['indications']}\n\n"
                f"**Recommended Dosage:**\n{fda_data['dosage']}\n\n"
                f"**Side Effects:**\n{fda_data['side_effects']}\n\n"
                f"**Important Warnings:**\n{fda_data['warnings']}"
                f"{allergy_note}\n\n"
                f"_Source: OpenFDA · RxCUI: {rxnorm['rxcui'] if rxnorm else 'N/A'}_\n\n"
                "⚕ **Disclaimer:** Always take medicines under a licensed doctor's supervision. Do not self-medicate."
            )
        else:
            # Fallback to local drug data
            local = _local_drug_info(drug_name)
            msg = (
                f"💊 **{drug_name.title()}**\n\n{local}\n\n"
                f"_RxCUI: {rxnorm['rxcui'] if rxnorm else 'Not found'}_\n\n"
                "⚕ **Disclaimer:** Verify all medicine information with your pharmacist or doctor."
            )
        return build_response("drug_info", {"message": msg, "drug": drug_name})

    # ── DOCTOR RECOMMENDATION ─────────────────────────────────────────────────
    if intent == "doctor_recommend":
        symptoms = parse_natural_language_symptoms(text)
        spec = recommend_specialization([], "General") if not symptoms else None
        if symptoms:
            try:
                preds = ml.predict_disease(symptoms)
                disease = preds[0]["disease"] if preds else "General"
                spec_result = recommend_specialization(symptoms, disease)
                spec = spec_result.get("specialization", "General Physician")
                reason = spec_result.get("reason", "")
                msg = (
                    f"👨‍⚕️ **Doctor Recommendation for {name}:**\n\n"
                    f"Based on your symptoms, I recommend consulting a **{spec}**.\n\n"
                    f"📌 Reason: {reason}\n\n"
                    "You can book an appointment directly from the **Doctor Connect** tab in your dashboard.\n\n"
                    "⚕ _This is an AI recommendation. A proper diagnosis requires physical examination._"
                )
            except Exception:
                spec = "General Physician"
                msg = f"👨‍⚕️ Based on your description, I recommend starting with a **General Physician**. They can refer you to the right specialist after evaluation."
        else:
            msg = "👨‍⚕️ Please describe your symptoms in detail and I'll recommend the right specialist for you!"
        return build_response("doctor_recommend", {"message": msg, "specialization": spec})

    # ── HEALTH TIP ────────────────────────────────────────────────────────────
    if intent == "health_tip":
        tips = _generate_health_tips(ctx, text)
        msg = (
            f"🌿 **Personalized Health Tips for {name}:**\n\n{tips}\n\n"
            "⚕ _These tips are general wellness guidelines. Consult your doctor before making major health changes._"
        )
        return build_response("health_tip", {"message": msg})

    # ── SYMPTOM ANALYSIS (primary AI flow) ───────────────────────────────────
    parsed_symptoms = parse_natural_language_symptoms(text)
    # Also include any explicitly named symptom tokens
    token_symptoms = [w.replace(" ","_") for w in re.findall(r'\b(?:fever|headache|cough|nausea|fatigue|dizziness|chest pain|joint pain|rash|vomiting|diarrhea|weakness|shortness of breath|blurry vision|polyuria|polydipsia)\b', text.lower())]
    all_symptoms = list(set(parsed_symptoms + token_symptoms))

    if not all_symptoms:
        msg = (
            f"I understand you might be feeling unwell, {name}. Could you describe your symptoms more specifically?\n\n"
            "For example:\n"
            "• *'I have a severe headache and high fever for 2 days'*\n"
            "• *'I feel chest tightness and shortness of breath'*\n"
            "• *'I have joint pain, fatigue, and a skin rash'*\n\n"
            "The more detail you give, the more accurate my analysis will be!"
        )
        return build_response("clarify", {"message": msg})

    # Run ML prediction
    predictions = []
    try:
        predictions = ml.predict_disease(all_symptoms)
    except Exception as e:
        print(f"[Chatbot] Prediction error: {e}")

    if not predictions:
        return build_response("general", {
            "message": f"I detected these symptoms: **{', '.join([s.replace('_',' ') for s in all_symptoms])}**.\n\nUnfortunately I couldn't match these to a known condition pattern. Please consult a doctor for a proper evaluation.\n\n⚕ _Always seek professional medical advice._"
        })

    top = predictions[0]
    disease  = top["disease"]
    conf     = top["confidence"]
    severity = top.get("severity","moderate")
    
    # Get urgency
    urgency_result = classify_urgency(all_symptoms, text, 0)
    urgency_level  = urgency_result.get("level","Moderate")
    urgency_icon   = urgency_result.get("icon","⚠")
    urgency_advice = urgency_result.get("advice","")

    # Get drug recommendations
    try:
        drug_recs = ml.get_drug_recommendations(disease)
    except Exception:
        drug_recs = {}

    # Get specialist
    try:
        spec_result = recommend_specialization(all_symptoms, disease)
        specialist  = spec_result.get("specialization", "General Physician")
    except Exception:
        specialist = "General Physician"

    # Personalization — check patient history
    history_note = ""
    if ctx.get("medical_history") and any(d.lower() in ctx["medical_history"].lower() for d in [disease.lower(), disease.split()[0].lower()]):
        history_note = f"\n\n📌 **Note:** Your medical profile indicates a history of {ctx['medical_history']}. This may be related to your current symptoms."

    # Build medicines string
    med_lines = ""
    if drug_recs.get("medicines"):
        for m in drug_recs["medicines"][:3]:
            med_lines += f"  • **{m.get('name','')}** — {m.get('dosage','')} ({m.get('timing','')})\n"
    else:
        med_lines = "  • Please consult your doctor for appropriate medication.\n"

    # Precautions
    precautions_text = ""
    if top.get("precautions"):
        prec = top["precautions"]
        if isinstance(prec, list):
            precautions_text = "\n".join([f"  • {p}" for p in prec[:3]])
        else:
            precautions_text = f"  • {prec}"

    # Emergency override
    urgent_banner = ""
    if urgency_level in ("Emergency","Severe"):
        urgent_banner = f"\n\n🚨 **{urgency_level.upper()} URGENCY** — {urgency_advice}\n📞 **Please call 108 or visit an emergency room immediately.**"

    msg = (
        f"{urgency_icon} **Medical Analysis for {name}**\n\n"
        f"**Detected Symptoms:** {', '.join([s.replace('_',' ').title() for s in all_symptoms])}\n\n"
        f"**Most Likely Condition:**\n"
        f"🔬 **{disease}** — {conf}% confidence | *{severity.title()} severity*\n\n"
        + (f"**Other Possibilities:**\n" + "".join([f"  • {p['disease']} ({p['confidence']}%)\n" for p in predictions[1:3]]) + "\n" if len(predictions) > 1 else "")
        + f"**Suggested Medicines:**\n{med_lines}\n"
        f"**Precautions:**\n{precautions_text or '  • Rest and stay hydrated.'}\n\n"
        f"**Recommended Specialist:** 👨‍⚕️ {specialist}\n"
        f"**Next Steps:** {top.get('next_actions','Consult a doctor for proper diagnosis.')}"
        f"{history_note}"
        f"{urgent_banner}\n\n"
        "⚕ **Disclaimer:** This is an AI analysis for informational purposes. Please verify with a licensed doctor before taking any medication."
    )

    return build_response("symptom_analysis", {
        "message": msg,
        "predictions": predictions[:3],
        "symptoms": all_symptoms,
        "urgency": urgency_level,
        "specialist": specialist,
        "drugs": drug_recs
    })


# ── Local fallback drug info ──────────────────────────────────────────────────
def _local_drug_info(drug_name: str) -> str:
    local_db = {
        "paracetamol": "**Uses:** Fever, mild to moderate pain relief.\n**Dosage:** 500mg–1000mg every 4–6 hours (max 4g/day).\n**Side Effects:** Rare at therapeutic doses; liver damage at overdose.\n**Precaution:** Avoid alcohol.",
        "metformin":   "**Uses:** Type 2 Diabetes management.\n**Dosage:** 500mg–2550mg daily with meals.\n**Side Effects:** Nausea, diarrhea, stomach upset (usually temporary).\n**Precaution:** Avoid in kidney disease.",
        "aspirin":     "**Uses:** Pain relief, fever, anti-platelet (heart protection).\n**Dosage:** 75mg–325mg daily (cardiovascular) or 325mg–650mg for pain.\n**Side Effects:** Stomach irritation, bleeding risk.\n**Precaution:** Avoid in children under 16.",
        "amoxicillin": "**Uses:** Bacterial infections (respiratory, ear, UTI).\n**Dosage:** 250mg–500mg every 8 hours.\n**Side Effects:** Rash, diarrhea, nausea.\n**Precaution:** Avoid if allergic to penicillin.",
        "ibuprofen":   "**Uses:** Pain, inflammation, fever.\n**Dosage:** 200mg–400mg every 6–8 hours with food.\n**Side Effects:** Stomach upset, increased BP, kidney stress.\n**Precaution:** Avoid in kidney/heart disease.",
        "lisinopril":  "**Uses:** Hypertension, heart failure.\n**Dosage:** 5mg–40mg once daily.\n**Side Effects:** Dry cough, dizziness, elevated potassium.\n**Precaution:** Monitor kidney function.",
        "atorvastatin":"**Uses:** High cholesterol, cardiovascular risk reduction.\n**Dosage:** 10mg–80mg once daily.\n**Side Effects:** Muscle pain, liver enzyme elevation.\n**Precaution:** Avoid grapefruit juice.",
    }
    name_l = drug_name.lower().strip()
    for key, info in local_db.items():
        if key in name_l or name_l in key:
            return info
    return f"Detailed information for **{drug_name.title()}** was not found in local database. Please check OpenFDA.gov or consult your pharmacist."


# ── Personalized health tips ──────────────────────────────────────────────────
def _generate_health_tips(ctx: dict, query: str) -> str:
    tips = []
    q = query.lower()
    history = (ctx.get("medical_history","") or "").lower()

    if "diabetes" in history or "sugar" in q or "glucose" in q:
        tips.append("🍎 **Diet:** Eat low-glycemic foods — whole grains, legumes, vegetables. Avoid refined sugar.")
        tips.append("🚶 **Exercise:** 30 minutes of brisk walking daily helps regulate blood sugar.")
        tips.append("💧 **Hydration:** Drink 8–10 glasses of water daily. Avoid sugary drinks.")
        tips.append("📊 **Monitoring:** Check fasting blood sugar regularly. Target HbA1c < 7%.")
    elif "hypertension" in history or "blood pressure" in q or "bp" in q:
        tips.append("🧂 **Salt Intake:** Limit sodium to <2300mg/day. Avoid processed foods.")
        tips.append("🏃 **Exercise:** Aerobic activity 150 min/week helps lower BP naturally.")
        tips.append("🧘 **Stress Management:** Practice meditation or deep breathing 10 min/day.")
        tips.append("🚭 **Lifestyle:** Quit smoking and limit alcohol — both raise blood pressure.")
    elif "sleep" in q or "insomnia" in q:
        tips.append("🌙 **Sleep Schedule:** Sleep and wake at the same time every day — even weekends.")
        tips.append("📵 **Screen-Free Bedtime:** Avoid phones/screens 1 hour before bed.")
        tips.append("☕ **Caffeine:** Avoid caffeine after 2 PM. Try chamomile tea instead.")
        tips.append("🛏 **Sleep Environment:** Keep room dark, cool (18–22°C), and quiet.")
    elif "weight" in q or "obesity" in q or "fat" in q:
        tips.append("🥗 **Calorie Deficit:** Aim for 500 kcal/day deficit through diet + exercise.")
        tips.append("🏋️ **Strength Training:** 3x/week resistance training boosts metabolism.")
        tips.append("⏰ **Intermittent Fasting:** 16:8 method can help with sustainable weight loss.")
        tips.append("🍽 **Mindful Eating:** Eat slowly, chew thoroughly, avoid eating while distracted.")
    else:
        # General wellness tips
        age = ctx.get("age", 30)
        tips.append("💧 **Hydration:** Drink at least 8 glasses (2L) of water daily.")
        tips.append("🏃 **Activity:** 150 minutes of moderate exercise per week is the WHO recommendation.")
        tips.append("😴 **Sleep:** Adults need 7–9 hours of quality sleep per night.")
        tips.append("🥦 **Diet:** Fill half your plate with vegetables at every meal.")
        if age and int(age) > 40:
            tips.append("🩺 **Screening:** Get annual health checkups including cholesterol, BP, and blood sugar tests.")
        tips.append("🧘 **Mental Health:** Practice mindfulness or journaling for 10 minutes daily.")

    return "\n".join(tips)


# ── Save message to DB ────────────────────────────────────────────────────────
def save_chat_message(user_id: int, role: str, message: str, metadata: dict = None):
    try:
        db.execute_query(
            "INSERT INTO chatbot_messages (user_id, role, message, metadata) VALUES (%s, %s, %s, %s)",
            (user_id, role, message, json.dumps(metadata or {}))
        )
    except Exception as e:
        print(f"[Chatbot] DB save error: {e}")


# ── Load chat history ─────────────────────────────────────────────────────────
def get_chat_history(user_id: int, limit: int = 40) -> list:
    try:
        rows = db.fetch_all(
            "SELECT role, message, metadata, created_at FROM chatbot_messages WHERE user_id = %s ORDER BY created_at ASC LIMIT %s",
            (user_id, limit)
        )
        result = []
        for r in rows:
            meta = {}
            try:
                meta = json.loads(r.get("metadata","{}") or "{}")
            except Exception:
                pass
            result.append({
                "role": r["role"],
                "message": r["message"],
                "metadata": meta,
                "created_at": str(r.get("created_at",""))
            })
        return result
    except Exception as e:
        print(f"[Chatbot] History error: {e}")
        return []


# ── Clear chat history ────────────────────────────────────────────────────────
def clear_chat_history(user_id: int):
    try:
        db.execute_query("DELETE FROM chatbot_messages WHERE user_id = %s", (user_id,))
    except Exception as e:
        print(f"[Chatbot] Clear error: {e}")
