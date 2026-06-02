# app.py - CuraAI Backend Web Server
# Flask API for full-stack clinical decision support and healthcare management system.

import os
import jwt
import bcrypt
import datetime
import functools
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Import local services
from database import db
from seed import seed_database
import ml_model
import ocr_service
import notification_service
import chatbot_engine

app = Flask(__name__)
# Configure CORS - covers all /api/* routes
CORS(app, resources={r"/api/*": {
    "origins": "*",
    "allow_headers": ["Content-Type", "Authorization", "Accept"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}})

# Ensure CORS headers appear on EVERY response, including 4xx/5xx errors
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin']  = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    return response

@app.errorhandler(500)
def internal_error(e):
    response = jsonify({'message': f'Internal server error: {str(e)}'})
    response.status_code = 500
    return response

@app.errorhandler(404)
def not_found(e):
    return jsonify({'message': 'Endpoint not found'}), 404

# Configurations
JWT_SECRET = os.environ.get("JWT_SECRET", "curaai_jwt_secret_key_987654321")
UPLOAD_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploads'))
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Auto seed database on startup
seed_database()

# ----------------- JWT HELPER FUNCTIONS -----------------
def generate_token(user_id, role):
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def token_required(f):
    @functools.wraps(f)
    def decorator(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(None, *args, **kwargs)

        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
        
        if not token:
            return jsonify({'message': 'Authorization token is missing!'}), 401
        
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            current_user = db.fetch_one(
                "SELECT id, name, mobile_number, role FROM users WHERE id = %s",
                (data['user_id'],)
            )
            if not current_user:
                return jsonify({'message': 'User account not found!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Session expired. Please login again.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid authentication token.'}), 401
        except Exception as e:
            print(f'[Auth] Token validation error: {e}')
            return jsonify({'message': 'Authentication error occurred.'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorator

# ----------------- AUTH ENDPOINTS -----------------
@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json(force=True, silent=True) or {}
    name    = (data.get('name') or '').strip()
    mobile  = (data.get('mobile_number') or '').strip().replace(' ', '').replace('-', '')
    password = (data.get('password') or '').strip()
    role    = data.get('role', 'patient').strip()

    print(f'[Register] Attempt: name={name!r}, mobile={mobile!r}, role={role!r}')

    # ── Field presence check
    if not name:
        return jsonify({'message': 'Full name is required.'}), 400
    if not mobile:
        return jsonify({'message': 'Mobile number is required.'}), 400
    if not password:
        return jsonify({'message': 'Password is required.'}), 400

    # ── Mobile validation: exactly 10 digits
    if not re.fullmatch(r'[6-9]\d{9}', mobile):
        return jsonify({'message': 'Enter a valid 10-digit Indian mobile number (starting with 6-9).'}), 400

    # ── Password validation: min 6 characters
    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters long.'}), 400

    # ── Role validation
    if role not in ('patient', 'doctor', 'admin'):
        role = 'patient'

    try:
        # ── Duplicate check
        exists = db.fetch_one("SELECT id FROM users WHERE mobile_number = %s", (mobile,))
        if exists:
            return jsonify({'message': 'This mobile number is already registered. Please login instead.'}), 400

        # ── Hash password
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # ── Insert user
        user_id = db.execute_query(
            "INSERT INTO users (name, mobile_number, password_hash, role) VALUES (%s, %s, %s, %s)",
            (name, mobile, pw_hash, role)
        )
        print(f'[Register] User created: id={user_id}, role={role}')

        # ── Initialize role-specific record
        if role == 'patient':
            db.execute_query(
                """INSERT INTO patients (user_id, name, age, weight, height, allergies, medications, emergency_contact)
                   VALUES (%s, %s, 25, 65.0, 165.0, '', '', '')""",
                (user_id, name)
            )
        elif role == 'doctor':
            db.execute_query(
                """INSERT INTO doctors (user_id, name, specialization, experience, availability, consultation_fees, ratings)
                   VALUES (%s, %s, 'General Physician', 1, 'Mon-Fri 09:00 - 17:00', 500.0, 5.0)""",
                (user_id, name)
            )

        token = generate_token(user_id, role)
        print(f'[Register] Token generated for user_id={user_id}')
        return jsonify({
            'message': f'Welcome to CuraAI, {name}! Your account has been created.',
            'token': token,
            'user': {'id': user_id, 'name': name, 'role': role, 'mobile_number': mobile}
        }), 201

    except Exception as e:
        print(f'[Register] ERROR: {e}')
        return jsonify({'message': f'Registration failed: {str(e)}'}), 500

@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json(force=True, silent=True) or {}
    mobile   = (data.get('mobile_number') or '').strip().replace(' ', '').replace('-', '')
    password = (data.get('password') or '').strip()

    print(f'[Login] Attempt: mobile={mobile!r}')

    if not mobile or not password:
        return jsonify({'message': 'Mobile number and password are required.'}), 400

    user = db.fetch_one("SELECT * FROM users WHERE mobile_number = %s", (mobile,))
    if not user:
        print(f'[Login] No user found for mobile={mobile!r}')
        return jsonify({'message': 'No account found with this mobile number.'}), 401

    try:
        pwd_match = bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8'))
    except Exception as e:
        print(f'[Login] bcrypt error: {e}')
        return jsonify({'message': 'Authentication error. Please try again.'}), 500

    if pwd_match:
        token = generate_token(user['id'], user['role'])
        print(f'[Login] Success: user_id={user["id"]}, role={user["role"]}')
        return jsonify({
            'message': 'Login successful!',
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'role': user['role'],
                'mobile_number': user['mobile_number']
            }
        }), 200
    else:
        print(f'[Login] Wrong password for mobile={mobile!r}')
        return jsonify({'message': 'Incorrect password. Please try again.'}), 401

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json
    mobile = data.get('mobile_number')
    
    if not mobile:
        return jsonify({'message': 'Mobile number required!'}), 400

    user = db.fetch_one("SELECT id, name FROM users WHERE mobile_number = %s", (mobile,))
    if not user:
        return jsonify({'message': 'No account associated with this mobile number!'}), 404

    # Generate a dummy 6-digit OTP
    otp = "184029" # Hardcoded for predictability or dynamic
    
    # Send via notification system
    msg = f"CuraAI: Use OTP {otp} to reset your password. Do not share this with anyone."
    notification_service.send_sms_notification(msg, "Forgot Password OTP Request", user['id'])

    return jsonify({'message': 'OTP sent successfully via SMS to registered mobile number.', 'otp_sent': True}), 200

@app.route('/api/auth/verify-otp', methods=['POST'])
def verify_otp():
    data = request.json
    mobile = data.get('mobile_number')
    otp = data.get('otp')
    new_password = data.get('new_password')

    if not mobile or not otp or not new_password:
        return jsonify({'message': 'Missing mobile number, OTP, or new password!'}), 400

    # Hardcoded OTP check for demonstration
    if otp != "184029":
        return jsonify({'message': 'Invalid or expired OTP!'}), 400

    # Update password
    salt = bcrypt.gensalt()
    pw_hash = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

    try:
        db.execute_query("UPDATE users SET password_hash = %s WHERE mobile_number = %s", (pw_hash, mobile))
        return jsonify({'message': 'Password has been successfully reset! You can now log in.'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to update password: {str(e)}'}), 500

# ----------------- PATIENT ENDPOINTS -----------------
@app.route('/api/patient/dashboard', methods=['GET'])
@token_required
def get_patient_dashboard(current_user):
    if current_user['role'] != 'patient':
        return jsonify({'message': 'Unauthorized role!'}), 403

    # Fetch patient profile
    patient = db.fetch_one("SELECT * FROM patients WHERE user_id = %s", (current_user['id'],))
    if not patient:
        return jsonify({'message': 'Patient profile not found!'}), 404

    # Fetch latest health record
    latest_record = db.fetch_one(
        "SELECT * FROM health_records WHERE patient_id = %s ORDER BY recorded_date DESC LIMIT 1",
        (patient['id'],)
    )

    # Fetch previous reports
    reports = db.fetch_all(
        "SELECT id, report_type, file_name, file_path, ai_summary, severity_level, uploaded_at FROM reports WHERE patient_id = %s ORDER BY uploaded_at DESC LIMIT 5",
        (patient['id'],)
    )

    # Fetch previous prescriptions
    prescriptions = db.fetch_all(
        "SELECT id, doctor_name, medicine_names, diagnosis, uploaded_at FROM prescriptions WHERE patient_id = %s ORDER BY uploaded_at DESC LIMIT 5",
        (patient['id'],)
    )

    # Fetch disease prediction history
    predictions = db.fetch_all(
        "SELECT id, symptoms_entered, predicted_disease, confidence_percentage, severity_level, recorded_at FROM disease_predictions WHERE patient_id = %s ORDER BY recorded_at DESC LIMIT 5",
        (patient['id'],)
    )

    # Calculate overall Health Score (Mock metric based on BMI, BP, sugar, cholesterol, and habits)
    health_score = 85
    reasons = []
    
    if latest_record:
        # BMI checks
        bmi = latest_record['bmi']
        if bmi and (bmi < 18.5 or bmi > 25.0):
            health_score -= 8
            reasons.append("BMI is outside the optimal 18.5 - 25.0 range")
        
        # BP checks
        sys = latest_record['blood_pressure_sys']
        dia = latest_record['blood_pressure_dia']
        if sys and dia:
            if sys > 130 or dia > 85:
                health_score -= 10
                reasons.append("Blood Pressure is elevated")
        
        # Sugar checks
        sugar = latest_record['sugar_level']
        if sugar:
            if sugar > 125:
                health_score -= 12
                reasons.append("Fasting blood glucose is high (Hyperglycemia risk)")
            elif sugar < 70:
                health_score -= 5
                reasons.append("Blood glucose is low (Hypoglycemia risk)")
        
        # Water checks
        water = latest_record['water_intake']
        if water and water < 2000:
            health_score -= 5
            reasons.append("Daily water intake is below recommended 2L")

    # Limit floor of health score to 30
    health_score = max(30, health_score)

    dashboard_data = {
        'profile': {
            'patient_id': patient['id'],
            'name': patient['name'],
            'age': patient['age'],
            'gender': patient['gender'],
            'blood_group': patient['blood_group'],
            'weight': patient['weight'],
            'height': patient['height'],
            'medical_history': patient['medical_history']
        },
        'latest_vitals': latest_record,
        'recent_reports': reports,
        'recent_prescriptions': prescriptions,
        'disease_history': predictions,
        'health_analytics': {
            'health_score': health_score,
            'health_score_reasons': reasons if reasons else ["Vitals within healthy physiological limits! Keep up the good work."]
        }
    }

    return jsonify(dashboard_data), 200

@app.route('/api/patient/health-records', methods=['GET', 'POST'])
@token_required
def manage_health_records(current_user):
    # Retrieve patient reference
    patient = db.fetch_one("SELECT id FROM patients WHERE user_id = %s", (current_user['id'],))
    if not patient:
        return jsonify({'message': 'Patient record not found'}), 404
        
    if request.method == 'POST':
        data = request.json
        sys = data.get('blood_pressure_sys')
        dia = data.get('blood_pressure_dia')
        sugar = data.get('sugar_level')
        chol = data.get('cholesterol')
        weight = data.get('weight')
        height = data.get('height')
        hr = data.get('heart_rate')
        o2 = data.get('oxygen_level')
        temp = data.get('temperature')
        water = data.get('water_intake')
        date_str = data.get('recorded_date') # Format: YYYY-MM-DD

        if not date_str:
            date_str = datetime.date.today().strftime('%Y-%m-%d')

        # Compute BMI if weight and height exist
        bmi = None
        if weight and height:
            height_m = float(height) / 100
            bmi = round(float(weight) / (height_m * height_m), 2)

        try:
            # Check if record for date already exists
            existing = db.fetch_one(
                "SELECT id FROM health_records WHERE patient_id = %s AND recorded_date = %s",
                (patient['id'], date_str)
            )

            if existing:
                query = """
                UPDATE health_records SET
                    blood_pressure_sys = %s, blood_pressure_dia = %s, sugar_level = %s,
                    cholesterol = %s, weight = %s, height = %s, bmi = %s,
                    heart_rate = %s, oxygen_level = %s, temperature = %s, water_intake = %s
                WHERE id = %s
                """
                db.execute_query(query, (sys, dia, sugar, chol, weight, height, bmi, hr, o2, temp, water, existing['id']))
                rec_id = existing['id']
            else:
                query = """
                INSERT INTO health_records 
                    (patient_id, blood_pressure_sys, blood_pressure_dia, sugar_level, cholesterol, weight, height, bmi, heart_rate, oxygen_level, temperature, water_intake, recorded_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                rec_id = db.execute_query(query, (patient['id'], sys, dia, sugar, chol, weight, height, bmi, hr, o2, temp, water, date_str))

            # Also update base patient weights/heights
            if weight or height:
                db.execute_query(
                    "UPDATE patients SET weight = COALESCE(%s, weight), height = COALESCE(%s, height) WHERE id = %s",
                    (weight, height, patient['id'])
                )

            # Trigger warnings on severe vitals
            warning_messages = []
            if sys and sys >= 160:
                warning_messages.append(f"CRITICAL HYPERTENSION WARNING: Systolic Blood Pressure recorded is dangerously high ({sys} mmHg).")
            if sugar and sugar >= 250:
                warning_messages.append(f"CRITICAL HYPERGLYCEMIA WARNING: Blood Sugar level recorded is dangerously high ({sugar} mg/dL).")
            if o2 and o2 <= 92:
                warning_messages.append(f"CRITICAL SPO2 WARNING: Oxygen level recorded is dangerously low ({o2}%).")

            if warning_messages:
                full_warning = f"Alert for patient {current_user['name']}: " + " | ".join(warning_messages)
                notification_service.send_sms_notification(full_warning, "Emergency Health Vitals Encountered", current_user['id'])

            return jsonify({'message': 'Health record successfully logged!', 'record_id': rec_id, 'warnings': warning_messages}), 200

        except Exception as e:
            return jsonify({'message': f'Failed to write health record: {str(e)}'}), 500

    else:
        # GET - Fetch all health records for charts
        records = db.fetch_all(
            "SELECT * FROM health_records WHERE patient_id = %s ORDER BY recorded_date ASC",
            (patient['id'],)
        )
        return jsonify(records), 200

# --- PATIENT PROFILE UPDATE ---
@app.route('/api/patient/profile', methods=['GET', 'PUT'])
@token_required
def patient_profile(current_user):
    patient = db.fetch_one("SELECT * FROM patients WHERE user_id = %s", (current_user['id'],))
    if not patient:
        return jsonify({'message': 'Patient profile not found'}), 404
    if request.method == 'GET':
        return jsonify(patient), 200
    data = request.json
    age = data.get('age', patient['age'])
    weight = data.get('weight', patient['weight'])
    height = data.get('height', patient['height'])
    gender = data.get('gender', patient.get('gender', ''))
    blood_group = data.get('blood_group', patient.get('blood_group', ''))
    medical_hist = data.get('medical_history', patient.get('medical_history', ''))
    allergies = data.get('allergies', patient.get('allergies', ''))
    medications = data.get('medications', patient.get('medications', ''))
    emergency_contact = data.get('emergency_contact', patient.get('emergency_contact', ''))
    bmi = None
    if weight and height:
        hm = float(height) / 100
        bmi = round(float(weight) / (hm * hm), 2)
    try:
        db.execute_query(
            "UPDATE patients SET age=%s, weight=%s, height=%s, gender=%s, blood_group=%s, medical_history=%s, allergies=%s, medications=%s, emergency_contact=%s WHERE user_id=%s",
            (age, weight, height, gender, blood_group, medical_hist, allergies, medications, emergency_contact, current_user['id'])
        )
        return jsonify({'message': 'Profile updated successfully!', 'bmi': bmi}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to update profile: {str(e)}'}), 500


# Helper to validate filenames
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------- OCR AND REPORT UPLOAD -----------------
@app.route('/api/patient/upload-report', methods=['POST'])
@token_required
def upload_report(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file segment found in request'}), 400
        
    file = request.files['file']
    report_type = request.form.get('report_type', 'other') # blood_test, x-ray, scan, other
    is_prescription = request.form.get('is_prescription', 'false').lower() == 'true'

    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(f"{current_user['id']}_{int(datetime.datetime.now().timestamp())}_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Fetch patient profile
        patient = db.fetch_one("SELECT id FROM patients WHERE user_id = %s", (current_user['id'],))
        if not patient:
            return jsonify({'message': 'Patient profile missing'}), 404

        # Run OCR service analysis
        ocr_result = ocr_service.process_file_ocr(file_path)
        
        # Save to SQL DB
        if is_prescription:
            # Save to prescriptions table
            query = """
            INSERT INTO prescriptions (patient_id, medicine_names, dosage_instructions, diagnosis, ocr_extracted_text, file_path)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            rec_id = db.execute_query(query, (
                patient['id'], 
                ocr_result['medicines'], 
                ocr_result['dosage_instructions'], 
                ocr_result['diagnosis'], 
                ocr_result['text'], 
                filename
            ))
            
            # Send Notification
            msg = f"CuraAI: A new doctor prescription was successfully uploaded and processed. Extracted medicines: {ocr_result['medicines']}."
            notification_service.send_sms_notification(msg, "New Prescription Processed", current_user['id'])
            
            return jsonify({
                'message': 'Prescription successfully uploaded & processed!',
                'prescription_id': rec_id,
                'extracted_data': ocr_result
            }), 201
        
        else:
            # Save to reports table
            query = """
            INSERT INTO reports (patient_id, report_type, file_name, file_path, ocr_text, ai_summary, severity_level)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            rec_id = db.execute_query(query, (
                patient['id'], 
                report_type, 
                file.filename, 
                filename, 
                ocr_result['text'], 
                ocr_result['summary'], 
                ocr_result['severity']
            ))

            # Send SMS warning if severity level is critical/high
            if ocr_result['severity'] in ['high', 'critical']:
                alert_msg = f"CuraAI Critical Alert: A newly uploaded report indicates a {ocr_result['severity'].upper()} health condition. Diagnosis findings: {ocr_result['diagnosis']}. Action advised: {ocr_result['summary'].split('RECOMMENDATION:')[-1]}"
                notification_service.send_sms_notification(alert_msg, f"Severe Report Uploaded ({ocr_result['severity'].upper()})", current_user['id'])
            else:
                info_msg = f"CuraAI: Medical report ({file.filename}) successfully uploaded. Severity level categorized as {ocr_result['severity'].upper()}."
                notification_service.send_sms_notification(info_msg, "Report Uploaded", current_user['id'])

            return jsonify({
                'message': 'Medical report successfully uploaded & summarized by AI!',
                'report_id': rec_id,
                'summary': ocr_result['summary'],
                'severity_level': ocr_result['severity'],
                'extracted_diagnosis': ocr_result['diagnosis']
            }), 201

    return jsonify({'message': 'File extension not supported'}), 400

@app.route('/api/uploads/<filename>')
def get_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ----------------- AI SYMPTOM ANALYSIS ENDPOINTS -----------------
@app.route('/api/symptom-analysis', methods=['POST'])
@token_required
def analyze_symptoms(current_user):
    data = request.json
    symptoms = data.get('symptoms', []) # Array of symptom strings
    
    # Get patient profile
    patient = db.fetch_one("SELECT id FROM patients WHERE user_id = %s", (current_user['id'],))
    if not patient:
        return jsonify({'message': 'Patient profile missing'}), 404

    # Run Prediction
    predictions = ml_model.ai_engine.predict_disease(symptoms)
    
    # Log prediction into DB
    top_pred = predictions[0]
    symptoms_str = ", ".join(symptoms)
    precautions_str = "; ".join(top_pred['precautions'])

    try:
        query = """
        INSERT INTO disease_predictions (patient_id, symptoms_entered, predicted_disease, confidence_percentage, severity_level, is_rare, precautions_recommended, next_medical_actions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        pred_id = db.execute_query(query, (
            patient['id'],
            symptoms_str,
            top_pred['disease'],
            top_pred['confidence'],
            top_pred['severity'],
            1 if top_pred['is_rare'] else 0,
            precautions_str,
            top_pred['next_actions']
        ))
        
        # Trigger SMS warning if predicted disease is critical or rare
        if top_pred['severity'] in ['high', 'critical'] or top_pred['is_rare']:
            alert_msg = f"CuraAI ALERT: AI predicted possible {top_pred['disease']} ({top_pred['confidence']}% confidence, Category: {top_pred['category']}). Severity is {top_pred['severity'].upper()}. Advice: {top_pred['next_actions']}"
            notification_service.send_sms_notification(alert_msg, "AI Detected Severe/Rare Disease", current_user['id'])

        return jsonify({
            'prediction_id': pred_id,
            'predictions': predictions
        }), 200

    except Exception as e:
        return jsonify({'message': f'Failed to write prediction logs: {str(e)}'}), 500

# --- CUSTOM NLP SYMPTOM ANALYSIS ---
@app.route('/api/symptom-analysis/custom', methods=['POST'])
@token_required
def analyze_custom_symptoms(current_user):
    data = request.json
    raw_text = data.get('symptom_text', '')
    severity = data.get('severity', 'moderate')
    duration_days = int(data.get('duration_days', 0))
    tag_symptoms = data.get('tag_symptoms', [])
    patient = db.fetch_one("SELECT id FROM patients WHERE user_id = %s", (current_user['id'],))
    if not patient:
        return jsonify({'message': 'Patient profile missing'}), 404
    nlp_symptoms = ml_model.parse_natural_language_symptoms(raw_text) if raw_text else []
    all_symptoms = list(set(nlp_symptoms + tag_symptoms))
    if not all_symptoms:
        return jsonify({'message': 'Could not extract recognisable symptoms. Try adding keywords like "headache", "chest pain".'}), 400
    predictions = ml_model.ai_engine.predict_disease(all_symptoms)
    top_pred = predictions[0]
    urgency = ml_model.classify_urgency(all_symptoms, raw_text, duration_days)
    doc_rec = ml_model.recommend_specialization(disease=top_pred['disease'], symptoms=all_symptoms)
    recommended_doctors = db.fetch_all("SELECT * FROM doctors WHERE specialization=%s ORDER BY ratings DESC LIMIT 3", (doc_rec['specialization'],))
    if not recommended_doctors:
        recommended_doctors = db.fetch_all("SELECT * FROM doctors ORDER BY ratings DESC LIMIT 3")
    patient_full = db.fetch_one("SELECT * FROM patients WHERE user_id=%s", (current_user['id'],))
    profile = {'age': patient_full['age'], 'weight': patient_full['weight'], 'medical_history': patient_full.get('medical_history', ''), 'allergies': patient_full.get('allergies', '')} if patient_full else None
    drugs = ml_model.ai_engine.get_drug_recommendations(top_pred['disease'], profile)
    habits = ml_model.ai_engine.get_health_recommendations(top_pred['disease'], patient_full['age'] if patient_full else 30, patient_full['weight'] if patient_full else 70, None, patient_full.get('medical_history', '') if patient_full else '')
    symptoms_str = raw_text[:500] if raw_text else ', '.join(all_symptoms)
    precautions_str = '; '.join(top_pred['precautions'])
    try:
        db.execute_query(
            "INSERT INTO disease_predictions (patient_id, symptoms_entered, predicted_disease, confidence_percentage, severity_level, is_rare, precautions_recommended, next_medical_actions) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (patient['id'], symptoms_str, top_pred['disease'], top_pred['confidence'], top_pred['severity'], 1 if top_pred['is_rare'] else 0, precautions_str, top_pred['next_actions'])
        )
    except Exception as db_err:
        print(f'[App] Failed to log custom prediction: {db_err}')
    if urgency['urgency_score'] >= 3:
        alert = f"CuraAI ALERT: {current_user['name']} reported {severity.upper()} symptoms. AI urgency: {urgency['level']}. Prediction: {top_pred['disease']} ({top_pred['confidence']}%). {urgency['advice']}"
        notification_service.send_sms_notification(alert, f"Custom Symptom Urgency: {urgency['level']}", current_user['id'])
    return jsonify({'parsed_symptoms': all_symptoms, 'predictions': predictions, 'urgency': urgency, 'recommended_specialization': doc_rec, 'recommended_doctors': recommended_doctors, 'drugs': drugs, 'habits': habits}), 200

# ----------------- AI DRUG RECOMMENDATION ENDPOINTS -----------------
@app.route('/api/drug-recommendations', methods=['POST'])
@token_required
def get_drug_recommendations(current_user):
    data = request.json
    disease = data.get('disease')
    prediction_id = data.get('prediction_id')

    if not disease:
        return jsonify({'message': 'Disease parameter required'}), 400

    patient = db.fetch_one("SELECT * FROM patients WHERE user_id = %s", (current_user['id'],))
    
    # Prepare patient profile for ML engine dosage/allergy check
    profile = None
    if patient:
        profile = {
            'age': patient['age'],
            'weight': patient['weight'],
            'medical_history': patient['medical_history'],
            'allergies': patient['medical_history'] # Allergies are stored in history field
        }

    # Fetch drug suggestions
    recs = ml_model.ai_engine.get_drug_recommendations(disease, profile)

    # Save recommendations to database
    try:
        meds_json = str(recs['medicines']) # Standard text list representation
        query = """
        INSERT INTO drug_recommendations (prediction_id, patient_id, recommended_medicines, dosage, usage_timing, side_effects, food_restrictions, precautions, alternatives, generic_medicines, emergency_warnings)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db.execute_query(query, (
            prediction_id,
            patient['id'] if patient else 1,
            meds_json,
            recs['medicines'][0]['dosage'] if recs['medicines'] else '',
            recs['medicines'][0]['timing'] if recs['medicines'] else '',
            recs['side_effects'],
            recs['food_restrictions'],
            recs['precautions'],
            recs['alternatives'],
            recs['generic_medicines'],
            recs['emergency_warnings']
        ))
    except Exception as db_err:
        print(f"[App Engine] Failed to save drug recommendations to DB: {db_err}")

    return jsonify(recs), 200

# ----------------- HEALTH HABITS RECOMMENDATION ENDPOINTS -----------------
@app.route('/api/health-recommendations', methods=['POST'])
@token_required
def get_lifestyle_recommendations(current_user):
    data = request.json
    disease = data.get('disease', 'General')
    
    patient = db.fetch_one("SELECT * FROM patients WHERE user_id = %s", (current_user['id'],))
    if not patient:
        return jsonify({'message': 'Patient profile missing'}), 404

    # Calculate BMI
    bmi = None
    if patient['weight'] and patient['height']:
        hm = float(patient['height']) / 100
        bmi = round(float(patient['weight']) / (hm * hm), 2)

    # Fetch custom habit suggestions
    habits = ml_model.ai_engine.get_health_recommendations(
        disease, 
        patient['age'], 
        patient['weight'], 
        bmi, 
        patient['medical_history']
    )
    
    return jsonify(habits), 200

# --- AI DOCTOR RECOMMENDATION ---
@app.route('/api/doctors/recommend', methods=['POST'])
@token_required
def recommend_doctors(current_user):
    data = request.json
    disease = data.get('disease', '')
    symptoms = data.get('symptoms', [])
    rec = ml_model.recommend_specialization(disease=disease, symptoms=symptoms)
    matched = db.fetch_all("SELECT * FROM doctors WHERE specialization=%s ORDER BY ratings DESC", (rec['specialization'],))
    if not matched:
        matched = db.fetch_all("SELECT * FROM doctors ORDER BY ratings DESC LIMIT 3")
    return jsonify({'recommended_specialization': rec['specialization'], 'reason': rec['reason'], 'doctors': matched}), 200

# ----------------- DOCTOR CONNECT SYSTEM ENDPOINTS -----------------
@app.route('/api/doctors', methods=['GET'])
@token_required
def list_doctors(current_user):
    doctors = db.fetch_all("SELECT * FROM doctors ORDER BY ratings DESC")
    return jsonify(doctors), 200

@app.route('/api/appointments', methods=['GET', 'POST'])
@token_required
def manage_appointments(current_user):
    if request.method == 'POST':
        data = request.json
        doc_id = data.get('doctor_id')
        date_str = data.get('appointment_date')
        time_str = data.get('appointment_time')
        consult_type = data.get('consultation_type', 'video') # video, in-person
        
        if not doc_id or not date_str or not time_str:
            return jsonify({'message': 'Missing doctor, date, or time slot!'}), 400

        # Retrieve patient
        patient = db.fetch_one("SELECT id, name FROM patients WHERE user_id = %s", (current_user['id'],))
        if not patient:
            return jsonify({'message': 'Patient profile missing'}), 404

        # Retrieve doctor
        doctor = db.fetch_one("SELECT name, consultation_fees FROM doctors WHERE id = %s", (doc_id,))
        if not doctor:
            return jsonify({'message': 'Doctor not found'}), 404

        try:
            # Create appointment
            query = """
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, consultation_type, fees, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'confirmed')
            """
            app_id = db.execute_query(query, (patient['id'], doc_id, date_str, time_str, consult_type, doctor['consultation_fees']))

            # Dispatch notification
            msg = f"CuraAI Booking: Appointment confirmed with {doctor['name']} on {date_str} at {time_str}. Consultation type: {consult_type.upper()}."
            notification_service.send_sms_notification(msg, "Doctor Appointment Booked", current_user['id'])

            return jsonify({'message': 'Appointment booked successfully!', 'appointment_id': app_id}), 201

        except Exception as e:
            return jsonify({'message': f'Database error: {str(e)}'}), 500
    
    else:
        # GET appointments
        if current_user['role'] == 'patient':
            patient = db.fetch_one("SELECT id FROM patients WHERE user_id = %s", (current_user['id'],))
            if not patient:
                return jsonify([])
            appointments = db.fetch_all(
                """SELECT a.*, d.name as doctor_name, d.specialization as doctor_specialization 
                   FROM appointments a JOIN doctors d ON a.doctor_id = d.id 
                   WHERE a.patient_id = %s ORDER BY a.appointment_date DESC""", 
                (patient['id'],)
            )
        elif current_user['role'] == 'doctor':
            doctor = db.fetch_one("SELECT id FROM doctors WHERE user_id = %s", (current_user['id'],))
            if not doctor:
                return jsonify([])
            appointments = db.fetch_all(
                """SELECT a.*, p.name as patient_name, p.age as patient_age, p.gender as patient_gender 
                   FROM appointments a JOIN patients p ON a.patient_id = p.id 
                   WHERE a.doctor_id = %s ORDER BY a.appointment_date DESC""", 
                (doctor['id'],)
            )
        else:
            # Admin gets all
            appointments = db.fetch_all(
                """SELECT a.*, p.name as patient_name, d.name as doctor_name, d.specialization 
                   FROM appointments a JOIN patients p ON a.patient_id = p.id 
                   JOIN doctors d ON a.doctor_id = d.id ORDER BY a.appointment_date DESC"""
            )
        return jsonify(appointments), 200

# ----------------- MESSAGING SYSTEM ENDPOINTS -----------------
@app.route('/api/messages', methods=['GET', 'POST'])
@token_required
def manage_messages(current_user):
    if request.method == 'POST':
        data = request.json
        receiver_id = data.get('receiver_id')
        message = data.get('message')

        if not receiver_id or not message:
            return jsonify({'message': 'Missing receiver or message body!'}), 400

        try:
            query = "INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s, %s, %s)"
            msg_id = db.execute_query(query, (current_user['id'], receiver_id, message))
            receiver_doc = db.fetch_one("SELECT name FROM doctors WHERE user_id=%s", (receiver_id,))
            doc_name = receiver_doc['name'] if receiver_doc else 'the doctor'
            sms_text = f"New Patient Message Received for {doc_name}.\nFrom: {current_user['name']}\nMessage: {message[:100]}"
            notification_service.send_sms_notification(sms_text, "Patient Message Alert", current_user['id'])
            return jsonify({'message': 'Message sent!', 'message_id': msg_id}), 201
        except Exception as e:
            return jsonify({'message': f'Failed to send message: {str(e)}'}), 500
    
    else:
        # GET messages between current user and counterparty
        counterparty_id = request.args.get('counterparty_id')
        if not counterparty_id:
            return jsonify({'message': 'Missing counterparty_id query parameter'}), 400

        query = """
        SELECT * FROM messages 
        WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
        ORDER BY sent_at ASC
        """
        messages = db.fetch_all(query, (current_user['id'], counterparty_id, counterparty_id, current_user['id']))
        return jsonify(messages), 200

# ----------------- EMERGENCY ALERT SYSTEM -----------------
@app.route('/api/emergency-alert', methods=['POST'])
@token_required
def trigger_emergency_alert(current_user):
    data = request.json
    location = data.get('location', 'Location GPS Coordinates Unavailable')
    patient_info = db.fetch_one("SELECT age, blood_group, medical_history FROM patients WHERE user_id = %s", (current_user['id'],))
    
    medical_summary = "None"
    if patient_info:
        medical_summary = f"Age: {patient_info['age']}, Blood Group: {patient_info['blood_group']}, History: {patient_info['medical_history']}"

    # Critical SOS message sent to 7795273421 and 7019113622
    sos_message = f"CuraAI CRITICAL SOS: Patient {current_user['name']} has triggered an Emergency Medical Alert. Location: {location}. Vitals Info: {medical_summary}. Ambulance dispatch suggested."
    
    success = notification_service.send_sms_notification(sos_message, "SOS Emergency Triggered", current_user['id'])
    
    if success:
        return jsonify({'message': 'Emergency alerts dispatched successfully to rapid-response teams.'}), 200
    else:
        return jsonify({'message': 'Emergency alerts logged, but SMS dispatch failed.'}), 500

# ----------------- MEDICINE REMINDERS -----------------
@app.route('/api/reminders', methods=['GET', 'POST', 'OPTIONS'])
@token_required
def reminders(current_user):
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    user_id = current_user['id']

    if request.method == 'GET':
        try:
            rows = db.fetch_all(
                "SELECT * FROM medicine_reminders WHERE user_id = %s ORDER BY reminder_time ASC",
                (user_id,)
            )
            return jsonify({'reminders': rows}), 200
        except Exception as e:
            print(f'[Reminders GET] ERROR: {e}')
            return jsonify({'reminders': []}), 200

    if request.method == 'POST':
        data = request.get_json(force=True, silent=True) or {}
        medicine = (data.get('medicine_name') or '').strip()
        time_str  = (data.get('reminder_time') or '').strip()
        dosage    = (data.get('dosage') or '').strip()
        frequency = data.get('frequency', 'daily')
        notes     = data.get('notes', '')

        if not medicine or not time_str:
            return jsonify({'message': 'Medicine name and reminder time are required.'}), 400

        try:
            rid = db.execute_query(
                "INSERT INTO medicine_reminders (user_id, medicine_name, dosage, reminder_time, frequency, notes) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, medicine, dosage, time_str, frequency, notes)
            )
            return jsonify({'message': f'Reminder set for {medicine} at {time_str}', 'id': rid}), 201
        except Exception as e:
            print(f'[Reminders POST] ERROR: {e}')
            return jsonify({'message': f'Failed to create reminder: {str(e)}'}), 500


@app.route('/api/reminders/<int:reminder_id>', methods=['PUT', 'DELETE', 'OPTIONS'])
@token_required
def reminder_detail(current_user, reminder_id):
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    user_id = current_user['id']

    if request.method == 'PUT':
        data = request.get_json(force=True, silent=True) or {}
        medicine  = (data.get('medicine_name') or '').strip()
        time_str  = (data.get('reminder_time') or '').strip()
        dosage    = data.get('dosage', '')
        frequency = data.get('frequency', 'daily')
        notes     = data.get('notes', '')
        is_active = 1 if data.get('is_active', True) else 0

        try:
            db.execute_query(
                "UPDATE medicine_reminders SET medicine_name=%s, dosage=%s, reminder_time=%s, frequency=%s, notes=%s, is_active=%s WHERE id=%s AND user_id=%s",
                (medicine, dosage, time_str, frequency, notes, is_active, reminder_id, user_id)
            )
            return jsonify({'message': 'Reminder updated successfully'}), 200
        except Exception as e:
            return jsonify({'message': f'Update failed: {str(e)}'}), 500

    if request.method == 'DELETE':
        try:
            db.execute_query(
                "DELETE FROM medicine_reminders WHERE id = %s AND user_id = %s",
                (reminder_id, user_id)
            )
            return jsonify({'message': 'Reminder deleted successfully'}), 200
        except Exception as e:
            return jsonify({'message': f'Delete failed: {str(e)}'}), 500


# Legacy POST route kept for backward compatibility
@app.route('/api/medicine-reminder', methods=['POST'])
@token_required
def set_medicine_reminder(current_user):
    data = request.get_json(force=True, silent=True) or {}
    medicine = data.get('medicine_name')
    time_str = data.get('reminder_time')
    if not medicine or not time_str:
        return jsonify({'message': 'Missing medicine name or reminder time'}), 400
    user_id = current_user['id']
    try:
        rid = db.execute_query(
            "INSERT INTO medicine_reminders (user_id, medicine_name, reminder_time) VALUES (%s, %s, %s)",
            (user_id, medicine, time_str)
        )
        return jsonify({'message': f'Reminder set for {medicine} at {time_str}!', 'id': rid}), 200
    except Exception as e:
        return jsonify({'message': f'Failed: {str(e)}'}), 500


# ----------------- ADMIN DASHBOARD ENDPOINTS -----------------
@app.route('/api/admin/dashboard', methods=['GET'])
@token_required
def get_admin_dashboard(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Unauthorized access!'}), 403

    # Total counters
    users_count = db.fetch_one("SELECT COUNT(*) as count FROM users")['count']
    patients_count = db.fetch_one("SELECT COUNT(*) as count FROM users WHERE role = 'patient'")['count']
    doctors_count = db.fetch_one("SELECT COUNT(*) as count FROM users WHERE role = 'doctor'")['count']
    reports_count = db.fetch_one("SELECT COUNT(*) as count FROM reports")['count']
    appointments_count = db.fetch_one("SELECT COUNT(*) as count FROM appointments")['count']
    predictions_count = db.fetch_one("SELECT COUNT(*) as count FROM disease_predictions")['count']

    # Disease analytics (top predicted diseases)
    disease_analytics = db.fetch_all(
        "SELECT predicted_disease as disease, COUNT(*) as count FROM disease_predictions GROUP BY predicted_disease ORDER BY count DESC LIMIT 5"
    )

    # User lists
    users_list = db.fetch_all("SELECT id, name, mobile_number, role, created_at FROM users ORDER BY id DESC")
    doctors_list = db.fetch_all("SELECT id, name, specialization, experience, ratings FROM doctors ORDER BY id DESC")
    appointments_list = db.fetch_all(
        """SELECT a.*, p.name as patient_name, d.name as doctor_name, d.specialization 
           FROM appointments a JOIN patients p ON a.patient_id = p.id 
           JOIN doctors d ON a.doctor_id = d.id ORDER BY a.id DESC LIMIT 10"""
    )
    
    # Notification logs
    notifications_list = db.fetch_all("SELECT id, mobile_number, message, trigger_reason, status, created_at FROM notifications ORDER BY id DESC LIMIT 20")

    # Simple system logs simulator
    logs = [
        {"timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "event": "Seeding database completed successfully."},
        {"timestamp": (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"), "event": "AI Diagnostic random forest engine initialized."},
        {"timestamp": (datetime.datetime.now() - datetime.timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), "event": "Authentication Server started listening on port 5000."}
    ]

    return jsonify({
        'stats': {
            'total_users': users_count,
            'patients': patients_count,
            'doctors': doctors_count,
            'reports': reports_count,
            'appointments': appointments_count,
            'ai_predictions': predictions_count
        },
        'disease_analytics': disease_analytics,
        'users': users_list,
        'doctors': doctors_list,
        'appointments': appointments_list,
        'notifications': notifications_list,
        'system_logs': logs
    }), 200

# ════════════════════════════════════════════════════════════
# CHATBOT ENDPOINTS
# ════════════════════════════════════════════════════════════

@app.route('/api/chat', methods=['POST', 'OPTIONS'])
@token_required
def chat_message(current_user):
    """Process a chatbot message and return AI response."""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    try:
        data = request.get_json(force=True, silent=True) or {}
        user_message = (data.get('message') or '').strip()
        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        user_id = current_user['id']
        print(f'[Chat] user_id={user_id}, msg={user_message[:60]!r}')

        chatbot_engine.save_chat_message(user_id, 'user', user_message)
        history = chatbot_engine.get_chat_history(user_id, limit=10)
        result  = chatbot_engine.process_message(user_id, user_message, history)

        chatbot_engine.save_chat_message(user_id, 'assistant', result['message'], {
            'type': result.get('type'),
            'data': {k: v for k, v in result.get('data', {}).items() if k != 'message'}
        })

        return jsonify({
            'response': result['message'],
            'type':  result.get('type', 'general'),
            'data':  result.get('data', {})
        }), 200

    except Exception as e:
        print(f'[Chat] ERROR: {e}')
        import traceback; traceback.print_exc()
        return jsonify({
            'response': f"I'm sorry, I encountered an issue processing your request. Please try again.\n\n⚕ _If the problem persists, please consult a doctor directly._",
            'type':  'error',
            'data':  {}
        }), 200   # Return 200 so frontend doesn't show fetch error


@app.route('/api/chat/history', methods=['GET', 'OPTIONS'])
@token_required
def get_chat_history(current_user):
    """Return chat history for the logged-in user."""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    try:
        limit   = int(request.args.get('limit', 50))
        history = chatbot_engine.get_chat_history(current_user['id'], limit=limit)
        return jsonify({'history': history, 'count': len(history)}), 200
    except Exception as e:
        print(f'[Chat History] ERROR: {e}')
        return jsonify({'history': [], 'count': 0}), 200


@app.route('/api/chat/history', methods=['DELETE', 'OPTIONS'])
@token_required
def clear_chat_history(current_user):
    """Clear chat history for the logged-in user."""
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200
    try:
        chatbot_engine.clear_chat_history(current_user['id'])
        return jsonify({'message': 'Chat history cleared successfully.'}), 200
    except Exception as e:
        print(f'[Chat Clear] ERROR: {e}')
        return jsonify({'message': 'Failed to clear history'}), 500


if __name__ == '__main__':
    print("[CuraAI Web Server] Booting backend server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
