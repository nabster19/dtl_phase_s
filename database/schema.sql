-- CuraAI MySQL Database Schema

CREATE DATABASE IF NOT EXISTS curaai;
USE curaai;

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    mobile_number VARCHAR(15) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('patient', 'doctor', 'admin') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Doctors Table
CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    specialization VARCHAR(100) NOT NULL,
    experience INT NOT NULL, -- in years
    availability VARCHAR(255) NOT NULL, -- e.g., "Mon-Fri 09:00 - 17:00"
    consultation_fees DECIMAL(10,2) NOT NULL,
    ratings DECIMAL(3,2) DEFAULT 5.0,
    profile_pic VARCHAR(255) DEFAULT 'default_doctor.png',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Patients Table
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    age INT,
    gender VARCHAR(20),
    blood_group VARCHAR(10),
    weight DECIMAL(5,2), -- in kg
    height DECIMAL(5,2), -- in cm
    address TEXT,
    medical_history TEXT, -- comma-separated list of chronic diseases or allergies
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. Health Records (Tracking BP, sugar, cholesterol, weight, height, BMI, heart rate, oxygen, temp, water intake)
CREATE TABLE IF NOT EXISTS health_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    blood_pressure_sys INT, -- Systolic BP
    blood_pressure_dia INT, -- Diastolic BP
    sugar_level INT, -- Sugar level in mg/dL
    cholesterol INT, -- Cholesterol in mg/dL
    weight DECIMAL(5,2), -- Weight in kg
    height DECIMAL(5,2), -- Height in cm
    bmi DECIMAL(4,2), -- Calculated BMI
    heart_rate INT, -- Heart rate in bpm
    oxygen_level INT, -- SpO2 percentage
    temperature DECIMAL(4,1), -- Temp in Celsius
    water_intake INT, -- Daily water intake in ml
    recorded_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    UNIQUE KEY unique_patient_date (patient_id, recorded_date)
);

-- 5. Symptoms Table
CREATE TABLE IF NOT EXISTS symptoms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category ENUM('common', 'chronic', 'rare', 'genetic', 'lifestyle') NOT NULL
);

-- 6. Disease Predictions Table
CREATE TABLE IF NOT EXISTS disease_predictions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    symptoms_entered TEXT NOT NULL, -- comma-separated or JSON list of symptoms
    predicted_disease VARCHAR(255) NOT NULL,
    confidence_percentage DECIMAL(5,2) NOT NULL,
    severity_level ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    is_rare BOOLEAN DEFAULT FALSE,
    precautions_recommended TEXT, -- JSON or separated list
    next_medical_actions TEXT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- 7. Drug Recommendations Table
CREATE TABLE IF NOT EXISTS drug_recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    prediction_id INT,
    patient_id INT NOT NULL,
    recommended_medicines TEXT NOT NULL, -- JSON list of medicines, dosage, timing
    dosage VARCHAR(255),
    usage_timing VARCHAR(255),
    side_effects TEXT,
    food_restrictions TEXT,
    precautions TEXT,
    alternatives TEXT, -- generic or alternative meds
    generic_medicines TEXT,
    emergency_warnings TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prediction_id) REFERENCES disease_predictions(id) ON DELETE SET NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- 8. Prescriptions Table (Uploaded & OCR processed)
CREATE TABLE IF NOT EXISTS prescriptions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NULL,
    doctor_name VARCHAR(255) DEFAULT 'Self Uploaded',
    medicine_names TEXT, -- extracted via OCR
    dosage_instructions TEXT, -- extracted via OCR
    diagnosis TEXT, -- extracted via OCR
    ocr_extracted_text TEXT,
    file_path VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE SET NULL
);

-- 9. Reports Table (Uploaded medical reports, X-rays, Scans)
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    report_type ENUM('blood_test', 'x-ray', 'scan', 'other') NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(255) NOT NULL,
    ocr_text TEXT,
    ai_summary TEXT,
    severity_level ENUM('low', 'medium', 'high', 'critical') DEFAULT 'low',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- 10. Appointments Table
CREATE TABLE IF NOT EXISTS appointments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time VARCHAR(20) NOT NULL, -- e.g., "10:00 AM"
    status ENUM('pending', 'confirmed', 'completed', 'cancelled') DEFAULT 'pending',
    consultation_type ENUM('video', 'in-person') DEFAULT 'video',
    fees DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
);

-- 11. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    mobile_number VARCHAR(15) NOT NULL,
    type VARCHAR(10) DEFAULT 'sms', -- 'sms' or 'email'
    message TEXT NOT NULL,
    status ENUM('sent', 'failed') DEFAULT 'sent',
    trigger_reason VARCHAR(255), -- e.g., "Severe disease detected", "Appointment booked"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 12. Messages Table (Patient-Doctor consultation chats)
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    message TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
);
