import sqlite3

conn = sqlite3.connect('curaai.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get doctor user IDs to delete
c.execute("SELECT user_id FROM doctors")
rows = c.fetchall()
doc_user_ids = [r[0] for r in rows]

# Delete existing doctors and their users
c.execute("DELETE FROM doctors")
if doc_user_ids:
    placeholders = ','.join(['?' for _ in doc_user_ids])
    c.execute(f"DELETE FROM users WHERE id IN ({placeholders})", doc_user_ids)

print(f"Removed {len(doc_user_ids)} old doctors")

import bcrypt
doctor_pw = bcrypt.hashpw(b"docpassword123", bcrypt.gensalt()).decode()

indian_doctors = [
    ("Dr. Rajesh Sharma",   "9998887771", "Cardiologist",      18, "Mon-Wed 09:00 - 13:00", 800.00,  4.90),
    ("Dr. Priya Nair",      "9998887772", "Neurologist",       14, "Tue-Thu 10:00 - 15:00", 900.00,  4.85),
    ("Dr. Suresh Patel",    "9998887773", "General Physician", 10, "Mon-Fri 08:00 - 12:00", 400.00,  4.75),
    ("Dr. Ananya Krishnan", "9998887774", "Dermatologist",     12, "Wed-Fri 13:00 - 17:00", 600.00,  4.70),
    ("Dr. Vikram Mehta",    "9998887775", "Orthopedic",        16, "Mon-Thu 14:00 - 18:00", 700.00,  4.90),
    ("Dr. Kavitha Reddy",   "9998887776", "Diabetologist",     13, "Tue-Fri 09:00 - 14:00", 650.00,  4.88),
]

for name, mobile, spec, exp, avail, fees, rating in indian_doctors:
    # Insert user
    c.execute(
        "INSERT INTO users (name, mobile_number, password_hash, role) VALUES (?, ?, ?, ?)",
        (name, mobile, doctor_pw, "doctor")
    )
    uid = c.lastrowid
    # Insert doctor
    c.execute(
        """INSERT INTO doctors (user_id, name, specialization, experience, availability,
           consultation_fees, ratings, profile_pic) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (uid, name, spec, exp, avail, fees, rating, f"doctor_{spec.lower().replace(' ','_')}.png")
    )
    print(f"  Added {name} ({spec}) - Rs.{fees}")

conn.commit()
conn.close()
print("\nAll Indian doctors inserted successfully!")
