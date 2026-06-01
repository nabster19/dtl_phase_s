# database.py - Database Connection Manager for CuraAI
# Integrates MySQL database with automatic SQLite fallback

import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor

# Configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "curaai")
USE_MYSQL = os.environ.get("USE_MYSQL", "false").lower() == "true"

class DatabaseManager:
    def __init__(self):
        self.is_sqlite = True
        self.connection = None
        self.sqlite_path = "curaai.db"
        self.connect()

    def connect(self):
        if USE_MYSQL:
            try:
                self.connection = pymysql.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME,
                    cursorclass=DictCursor,
                    autocommit=True
                )
                self.is_sqlite = False
                print("[CuraAI Database] Connected to MySQL database.")
            except Exception as e:
                print(f"[CuraAI Database] MySQL Connection Failed: {e}. Falling back to SQLite.")
                self.is_sqlite = True
        
        if self.is_sqlite:
            # SQLite path is in current working directory
            self.connection = sqlite3.connect(self.sqlite_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            print(f"[CuraAI Database] Connected to SQLite database: {os.path.abspath(self.sqlite_path)}")
            self.create_sqlite_tables()

    def get_cursor(self):
        if self.is_sqlite:
            # For SQLite, we reconnect or return cursor from connection
            return self.connection.cursor()
        else:
            try:
                self.connection.ping(reconnect=True)
                return self.connection.cursor()
            except Exception as e:
                print(f"[CuraAI Database] Reconnecting MySQL: {e}")
                self.connect()
                return self.connection.cursor()

    def execute_query(self, query, params=None):
        """Executes an INSERT, UPDATE, or DELETE query and returns the lastrowid."""
        if params is None:
            params = ()
        
        # SQLite uses ? instead of %s
        if self.is_sqlite:
            query = query.replace("%s", "?")

        cursor = self.get_cursor()
        try:
            cursor.execute(query, params)
            if self.is_sqlite:
                self.connection.commit()
                last_id = cursor.lastrowid
            else:
                last_id = cursor.lastrowid
            cursor.close()
            return last_id
        except Exception as e:
            print(f"[CuraAI Database] Query Execution Error: {e}")
            if self.is_sqlite:
                self.connection.rollback()
            raise e

    def fetch_all(self, query, params=None):
        """Fetches all rows matching the query."""
        if params is None:
            params = ()
        
        if self.is_sqlite:
            query = query.replace("%s", "?")

        cursor = self.get_cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            if self.is_sqlite:
                # Convert SQLite Rows to standard dicts
                result = [dict(row) for row in rows]
            else:
                result = list(rows)
            cursor.close()
            return result
        except Exception as e:
            print(f"[CuraAI Database] Fetch All Error: {e}")
            raise e

    def fetch_one(self, query, params=None):
        """Fetches a single row matching the query."""
        if params is None:
            params = ()

        if self.is_sqlite:
            query = query.replace("%s", "?")

        cursor = self.get_cursor()
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            if self.is_sqlite:
                result = dict(row) if row else None
            else:
                result = row
            cursor.close()
            return result
        except Exception as e:
            print(f"[CuraAI Database] Fetch One Error: {e}")
            raise e

    def create_sqlite_tables(self):
        """Creates SQLite tables if they do not exist, mapping types from MySQL schema."""
        cursor = self.connection.cursor()
        
        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile_number TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ('patient', 'doctor', 'admin')) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 2. Doctors Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            experience INTEGER NOT NULL,
            availability TEXT NOT NULL,
            consultation_fees REAL NOT NULL,
            ratings REAL DEFAULT 5.0,
            profile_pic TEXT DEFAULT 'default_doctor.png',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # 3. Patients Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            age INTEGER,
            gender TEXT,
            blood_group TEXT,
            weight REAL,
            height REAL,
            address TEXT,
            medical_history TEXT,
            allergies TEXT DEFAULT '',
            medications TEXT DEFAULT '',
            emergency_contact TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)


        # 4. Health Records
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            blood_pressure_sys INTEGER,
            blood_pressure_dia INTEGER,
            sugar_level INTEGER,
            cholesterol INTEGER,
            weight REAL,
            height REAL,
            bmi REAL,
            heart_rate INTEGER,
            oxygen_level INTEGER,
            temperature REAL,
            water_intake INTEGER,
            recorded_date DATE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
            UNIQUE(patient_id, recorded_date)
        )
        """)

        # 5. Symptoms Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS symptoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            category TEXT CHECK(category IN ('common', 'chronic', 'rare', 'genetic', 'lifestyle')) NOT NULL
        )
        """)

        # 6. Disease Predictions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS disease_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            symptoms_entered TEXT NOT NULL,
            predicted_disease TEXT NOT NULL,
            confidence_percentage REAL NOT NULL,
            severity_level TEXT CHECK(severity_level IN ('low', 'medium', 'high', 'critical')) NOT NULL,
            is_rare INTEGER DEFAULT 0,
            precautions_recommended TEXT,
            next_medical_actions TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
        """)

        # 7. Drug Recommendations
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS drug_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            patient_id INTEGER NOT NULL,
            recommended_medicines TEXT NOT NULL,
            dosage TEXT,
            usage_timing TEXT,
            side_effects TEXT,
            food_restrictions TEXT,
            precautions TEXT,
            alternatives TEXT,
            generic_medicines TEXT,
            emergency_warnings TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (prediction_id) REFERENCES disease_predictions(id) ON DELETE SET NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
        """)

        # 8. Prescriptions
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS prescriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER,
            doctor_name TEXT DEFAULT 'Self Uploaded',
            medicine_names TEXT,
            dosage_instructions TEXT,
            diagnosis TEXT,
            ocr_extracted_text TEXT,
            file_path TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE SET NULL
        )
        """)

        # 9. Reports
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            report_type TEXT CHECK(report_type IN ('blood_test', 'x-ray', 'scan', 'other')) NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            ocr_text TEXT,
            ai_summary TEXT,
            severity_level TEXT CHECK(severity_level IN ('low', 'medium', 'high', 'critical')) DEFAULT 'low',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
        )
        """)

        # 10. Appointments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date DATE NOT NULL,
            appointment_time TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending', 'confirmed', 'completed', 'cancelled')) DEFAULT 'pending',
            consultation_type TEXT CHECK(consultation_type IN ('video', 'in-person')) DEFAULT 'video',
            fees REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE
        )
        """)

        # 11. Notifications
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mobile_number TEXT NOT NULL,
            type TEXT DEFAULT 'sms',
            message TEXT NOT NULL,
            status TEXT CHECK(status IN ('sent', 'failed')) DEFAULT 'sent',
            trigger_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # 12. Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # 13. Chatbot Messages Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chatbot_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT CHECK(role IN ('user','assistant')) NOT NULL,
            message TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        self.connection.commit()
        cursor.close()

db = DatabaseManager()
