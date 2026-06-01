# CuraAI – AI-Powered Clinical Decision Support & Smart Healthcare Management System

CuraAI is a state-of-the-art full-stack clinical decision support and patient care platform. Designed for modern healthcare settings, it integrates digital medical record maintenance, AI-driven symptom diagnostics, OCR-powered report scanning, secure doctor-patient consulting pipelines, and automated Twilio alert gateways.

---

## 🌟 Key Features

1. **User Authentication System**
   * Multi-role support: **Patient**, **Doctor**, and **Admin**.
   * Secure JWT sessions with bcrypt password encryption.
   * OTP verification simulation for forgotten passwords.

2. **Electronic Health Records & Vitals Analytics**
   * Real-time logging of critical physiological metrics: BP, Sugar, Cholesterol, Weight, Height, Heart Rate, Oxygen, Temp, Water Intake.
   * Smart calculations (e.g. BMI index auto-computations).
   * Interactive trends visualization (Weekly curves, Monthly BP charts) using Chart.js.

3. **AI Symptom Analyzer**
   * Multi-symptom selector matched against a trained Random Forest model.
   * Returns disease classifications, probability percentages, severity categories, and precaution lists.

4. **AI Drug & Lifestyle Recommendations**
   * Offers customized dosages, alternative medications, food restrictions, and allergy checks.
   * Generates dynamic diet, exercise, and hydration lifestyle improvement cards.

5. **OCR Prescription & Report Scanner**
   * Upload image/PDF documents to scan findings.
   * Pytesseract OCR extraction with robust rule-based parsing regex fallback if Tesseract binaries are not in system PATH.
   * Identifies abnormalities and triggers alerts on high-severity logs.

6. **Doctor Connect Consultation Portal**
   * Dynamic listing of specialized consultants (seeded data).
   * Scheduling calendar & consultation format selector (Video / In-person).
   * Encrypted client-doctor direct messaging logs.

7. **Twilio SMS Gateway & Reminders**
   * Dispatches warning alerts to configured numbers (`7795273421` for Patient, `7019113622` for Admin) upon severe vital readings, critical OCR classifications, or manual SOS alerts.
   * Daily medicine intake SMS notifications.

8. **Pulsing SOS Emergency Alert**
   * Instant float button dispatching geo-coordinates and patient medical history summary to emergency coordinators.

9. **Admin Intelligence Hub**
   * Aggregate stats grid, disease analytic counts, user permission lists, system action logs, and Twilio SMS transmission audit logs.

---

## 🛠️ Technology Stack

* **Frontend**: React.js, Tailwind CSS v3, Chart.js / React-Chartjs-2, Lucide Icons.
* **Backend**: Python Flask, Flask-CORS, PyJWT, Bcrypt, PyMySQL (MySQL connector), Pytesseract, Pillow.
* **Database**: MySQL (Production) / SQLite `curaai.db` (Dynamic development fallback).
* **Machine Learning**: Scikit-Learn, Pandas, NumPy.
* **Notifications**: Twilio SMS API.

---

## 🚀 Setup & Execution Guide

### Prerequisite Checklist
* **Python**: Python 3.12+ installed (invocable via `py`).
* **Node.js**: Node v18+ with `npm` installed.

### Execution steps

To run both servers automatically in separate terminal windows:
1. Double-click the **`run.bat`** script at the project root directory.

### Manual Backend Setup (`/backend`)
1. Open a terminal in `/backend`.
2. Run `py -m pip install -r requirements.txt` to install dependencies.
3. Start the Flask server:
   ```bash
   py app.py
   ```
4. The backend initializes, creates the SQLite file (`curaai.db`), triggers the seeder database scripts, and starts listening on:
   * **API URL**: `http://localhost:5000/api`

### Manual Frontend Setup (`/frontend`)
1. Open a terminal in `/frontend`.
2. Run `npm install` to load packages.
3. Launch the React Vite server:
   ```bash
   npm run dev
   ```
4. Access the web dashboard on:
   * **App URL**: `http://127.0.0.1:5173/`

---

## 🔑 Default Seeded Accounts

The database contains pre-configured credentials for quick evaluations:

| Role | Mobile Number | Password | Purpose |
| :--- | :--- | :--- | :--- |
| **Patient** | `7795273421` | `password123` | Log vitals, scan reports, chat with doctors, test SOS |
| **Admin** | `7019113622` | `admin123` | Review Twilio logs, disease graphs, and system events |
| **Doctor** (Dr. Sarah Connor) | `7019113620` | `doctor123` | View appointment board, read patient histories, chat |

---

## 🛡️ Robust Fail-Safe Behaviors

* **Database Driver Fallback**: If MySQL details are missing or the database server is offline, the backend dynamically loads standard SQLite, mapping the `%s` SQL query tokens to `?` placeholder parameters on-the-fly.
* **OCR Binary Fallback**: If `pytesseract` throws exceptions (due to missing system binary), the script intercepts the call and falls back to a rules-based keyword extractor, analyzing the file content and returning realistic clinical outputs.
* **Twilio SMS Logging Fallback**: If Twilio credentials are not set in the environment variables, the system logs the SMS to standard console output and dashboard notification records so evaluations are never blocked.
