# chatbot_engine.py — CuraAI Conversational Medical Chatbot Engine
# Uses: existing ML model, OpenFDA API, RxNorm API, patient history from DB

import re
import json
import requests
from datetime import datetime
from ml_model import HealthcareMLModel, parse_natural_language_symptoms, recommend_specialization, classify_urgency
import os
from dotenv import load_dotenv
from groq import Groq
from database import db

# Load environment variables
load_dotenv()
try:
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    groq_client = None
    print(f"Failed to initialize Groq client: {e}")

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
    ctx = get_patient_context(user_id)
    name = ctx.get("name","User").split()[0]
    
    if groq_client:
        system_prompt = (
            "You are CuraAI, an intelligent AI healthcare assistant. "
            "Analyze symptoms carefully, suggest diseases, recommend doctors, medicines, precautions, and health habits. "
            "Give different responses for different symptoms. "
            f"The patient's name is {name}. Their profile context: {json.dumps(ctx)}. "
            "Use Markdown for formatting."
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add a few recent messages for context
        for msg in session_history[-5:]:
            role = msg.get("role", "user")
            messages.append({"role": role, "content": msg.get("message", "")})
            
        messages.append({"role": "user", "content": text})
        
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=messages,
                model="llama-3.1-8b-instant",
                temperature=0.6,
                max_tokens=1024,
            )
            response_text = chat_completion.choices[0].message.content
            return build_response("symptom_analysis", {"message": response_text})
        except Exception as e:
            print(f"[Groq AI Error] {e}")
            return build_response("error", {"message": "I'm sorry, my AI brain is currently unavailable. Please try again later."})
    else:
        # Fallback if Groq is not configured
        return build_response("error", {"message": "Groq AI is not configured. Please add GROQ_API_KEY to .env."})


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
