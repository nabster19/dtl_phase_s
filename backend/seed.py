# seed.py - Database Seeding Utility for CuraAI
# Sets up default users, 6 sample doctors, and 7 days of health record telemetry.

import bcrypt
from database import db
from datetime import datetime, timedelta

def hash_password(password):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def seed_database():
    print("[CuraAI Seed] Seeding database...")
    
    # 1. Clear or check existing users
    try:
        user_check = db.fetch_all("SELECT * FROM users LIMIT 1")
        if user_check:
            print("[CuraAI Seed] Data already exists. Skipping seeding.")
            return
    except Exception as e:
        print(f"[CuraAI Seed] Database check failed: {e}. Attempting to run seeding anyway.")

    # 2. Add Users & Roles
    print("[CuraAI Seed] Creating users...")
    patient_pw = hash_password("password123")
    doctor_pw = hash_password("docpassword123")
    admin_pw = hash_password("adminpassword123")

    # Patient (John Doe - target 7795273421)
    patient_user_id = db.execute_query(
        "INSERT INTO users (name, mobile_number, password_hash, role) VALUES (%s, %s, %s, %s)",
        ("John Doe", "7795273421", patient_pw, "patient")
    )
    # Admin (Admin User - target 7019113622)
    admin_user_id = db.execute_query(
        "INSERT INTO users (name, mobile_number, password_hash, role) VALUES (%s, %s, %s, %s)",
        ("System Admin", "7019113622", admin_pw, "admin")
    )

    # 3. Add Patients profile
    patient_id = db.execute_query(
        """INSERT INTO patients (user_id, name, age, gender, blood_group, weight, height, address, medical_history, allergies, medications, emergency_contact) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (patient_user_id, "John Doe", 45, "Male", "O+", 82.5, 175.0, "123 Healthcare Blvd, Medical District", "Hypertension, Pre-Diabetes", "Penicillin", "Metformin 500mg twice daily", "+91 9876543210")
    )

    # 4. Add Doctors & Users
    doctors_data = [
        {"name": "Dr. Rajesh Sharma",    "spec": "Cardiologist",      "exp": 18, "avail": "Mon-Wed 09:00 - 13:00", "fees": 800.00,  "rating": 4.90, "mobile": "9998887771"},
        {"name": "Dr. Priya Nair",       "spec": "Neurologist",       "exp": 14, "avail": "Tue-Thu 10:00 - 15:00", "fees": 900.00,  "rating": 4.85, "mobile": "9998887772"},
        {"name": "Dr. Suresh Patel",     "spec": "General Physician", "exp": 10, "avail": "Mon-Fri 08:00 - 12:00", "fees": 400.00,  "rating": 4.75, "mobile": "9998887773"},
        {"name": "Dr. Ananya Krishnan",  "spec": "Dermatologist",     "exp": 12, "avail": "Wed-Fri 13:00 - 17:00", "fees": 600.00,  "rating": 4.70, "mobile": "9998887774"},
        {"name": "Dr. Vikram Mehta",     "spec": "Orthopedic",        "exp": 16, "avail": "Mon-Thu 14:00 - 18:00", "fees": 700.00,  "rating": 4.90, "mobile": "9998887775"},
        {"name": "Dr. Kavitha Reddy",    "spec": "Diabetologist",     "exp": 13, "avail": "Tue-Fri 09:00 - 14:00", "fees": 650.00,  "rating": 4.88, "mobile": "9998887776"},
    ]

    print("[CuraAI Seed] Creating sample doctors...")
    for doc in doctors_data:
        doc_user_id = db.execute_query(
            "INSERT INTO users (name, mobile_number, password_hash, role) VALUES (%s, %s, %s, %s)",
            (doc["name"], doc["mobile"], doctor_pw, "doctor")
        )
        db.execute_query(
            """INSERT INTO doctors (user_id, name, specialization, experience, availability, consultation_fees, ratings, profile_pic) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (doc_user_id, doc["name"], doc["spec"], doc["exp"], doc["avail"], doc["fees"], doc["rating"], f"doctor_{doc['spec'].lower().replace(' ', '_')}.png")
        )


    # 5. Add Health records (7 days historical trend data for John Doe)
    print("[CuraAI Seed] Seeding health tracking telemetry...")
    base_date = datetime.now().date()
    
    # 7 days of fluctuating health metrics
    health_telemetry = [
        {"bp_sys": 138, "bp_dia": 88, "sugar": 145, "chol": 218, "weight": 83.2, "hr": 78, "o2": 97, "temp": 36.8, "water": 1800, "days_ago": 6},
        {"bp_sys": 136, "bp_dia": 87, "sugar": 138, "chol": 218, "weight": 83.0, "hr": 76, "o2": 98, "temp": 36.7, "water": 2000, "days_ago": 5},
        {"bp_sys": 140, "bp_dia": 90, "sugar": 150, "chol": 222, "weight": 82.9, "hr": 82, "o2": 97, "temp": 37.0, "water": 1500, "days_ago": 4},
        {"bp_sys": 135, "bp_dia": 85, "sugar": 128, "chol": 222, "weight": 82.7, "hr": 75, "o2": 99, "temp": 36.5, "water": 2500, "days_ago": 3},
        {"bp_sys": 132, "bp_dia": 84, "sugar": 120, "chol": 215, "weight": 82.6, "hr": 72, "o2": 98, "temp": 36.6, "water": 2200, "days_ago": 2},
        {"bp_sys": 130, "bp_dia": 82, "sugar": 115, "chol": 210, "weight": 82.5, "hr": 70, "o2": 98, "temp": 36.6, "water": 2800, "days_ago": 1},
        {"bp_sys": 128, "bp_dia": 80, "sugar": 108, "chol": 205, "weight": 82.4, "hr": 71, "o2": 99, "temp": 36.5, "water": 3000, "days_ago": 0}
    ]

    for record in health_telemetry:
        rec_date = base_date - timedelta(days=record["days_ago"])
        # Calculate BMI
        height_m = 1.75
        bmi = round(record["weight"] / (height_m * height_m), 2)
        
        db.execute_query(
            """INSERT INTO health_records 
               (patient_id, blood_pressure_sys, blood_pressure_dia, sugar_level, cholesterol, weight, height, bmi, heart_rate, oxygen_level, temperature, water_intake, recorded_date) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (patient_id, record["bp_sys"], record["bp_dia"], record["sugar"], record["chol"], record["weight"], 175.0, bmi, record["hr"], record["o2"], record["temp"], record["water"], rec_date)
        )

    # 6. Add Symptoms lookup database
    print("[CuraAI Seed] Seeding symptoms list...")
    symptoms_list = [
        ("fever", "common"), ("chills", "common"), ("cough", "common"), ("sore_throat", "common"), 
        ("muscle_aches", "common"), ("fatigue", "common"), ("polyuria", "chronic"), ("polydipsia", "chronic"), 
        ("weight_loss", "chronic"), ("blurry_vision", "chronic"), ("headache", "common"), 
        ("shortness_of_breath", "chronic"), ("nosebleeds", "common"), ("dizziness", "common"), 
        ("chest_pain", "chronic"), ("itchy_skin", "common"), ("red_rash", "common"), 
        ("dry_skin", "lifestyle"), ("skin_blisters", "common"), ("severe_headache", "chronic"), 
        ("nausea", "common"), ("sensitivity_to_light", "chronic"), ("sensitivity_to_sound", "chronic"), 
        ("aura", "rare"), ("diarrhea", "common"), ("bloating", "lifestyle"), ("abdominal_pain", "common"), 
        ("salty_skin", "genetic"), ("poor_growth", "genetic"), ("muscle_weakness", "chronic"), 
        ("slurred_speech", "rare"), ("muscle_cramps", "common"), ("difficulty_swallowing", "rare"), 
        ("involuntary_movements", "rare"), ("cognitive_decline", "rare"), ("balance_issues", "rare"), 
        ("depression", "lifestyle"), ("joint_pain", "chronic"), ("butterfly_rash", "rare"), 
        ("hair_loss", "lifestyle"), ("heartburn", "lifestyle"), ("acid_reflux", "lifestyle"), 
        ("joint_stiffness", "chronic"), ("swollen_joints", "chronic"), ("weight_gain", "lifestyle"), 
        ("cold_intolerance", "chronic"), ("pale_skin", "common"), ("weakness", "common"), 
        ("cold_hands", "lifestyle")
    ]

    for name, cat in symptoms_list:
        try:
            db.execute_query("INSERT INTO symptoms (name, category) VALUES (%s, %s)", (name, cat))
        except Exception:
            pass # Ignore duplicates if re-seeding

    print("[CuraAI Seed] Database successfully seeded with demo assets.")

if __name__ == "__main__":
    seed_database()
