# ml_model.py - Machine Learning & AI Decision Support System
# Trains a Random Forest model on symptom data and contains recommender rules.

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
import os
import pickle

# Define All Symptoms
ALL_SYMPTOMS = [
    "fever", "chills", "cough", "sore_throat", "muscle_aches", "fatigue", 
    "polyuria", "polydipsia", "weight_loss", "blurry_vision",
    "headache", "shortness_of_breath", "nosebleeds", "dizziness", "chest_pain",
    "itchy_skin", "red_rash", "dry_skin", "skin_blisters",
    "severe_headache", "nausea", "sensitivity_to_light", "sensitivity_to_sound", "aura",
    "diarrhea", "bloating", "abdominal_pain", "salty_skin", "poor_growth",
    "muscle_weakness", "slurred_speech", "muscle_cramps", "difficulty_swallowing",
    "involuntary_movements", "cognitive_decline", "balance_issues", "depression",
    "joint_pain", "butterfly_rash", "hair_loss", "heartburn", "acid_reflux",
    "joint_stiffness", "swollen_joints", "weight_gain", "cold_intolerance",
    "pale_skin", "weakness", "cold_hands"
]

# Define Disease Database
DISEASE_METADATA = {
    "Diabetes Type 2": {
        "category": "lifestyle",
        "severity": "medium",
        "is_rare": False,
        "precautions": ["Reduce carbohydrate intake", "Exercise 30 mins daily", "Monitor glucose weekly"],
        "next_actions": "Schedule HbA1c test and consult a Diabetologist."
    },
    "Hypertension": {
        "category": "chronic",
        "severity": "medium",
        "is_rare": False,
        "precautions": ["Reduce sodium intake", "Avoid stress", "Monitor Blood Pressure twice daily"],
        "next_actions": "Consult a Cardiologist for Blood Pressure management."
    },
    "Hypercholesterolemia": {
        "category": "lifestyle",
        "severity": "medium",
        "is_rare": False,
        "precautions": ["Avoid saturated fats", "Eat soluble fiber", "Daily cardiovascular exercise"],
        "next_actions": "Request Lipid Profile blood test and review with General Physician."
    },
    "Influenza": {
        "category": "common",
        "severity": "low",
        "is_rare": False,
        "precautions": ["Complete bed rest", "Stay hydrated", "Isolate to prevent spreading"],
        "next_actions": "Consult General Physician if fever stays above 102°F for 3 days."
    },
    "Dermatitis": {
        "category": "common",
        "severity": "low",
        "is_rare": False,
        "precautions": ["Moisturize skin frequently", "Avoid harsh soaps", "Apply cool compresses"],
        "next_actions": "Consult a Dermatologist for topical steroid options."
    },
    "Migraine": {
        "category": "chronic",
        "severity": "low",
        "is_rare": False,
        "precautions": ["Avoid bright lights & loud sounds", "Maintain consistent sleep cycle", "Identify food triggers"],
        "next_actions": "Consult a Neurologist if frequency exceeds twice a week."
    },
    "Celiac Disease": {
        "category": "genetic",
        "severity": "medium",
        "is_rare": False,
        "precautions": ["Strict gluten-free diet", "Read food labels carefully", "Avoid cross-contamination"],
        "next_actions": "Consult Gastroenterologist for tTG-IgA testing."
    },
    "Cystic Fibrosis": {
        "category": "genetic",
        "severity": "high",
        "is_rare": True,
        "precautions": ["Chest physical therapy", "Use saline nebulizers", "Avoid smoke and dust"],
        "next_actions": "Consult a Pulmonologist and Genetic Specialist immediately."
    },
    "ALS (Amyotrophic Lateral Sclerosis)": {
        "category": "rare",
        "severity": "critical",
        "is_rare": True,
        "precautions": ["Assistive physical therapy", "Nutritional monitoring", "Respiratory support plans"],
        "next_actions": "Urgent consultation with a Neurologist specializing in motor neuron diseases."
    },
    "Huntington's Disease": {
        "category": "genetic",
        "severity": "critical",
        "is_rare": True,
        "precautions": ["Speech therapy", "Fall prevention planning", "Psychological counseling"],
        "next_actions": "Consult Neurologist and Genetic Counselor for genetic mapping."
    },
    "Lupus": {
        "category": "chronic",
        "severity": "high",
        "is_rare": False,
        "precautions": ["Use high SPF sunscreen", "Manage physical stress", "Regular kidney checks"],
        "next_actions": "Consult a Rheumatologist for autoimmune screening (ANA test)."
    },
    "Gastroesophageal Reflux (GERD)": {
        "category": "lifestyle",
        "severity": "low",
        "is_rare": False,
        "precautions": ["Eat small frequent meals", "Do not lie down for 2 hours after eating", "Avoid spicy foods"],
        "next_actions": "Consult General Physician; consider endoscopy if symptoms persist."
    },
    "Rheumatoid Arthritis": {
        "category": "chronic",
        "severity": "medium",
        "is_rare": False,
        "precautions": ["Joint-friendly exercises", "Apply warm compresses for stiffness", "Maintain healthy weight"],
        "next_actions": "Consult a Rheumatologist for joint health evaluation."
    },
    "Hypothyroidism": {
        "category": "chronic",
        "severity": "low",
        "is_rare": False,
        "precautions": ["Take levothyroxine on empty stomach", "Eat iodine-rich foods", "Monitor thyroid levels regularly"],
        "next_actions": "Consult an Endocrinologist for Thyroid Panel test."
    },
    "Anemia": {
        "category": "common",
        "severity": "low",
        "is_rare": False,
        "precautions": ["Eat iron-rich foods (spinach, red meat)", "Consume Vitamin C with iron", "Avoid tea with meals"],
        "next_actions": "Get a Complete Blood Count (CBC) test and consult General Physician."
    }
}

# Mapping of diseases to typical symptoms for dataset generation
DISEASE_SYMPTOMS_MAP = {
    "Diabetes Type 2": ["polyuria", "polydipsia", "fatigue", "weight_loss", "blurry_vision"],
    "Hypertension": ["headache", "shortness_of_breath", "nosebleeds", "dizziness", "chest_pain"],
    "Hypercholesterolemia": ["chest_pain", "dizziness", "fatigue"],
    "Influenza": ["fever", "chills", "cough", "sore_throat", "muscle_aches", "fatigue"],
    "Dermatitis": ["itchy_skin", "red_rash", "dry_skin", "skin_blisters"],
    "Migraine": ["severe_headache", "nausea", "sensitivity_to_light", "sensitivity_to_sound", "aura"],
    "Celiac Disease": ["diarrhea", "bloating", "abdominal_pain", "weight_loss", "fatigue"],
    "Cystic Fibrosis": ["cough", "shortness_of_breath", "salty_skin", "poor_growth"],
    "ALS (Amyotrophic Lateral Sclerosis)": ["muscle_weakness", "slurred_speech", "muscle_cramps", "difficulty_swallowing"],
    "Huntington's Disease": ["involuntary_movements", "cognitive_decline", "balance_issues", "depression"],
    "Lupus": ["joint_pain", "butterfly_rash", "fever", "fatigue", "hair_loss"],
    "Gastroesophageal Reflux (GERD)": ["heartburn", "acid_reflux", "chest_pain", "difficulty_swallowing"],
    "Rheumatoid Arthritis": ["joint_stiffness", "swollen_joints", "fatigue", "joint_pain"],
    "Hypothyroidism": ["weight_gain", "dry_skin", "cold_intolerance", "fatigue", "muscle_weakness"],
    "Anemia": ["pale_skin", "fatigue", "weakness", "cold_hands", "dizziness"]
}

# Drug Recommendations Mapping Database
DRUG_RECOMMENDATION_DATABASE = {
    "Diabetes Type 2": {
        "medicines": [
            {"name": "Metformin", "dosage": "500mg", "timing": "Twice daily with breakfast and dinner"},
            {"name": "Glipizide", "dosage": "5mg", "timing": "Once daily, 30 minutes before breakfast"}
        ],
        "side_effects": "Nausea, diarrhea, abdominal discomfort, metallic taste, vitamin B12 deficiency.",
        "food_restrictions": "Limit alcohol (increases risk of lactic acidosis), monitor simple sugars intake.",
        "precautions": "Monitor kidney function annually; check blood sugar levels regularly.",
        "alternatives": "Pioglitazone, Sitagliptin",
        "generic_medicines": "Metformin HCL (Generic)",
        "emergency_warnings": "Seek emergency care if experiencing rapid breathing, deep sweating, or extreme confusion (lactic acidosis/hypoglycemia)."
    },
    "Hypertension": {
        "medicines": [
            {"name": "Lisinopril", "dosage": "10mg", "timing": "Once daily in the morning"},
            {"name": "Amlodipine", "dosage": "5mg", "timing": "Once daily at the same time"}
        ],
        "side_effects": "Dry cough, dizziness, headache, high potassium levels, swelling in ankles.",
        "food_restrictions": "Avoid salt substitutes containing potassium; limit high-sodium foods.",
        "precautions": "Check kidney function and blood pressure daily. Do not stop taking abruptly.",
        "alternatives": "Losartan, Valsartan",
        "generic_medicines": "Lisinopril (Generic)",
        "emergency_warnings": "Seek emergency help for swelling of face, lips, tongue, or difficulty breathing (angioedema)."
    },
    "Hypercholesterolemia": {
        "medicines": [
            {"name": "Atorvastatin", "dosage": "20mg", "timing": "Once daily in the evening"},
            {"name": "Rosuvastatin", "dosage": "10mg", "timing": "Once daily at bedtime"}
        ],
        "side_effects": "Muscle aches, headache, mild increase in blood sugar, liver enzyme elevation.",
        "food_restrictions": "Avoid grapefruit or grapefruit juice (increases drug concentration).",
        "precautions": "Periodic liver enzyme tests required. Report unexplained muscle pain immediately.",
        "alternatives": "Simvastatin, Ezetimibe",
        "generic_medicines": "Atorvastatin Calcium (Generic)",
        "emergency_warnings": "Contact doctor immediately if experiencing dark-colored urine or severe muscle weakness (rhabdomyolysis)."
    },
    "Influenza": {
        "medicines": [
            {"name": "Oseltamivir (Tamiflu)", "dosage": "75mg", "timing": "Twice daily for 5 days"},
            {"name": "Paracetamol (Tylenol)", "dosage": "650mg", "timing": "Every 6 hours as needed for fever"}
        ],
        "side_effects": "Nausea, vomiting, headache, dizziness.",
        "food_restrictions": "None. Take with food to minimize stomach upset.",
        "precautions": "Must start within 48 hours of symptom onset for maximum effectiveness.",
        "alternatives": "Baloxavir Marboxil, Ibuprofen",
        "generic_medicines": "Oseltamivir Phosphate (Generic)",
        "emergency_warnings": "Seek emergency care for difficulty breathing, chest pain, or sudden confusion."
    },
    "Dermatitis": {
        "medicines": [
            {"name": "Hydrocortisone Cream 1%", "dosage": "Apply thin layer", "timing": "Twice daily to affected skin"},
            {"name": "Cetirizine (Zyrtec)", "dosage": "10mg", "timing": "Once daily at bedtime for itching"}
        ],
        "side_effects": "Skin thinning (prolonged steroid use), local irritation, drowsiness (from antihistamine).",
        "food_restrictions": "Avoid foods known to trigger your specific allergic eczema.",
        "precautions": "Do not apply steroid cream on face or broken skin unless directed by dermatologist.",
        "alternatives": "Clobetasol, Elidel Cream",
        "generic_medicines": "Hydrocortisone 1% Cream (Generic)",
        "emergency_warnings": "Seek care if rash becomes hot, oozes yellow pus, or spreads rapidly (bacterial infection)."
    },
    "Migraine": {
        "medicines": [
            {"name": "Sumatriptan", "dosage": "50mg", "timing": "Take one tablet at the onset of migraine"},
            {"name": "Naproxen", "dosage": "500mg", "timing": "Take with food for pain relief"}
        ],
        "side_effects": "Tingling sensation, chest tightness, drowsiness, dry mouth.",
        "food_restrictions": "Avoid aged cheeses, red wine, chocolate, and foods containing MSG (common triggers).",
        "precautions": "Do not use Sumatriptan if you have history of coronary artery disease.",
        "alternatives": "Rizatriptan, Ibuprofen 400mg",
        "generic_medicines": "Sumatriptan Succinate (Generic)",
        "emergency_warnings": "Seek emergency services if migraine is accompanied by one-sided weakness, slurred speech, or vision loss."
    },
    "Celiac Disease": {
        "medicines": [
            {"name": "Multivitamins (Gluten-Free)", "dosage": "1 tablet", "timing": "Once daily with food"},
            {"name": "Calcium & Vit D", "dosage": "500mg/400IU", "timing": "Twice daily"}
        ],
        "side_effects": "Constipation (from calcium), mild stomach upset.",
        "food_restrictions": "STRICT avoidance of wheat, barley, rye, malt, and triticale.",
        "precautions": "Check all labels, cosmetics, and prescription excipients for gluten sources.",
        "alternatives": "None. Strict diet is primary therapy.",
        "generic_medicines": "N/A",
        "emergency_warnings": "Report severe abdominal pain, persistent vomiting, or rapid weight loss to your gastroenterologist."
    },
    "Cystic Fibrosis": {
        "medicines": [
            {"name": "Dornase Alfa (Pulmozyme)", "dosage": "2.5mg", "timing": "Once daily via nebulizer"},
            {"name": "Pancrelipase (Creon)", "dosage": "Capsules", "timing": "Take with every meal and snack"}
        ],
        "side_effects": "Hoarseness, pharyngitis, chest pain, abdominal cramps.",
        "food_restrictions": "High-calorie, high-fat diet required. Supplemental fat-soluble vitamins (A, D, E, K).",
        "precautions": "Maintain strict airway clearance routine. Avoid contact with others who have cystic fibrosis.",
        "alternatives": "Ivacaftor, Symdeko",
        "generic_medicines": "Creon (Brand is highly standard)",
        "emergency_warnings": "Seek emergency care for coughing up blood (hemoptysis) or severe chest pain/sudden breathlessness."
    },
    "ALS (Amyotrophic Lateral Sclerosis)": {
        "medicines": [
            {"name": "Riluzole", "dosage": "50mg", "timing": "Twice daily, 1 hour before or 2 hours after meals"},
            {"name": "Baclofen", "dosage": "10mg", "timing": "Three times daily for muscle spasms"}
        ],
        "side_effects": "Nausea, dizziness, weakness, liver function changes, sleepiness.",
        "food_restrictions": "High-protein, soft or pureed foods if swallowing is difficult.",
        "precautions": "Perform liver function tests every month for the first 3 months.",
        "alternatives": "Edaravone (Radicava), Tizanidine",
        "generic_medicines": "Riluzole (Generic)",
        "emergency_warnings": "Contact physician immediately if experiencing severe choking, shortness of breath, or chest infections."
    },
    "Huntington's Disease": {
        "medicines": [
            {"name": "Tetrabenazine", "dosage": "12.5mg", "timing": "Once daily in the morning, gradually adjusted"},
            {"name": "Sertraline (Zoloft)", "dosage": "50mg", "timing": "Once daily for mood management"}
        ],
        "side_effects": "Drowsiness, depression, anxiety, balance problems, dry mouth.",
        "food_restrictions": "Avoid alcohol; ensure high-calorie intake due to high metabolic expenditure from chorea.",
        "precautions": "Monitor closely for suicidal ideation, depression, or severe behavioral changes.",
        "alternatives": "Deutetrabenazine, Haloperidol",
        "generic_medicines": "Tetrabenazine (Generic)",
        "emergency_warnings": "Seek immediate psychiatric care for thoughts of self-harm or severe aggression."
    },
    "Lupus": {
        "medicines": [
            {"name": "Hydroxychloroquine (Plaquenil)", "dosage": "200mg", "timing": "Once or twice daily with food"},
            {"name": "Prednisone", "dosage": "5mg", "timing": "Once daily in the morning with food"}
        ],
        "side_effects": "Stomach upset, retinal changes (rare but serious), mood changes, weight gain, high BP.",
        "food_restrictions": "Avoid alfalfa sprouts (contains L-canavanine, which can trigger flares).",
        "precautions": "Annual comprehensive eye exams required for Hydroxychloroquine.",
        "alternatives": "Methotrexate, Belimumab",
        "generic_medicines": "Hydroxychloroquine Sulfate (Generic)",
        "emergency_warnings": "Seek emergency care for high fever, sudden shortness of breath, or chest pain (pleurisy/carditis)."
    },
    "Gastroesophageal Reflux (GERD)": {
        "medicines": [
            {"name": "Omeprazole", "dosage": "20mg", "timing": "Once daily 30 minutes before first meal"},
            {"name": "Famotidine", "dosage": "20mg", "timing": "Once daily at bedtime"}
        ],
        "side_effects": "Headache, abdominal pain, flatulence, long-term B12/magnesium deficiency.",
        "food_restrictions": "Avoid citrus fruits, tomatoes, caffeine, chocolate, mint, carbonated drinks.",
        "precautions": "Do not lie down within 3 hours after eating. Elevate head of bed.",
        "alternatives": "Pantoprazole, Esomeprazole",
        "generic_medicines": "Omeprazole Delayed Release (Generic)",
        "emergency_warnings": "Seek emergency care if chest pain radiates to arm/jaw or is accompanied by sweating."
    },
    "Rheumatoid Arthritis": {
        "medicines": [
            {"name": "Methotrexate", "dosage": "7.5mg", "timing": "ONCE WEEKLY (Critical: Do not take daily)"},
            {"name": "Folic Acid", "dosage": "1mg", "timing": "Once daily on days Methotrexate is NOT taken"}
        ],
        "side_effects": "Nausea, fatigue, mouth sores, liver toxicity, increased risk of infection.",
        "food_restrictions": "Strictly avoid alcohol (increases liver damage risk).",
        "precautions": "Regular blood tests (CBC, liver/kidney function). Use reliable birth control.",
        "alternatives": "Leflunomide, Adalimumab (Humira)",
        "generic_medicines": "Methotrexate Sodium (Generic)",
        "emergency_warnings": "Contact doctor immediately for signs of infection (fever, chills), dry cough, or yellowing skin."
    },
    "Hypothyroidism": {
        "medicines": [
            {"name": "Levothyroxine", "dosage": "50mcg", "timing": "Once daily in morning 60 mins before breakfast"}
        ],
        "side_effects": "Usually well tolerated; signs of excess dose include racing heart, sweating, insomnia.",
        "food_restrictions": "Avoid soy, calcium, or iron supplements within 4 hours of taking medication.",
        "precautions": "Check TSH levels in 6-8 weeks after starting or modifying dose.",
        "alternatives": "Synthroid, Armour Thyroid",
        "generic_medicines": "Levothyroxine Sodium (Generic)",
        "emergency_warnings": "Go to hospital if experiencing extreme fatigue, low body temperature, or confusion (myxedema coma)."
    },
    "Anemia": {
        "medicines": [
            {"name": "Ferrous Sulfate (Iron)", "dosage": "325mg", "timing": "Once daily on empty stomach with Vitamin C"},
            {"name": "Vitamin C (Ascorbic Acid)", "dosage": "500mg", "timing": "Take together with Iron"}
        ],
        "side_effects": "Dark stools, constipation, nausea, metallic taste, heartburn.",
        "food_restrictions": "Avoid coffee, tea, calcium, or antacids within 2 hours of taking iron.",
        "precautions": "Take with a light meal only if stomach upset is severe (though absorption decreases).",
        "alternatives": "Iron Gluconate, Intravenous Iron",
        "generic_medicines": "Ferrous Sulfate (Generic)",
        "emergency_warnings": "Seek care if experiencing severe abdominal cramping, vomiting blood, or rapid heartbeat."
    }
}

class HealthcareMLModel:
    def __init__(self):
        self.mlb = MultiLabelBinarizer()
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model_file = "curaai_model.pkl"
        self.binarizer_file = "curaai_mlb.pkl"
        self.is_trained = False
        self.train_and_save()

    def train_and_save(self):
        """Generates synthetic patient records matching symptoms and diseases, then trains the model."""
        # 1. Prepare synthetic dataset
        data = []
        labels = []
        
        # Generate 60 records for each disease with slight variations (noise)
        np.random.seed(42)
        for disease, symptoms in DISEASE_SYMPTOMS_MAP.items():
            for _ in range(60):
                # Always include core symptoms
                patient_symptoms = list(symptoms)
                
                # Randomly drop 1 symptom (sometimes patients don't have all symptoms)
                if len(patient_symptoms) > 2 and np.random.rand() > 0.3:
                    drop_idx = np.random.randint(0, len(patient_symptoms))
                    patient_symptoms.pop(drop_idx)
                
                # Randomly add 1-2 other random symptoms (noise)
                if np.random.rand() > 0.5:
                    noise_count = np.random.randint(1, 3)
                    for _ in range(noise_count):
                        rand_sym = np.random.choice(ALL_SYMPTOMS)
                        if rand_sym not in patient_symptoms:
                            patient_symptoms.append(rand_sym)
                
                data.append(patient_symptoms)
                labels.append(disease)

        # 2. Fit MultiLabelBinarizer
        self.mlb.fit([ALL_SYMPTOMS])
        X = self.mlb.transform(data)
        y = np.array(labels)

        # 3. Train Random Forest
        self.model.fit(X, y)
        self.is_trained = True

        # Save to disk
        try:
            with open(self.model_file, 'wb') as f:
                pickle.dump(self.model, f)
            with open(self.binarizer_file, 'wb') as f:
                pickle.dump(self.mlb, f)
        except Exception as e:
            print(f"[ML Model] Failed to save model file: {e}")

    def predict_disease(self, active_symptoms):
        """Predicts disease based on symptom list. Returns predictions with confidence percentages."""
        if not active_symptoms:
            return [{
                "disease": "No symptoms provided",
                "confidence": 100.0,
                "category": "common",
                "severity": "low",
                "is_rare": False,
                "precautions": ["Rest", "Keep active", "Stay hydrated"],
                "next_actions": "Enter symptoms to perform an AI assessment."
            }]

        # Filter symptoms to valid ones
        valid_symptoms = [s for s in active_symptoms if s in ALL_SYMPTOMS]
        if not valid_symptoms:
            return [{
                "disease": "Inconclusive diagnosis",
                "confidence": 100.0,
                "category": "common",
                "severity": "low",
                "is_rare": False,
                "precautions": ["Rest", "Consult General Physician"],
                "next_actions": "Please select standard symptoms from the diagnostic list."
            }]

        # Binarize input
        x_vec = self.mlb.transform([valid_symptoms])
        
        # Get probability distributions
        probs = self.model.predict_proba(x_vec)[0]
        classes = self.model.classes_
        
        # Zip and sort by probability
        predictions = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)
        
        results = []
        # Return top 3 predictions
        for disease, prob in predictions[:3]:
            # Convert probability to percentage
            conf = float(prob * 100)
            if conf < 1.0:
                continue

            metadata = DISEASE_METADATA.get(disease, {
                "category": "common",
                "severity": "low",
                "is_rare": False,
                "precautions": ["Monitor symptoms", "Consult physician"],
                "next_actions": "Consult a health specialist."
            })

            results.append({
                "disease": disease,
                "confidence": round(conf, 2),
                "category": metadata["category"],
                "severity": metadata["severity"],
                "is_rare": metadata["is_rare"],
                "precautions": metadata["precautions"],
                "next_actions": metadata["next_actions"]
            })
        
        if not results:
            results.append({
                "disease": "Undetermined Health Condition",
                "confidence": 100.0,
                "category": "common",
                "severity": "medium",
                "is_rare": False,
                "precautions": ["Keep hydrated", "Avoid stress", "Monitor vital signs"],
                "next_actions": "Review symptoms with a general practitioner."
            })
            
        return results

    def get_drug_recommendations(self, disease, patient_profile=None):
        """Generates drug recommendations based on disease and patient factors (allergies, weight, age)."""
        recs = DRUG_RECOMMENDATION_DATABASE.get(disease)
        
        if not recs:
            return {
                "medicines": [{"name": "General Therapeutic Care", "dosage": "As directed", "timing": "As needed"}],
                "side_effects": "Varies by treatment.",
                "food_restrictions": "Maintain a balanced, nutritious diet.",
                "precautions": "Discuss therapy options with your medical provider.",
                "alternatives": "Alternative therapies available.",
                "generic_medicines": "Generic options available.",
                "emergency_warnings": "Seek professional help for severe reactions."
            }

        # Adapt based on patient profile (age, weight, history, allergies)
        adapted_recs = dict(recs)
        
        if patient_profile:
            age = patient_profile.get("age")
            weight = patient_profile.get("weight")
            history = patient_profile.get("medical_history", "").lower()
            
            # Age adjustment
            if age and age < 12:
                # Pediatric dosing reduction
                adapted_recs["medicines"] = [
                    {"name": med["name"], "dosage": "Half Adult Dose (Pediatric)", "timing": med["timing"]} 
                    for med in recs["medicines"]
                ]
                adapted_recs["precautions"] += " PEDIATRIC ALERT: Adjust dosage carefully based on pediatric chart."
            elif age and age > 65:
                # Geriatric dosing caution
                adapted_recs["precautions"] += " GERIATRIC WARNING: Monitor renal clearance closely in elderly patients."

            # Allergy checks
            allergies = patient_profile.get("allergies", "").lower()
            if allergies:
                conflict_found = False
                for med in recs["medicines"]:
                    if med["name"].lower() in allergies:
                        conflict_found = True
                
                if conflict_found:
                    adapted_recs["emergency_warnings"] += " ALLERGY DETECTED: Patient is allergic to recommended first-line drugs. Switch immediately to alternative medicines listed."

        return adapted_recs

    def get_health_recommendations(self, disease, age, weight, bmi, medical_history=""):
        """Generates comprehensive lifestyle, diet, exercise, and hydration recommendations."""
        # Baseline habits
        daily_habits = ["Aim for 7-8 hours of sleep daily", "Maintain proper posture during work", "Take 5-minute movement breaks every hour"]
        exercise = ["Walk 10,000 steps daily", "Perform light stretching morning and night"]
        diet = ["Include lean protein with meals", "Eat 3-5 servings of vegetables daily", "Limit added sugars and processed foods"]
        sleep = ["Go to bed at same time every night", "Avoid blue light screens 1 hour before sleep"]
        stress = ["Practice 10 minutes of deep belly breathing (Box Breathing)", "Perform progress muscle relaxation"]
        water = 2500  # ml

        # Condition-specific tweaks
        if disease == "Diabetes Type 2":
            diet.extend(["Focus on low-glycemic foods (whole grains, legumes)", "Avoid carbonated sodas and white bread", "Consume fiber-rich foods"])
            exercise.extend(["Perform 30 minutes of aerobic exercise (brisk walking, cycling) daily", "Do bodyweight resistance exercises twice a week"])
            daily_habits.extend(["Examine feet daily for cuts or sores", "Monitor post-meal blood sugar levels"])
        elif disease == "Hypertension":
            diet.extend(["Adopt the DASH diet (Dietary Approaches to Stop Hypertension)", "Restrict daily sodium intake to less than 1,500mg", "Increase potassium-rich foods (bananas, spinach)"])
            exercise.extend(["Engage in moderate swimming, cycling, or brisk walking", "Avoid heavy weightlifting (can spike BP)"])
            stress.extend(["Practice 15 minutes of guided mindfulness meditation daily", "Engage in gentle Hatha Yoga"])
        elif disease == "Hypercholesterolemia":
            diet.extend(["Limit saturated fats and trans fats", "Increase soluble fiber (oats, barley, beans)", "Add healthy fats like avocados, olive oil, and almonds"])
            exercise.extend(["Engage in 40 minutes of moderate-to-vigorous aerobic exercise 3-4 times per week"])
        elif disease == "Migraine":
            daily_habits.extend(["Keep a headache journal to identify triggers", "Eat meals at consistent times (do not skip meals)"])
            sleep.extend(["Avoid oversleeping on weekends", "Keep bedroom cool and dark"])
            stress.extend(["Practice restorative yoga", "Try biofeedback or progressive muscle relaxation"])
        elif disease == "Anemia":
            diet.extend(["Eat iron-rich foods (red meat, poultry, seafood, lentils, spinach)", "Pair iron-rich foods with Vitamin C (citrus, bell peppers) to boost absorption"])
            daily_habits.extend(["Avoid drinking tea or coffee directly with or after meals"])
            exercise = ["Engage in low-intensity walking", "Avoid highly strenuous training sessions until hemoglobin improves"]

        # Age customizations
        if age and age > 60:
            exercise = ["Perform low-impact exercises like water aerobics or chair yoga", "Do balance training exercises to prevent falls"]
            sleep.extend(["Ensure room is free of tripping hazards for nighttime restroom visits"])
        
        # BMI customizations
        if bmi and bmi > 25.0:
            exercise.append("Aim for 150-300 minutes of moderate intensity exercise weekly")
            diet.append("Incorporate caloric control; focus on nutrient-dense, lower-calorie foods")
            water = max(water, 3000)
        elif bmi and bmi < 18.5:
            diet.append("Focus on healthy weight gain with nutrient-dense high-calorie foods (nuts, dairy, avocados)")
            exercise = ["Perform strength/resistance training to build muscle mass", "Limit excessive cardio burn"]

        # Water logic based on weight
        if weight:
            # General rule: ~35ml of water per kg of bodyweight
            water = int(weight * 35)
            # Clip between reasonable ranges
            water = max(1500, min(water, 4500))

        # Format into clean lists
        return {
            "daily_habits": daily_habits,
            "exercise": exercise,
            "diet": diet,
            "sleep": sleep,
            "stress": stress,
            "water_target_ml": water,
            "lifestyle_plan": {
                "foods_to_avoid": [
                    "Ultra-processed meals", "High-fructose corn syrups", "Trans fats & deep-fried foods"
                ] + (["Refined carbs, sugars, white rice"] if disease == "Diabetes Type 2" else [])
                  + (["High sodium foods, canned soups, pickles"] if disease == "Hypertension" else [])
                  + (["Processed meats, butter, fast foods"] if disease == "Hypercholesterolemia" else []),
                "foods_to_consume": [
                    "Leafy green vegetables", "Lean proteins (fish, chicken, tofu)", "Berries and citrus fruits"
                ] + (["Oats, lentils, almonds"] if disease == "Hypercholesterolemia" else [])
                  + (["Spinach, red meat, beans"] if disease == "Anemia" else []),
                "yoga_suggestions": [
                    "Tadasana (Mountain Pose) for posture",
                    "Balasana (Child's Pose) for stress reduction",
                    "Savasana (Corpse Pose) for relaxation"
                ] + (["Virasana (Hero Pose) for digestion"] if disease == "Gastroesophageal Reflux (GERD)" else []),
                "meditation_recommendations": [
                    "10 minutes of Mindfulness Breathing",
                    "Guided Body Scan Meditation before sleep"
                ]
            }
        }

# Instantiate model
ai_engine = HealthcareMLModel()

# ─────────────────────────────────────────────────────────────────
# NATURAL LANGUAGE SYMPTOM PARSER
# Maps free-text user descriptions to known symptom tokens.
# ─────────────────────────────────────────────────────────────────

NLP_KEYWORD_MAP = {
    # Pain & chest
    "chest pain": "chest_pain", "chest tightness": "chest_pain",
    "sharp chest": "chest_pain", "chest pressure": "chest_pain",
    # Breathing
    "short of breath": "shortness_of_breath", "breathing difficulty": "shortness_of_breath",
    "breathless": "shortness_of_breath", "can't breathe": "shortness_of_breath",
    "trouble breathing": "shortness_of_breath",
    # Head
    "headache": "headache", "head pain": "headache", "head ache": "headache",
    "migraine": "severe_headache", "throbbing head": "severe_headache",
    "severe headache": "severe_headache",
    # Vision
    "blurry vision": "blurry_vision", "blurred vision": "blurry_vision",
    "vision blur": "blurry_vision", "can't see clearly": "blurry_vision",
    # Dizziness
    "dizzy": "dizziness", "dizziness": "dizziness", "vertigo": "dizziness",
    "light headed": "dizziness", "lightheaded": "dizziness",
    # Fatigue
    "tired": "fatigue", "fatigue": "fatigue", "exhausted": "fatigue",
    "weakness": "weakness", "weak": "weakness", "no energy": "fatigue",
    # Fever / Chills
    "fever": "fever", "high temperature": "fever", "temperature": "fever",
    "chills": "chills", "shivering": "chills", "cold sweats": "chills",
    # Cough / Throat
    "cough": "cough", "coughing": "cough", "sore throat": "sore_throat",
    "throat pain": "sore_throat", "scratchy throat": "sore_throat",
    # Nausea / Stomach
    "nausea": "nausea", "nauseous": "nausea", "vomit": "nausea",
    "stomach pain": "abdominal_pain", "abdominal pain": "abdominal_pain",
    "belly pain": "abdominal_pain", "bloating": "bloating", "bloated": "bloating",
    "heartburn": "heartburn", "acid reflux": "acid_reflux", "indigestion": "heartburn",
    "diarrhea": "diarrhea", "loose stools": "diarrhea",
    # Skin
    "itchy skin": "itchy_skin", "skin itch": "itchy_skin", "rash": "red_rash",
    "skin rash": "red_rash", "dry skin": "dry_skin", "skin blisters": "skin_blisters",
    "butterfly rash": "butterfly_rash", "hair loss": "hair_loss",
    # Joints & Muscles
    "joint pain": "joint_pain", "joints hurt": "joint_pain",
    "muscle ache": "muscle_aches", "muscle pain": "muscle_aches",
    "joint stiffness": "joint_stiffness", "stiff joints": "joint_stiffness",
    "swollen joints": "swollen_joints",
    "muscle weakness": "muscle_weakness", "muscle cramps": "muscle_cramps",
    # Urination / Thirst
    "frequent urination": "polyuria", "urinating often": "polyuria", "polyuria": "polyuria",
    "excessive thirst": "polydipsia", "always thirsty": "polydipsia",
    # Neuro
    "slurred speech": "slurred_speech", "balance issues": "balance_issues",
    "involuntary movements": "involuntary_movements", "tremors": "involuntary_movements",
    "cognitive decline": "cognitive_decline", "memory loss": "cognitive_decline",
    "difficulty swallowing": "difficulty_swallowing",
    # Weight changes
    "weight loss": "weight_loss", "losing weight": "weight_loss",
    "weight gain": "weight_gain", "gaining weight": "weight_gain",
    # Misc
    "pale skin": "pale_skin", "cold hands": "cold_hands",
    "nosebleed": "nosebleeds", "nose bleed": "nosebleeds",
    "depression": "depression", "depressed": "depression",
    "poor growth": "poor_growth", "salty skin": "salty_skin",
    "sensitivity to light": "sensitivity_to_light", "light sensitivity": "sensitivity_to_light",
    "sensitivity to sound": "sensitivity_to_sound", "aura": "aura",
    "cold intolerance": "cold_intolerance", "always cold": "cold_intolerance",
}

def parse_natural_language_symptoms(text):
    """
    Parses free-text symptom descriptions into structured symptom tokens.
    Returns (matched_symptoms: list, unmatched_text: list)
    """
    text_lower = text.lower()
    matched = set()
    
    # Sort by length descending so longer phrases match first
    for phrase, token in sorted(NLP_KEYWORD_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if phrase in text_lower:
            matched.add(token)
    
    return list(matched)


# ─────────────────────────────────────────────────────────────────
# URGENCY LEVEL CLASSIFIER
# ─────────────────────────────────────────────────────────────────

EMERGENCY_SYMPTOMS = {
    "chest_pain", "shortness_of_breath", "slurred_speech", "involuntary_movements",
    "difficulty_swallowing", "severe_headache"
}
SEVERE_SYMPTOMS = {
    "muscle_weakness", "balance_issues", "cognitive_decline", "butterfly_rash",
    "cough", "nosebleeds", "poor_growth", "salty_skin"
}
MODERATE_SYMPTOMS = {
    "headache", "dizziness", "fatigue", "joint_pain", "muscle_aches",
    "abdominal_pain", "heartburn", "acid_reflux", "bloating", "nausea",
    "polyuria", "polydipsia", "blurry_vision", "weight_loss", "weight_gain",
    "swollen_joints", "joint_stiffness", "hair_loss", "depression"
}

def classify_urgency(symptoms, description="", duration_days=0):
    """
    Returns urgency dict: level (Mild/Moderate/Severe/Emergency), color, advice.
    """
    sym_set = set(symptoms)

    # Duration escalation
    if duration_days and duration_days > 14:
        # Escalate one level if symptom persists > 2 weeks
        duration_boost = True
    else:
        duration_boost = False

    emergency_hit = sym_set & EMERGENCY_SYMPTOMS
    severe_hit = sym_set & SEVERE_SYMPTOMS

    # Hard keyword escalation from description
    emergency_words = ["can't breathe", "cannot breathe", "unconscious", "collapse",
                        "heart attack", "stroke", "severe pain", "emergency"]
    desc_emergency = any(w in description.lower() for w in emergency_words)

    if emergency_hit or desc_emergency:
        return {
            "level": "Emergency",
            "color": "red",
            "icon": "🚨",
            "advice": "Seek immediate emergency medical attention or call 112/911. Do NOT delay.",
            "urgency_score": 4
        }
    elif severe_hit or duration_boost:
        return {
            "level": "Severe",
            "color": "orange",
            "icon": "⚠️",
            "advice": "Consult a doctor within 24 hours. Avoid physical strain.",
            "urgency_score": 3
        }
    elif sym_set & MODERATE_SYMPTOMS:
        return {
            "level": "Moderate",
            "color": "yellow",
            "icon": "🔶",
            "advice": "Schedule a doctor appointment within 2–3 days. Monitor symptoms closely.",
            "urgency_score": 2
        }
    else:
        return {
            "level": "Mild",
            "color": "green",
            "icon": "✅",
            "advice": "Rest, stay hydrated, and monitor symptoms. Consult if they worsen.",
            "urgency_score": 1
        }


# ─────────────────────────────────────────────────────────────────
# AI DOCTOR SPECIALIZATION RECOMMENDER
# ─────────────────────────────────────────────────────────────────

DISEASE_TO_SPECIALIZATION = {
    "Diabetes Type 2": "Diabetologist",
    "Hypertension": "Cardiologist",
    "Hypercholesterolemia": "Cardiologist",
    "Influenza": "General Physician",
    "Dermatitis": "Dermatologist",
    "Migraine": "Neurologist",
    "Celiac Disease": "Gastroenterologist",
    "Cystic Fibrosis": "Pulmonologist",
    "ALS (Amyotrophic Lateral Sclerosis)": "Neurologist",
    "Huntington's Disease": "Neurologist",
    "Lupus": "Rheumatologist",
    "Gastroesophageal Reflux (GERD)": "Gastroenterologist",
    "Rheumatoid Arthritis": "Orthopedic",
    "Hypothyroidism": "Endocrinologist",
    "Anemia": "General Physician",
}

SYMPTOM_TO_SPECIALIZATION = {
    "chest_pain": "Cardiologist",
    "shortness_of_breath": "Pulmonologist",
    "severe_headache": "Neurologist",
    "headache": "Neurologist",
    "dizziness": "Neurologist",
    "balance_issues": "Neurologist",
    "slurred_speech": "Neurologist",
    "involuntary_movements": "Neurologist",
    "cognitive_decline": "Neurologist",
    "itchy_skin": "Dermatologist",
    "red_rash": "Dermatologist",
    "skin_blisters": "Dermatologist",
    "butterfly_rash": "Dermatologist",
    "joint_pain": "Orthopedic",
    "joint_stiffness": "Orthopedic",
    "swollen_joints": "Orthopedic",
    "polyuria": "Diabetologist",
    "polydipsia": "Diabetologist",
    "heartburn": "Gastroenterologist",
    "acid_reflux": "Gastroenterologist",
    "abdominal_pain": "Gastroenterologist",
    "bloating": "Gastroenterologist",
    "cold_intolerance": "Endocrinologist",
    "weight_gain": "Endocrinologist",
    "pale_skin": "General Physician",
    "fatigue": "General Physician",
}

def recommend_specialization(disease=None, symptoms=None):
    """
    Returns recommended doctor specialization and reasoning.
    Priority: disease match > symptom emergency match > symptom general match.
    """
    reason = []

    # Disease-based match first
    if disease and disease in DISEASE_TO_SPECIALIZATION:
        spec = DISEASE_TO_SPECIALIZATION[disease]
        reason.append(f"Primary diagnosis '{disease}' is best managed by a {spec}.")
        return {"specialization": spec, "reason": "; ".join(reason)}

    # Symptom-based match
    if symptoms:
        # Emergency symptoms get priority
        for sym in symptoms:
            if sym in EMERGENCY_SYMPTOMS and sym in SYMPTOM_TO_SPECIALIZATION:
                spec = SYMPTOM_TO_SPECIALIZATION[sym]
                reason.append(f"Critical symptom '{sym.replace('_',' ')}' requires a {spec}.")
                return {"specialization": spec, "reason": "; ".join(reason)}

        # General symptom match — pick most frequent specialization vote
        votes = {}
        for sym in symptoms:
            if sym in SYMPTOM_TO_SPECIALIZATION:
                sp = SYMPTOM_TO_SPECIALIZATION[sym]
                votes[sp] = votes.get(sp, 0) + 1

        if votes:
            best = max(votes, key=votes.get)
            reason.append(f"{votes[best]} symptom(s) suggest a {best}.")
            return {"specialization": best, "reason": "; ".join(reason)}

    return {"specialization": "General Physician", "reason": "No specific specialization match; a General Physician can triage."}
