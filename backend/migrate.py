import sqlite3
conn = sqlite3.connect('curaai.db')
c = conn.cursor()

new_cols = [
    "ALTER TABLE patients ADD COLUMN allergies TEXT DEFAULT ''",
    "ALTER TABLE patients ADD COLUMN medications TEXT DEFAULT ''",
    "ALTER TABLE patients ADD COLUMN emergency_contact TEXT DEFAULT ''",
    "ALTER TABLE patients ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
]

for sql in new_cols:
    try:
        c.execute(sql)
        print(f"OK: {sql[:50]}")
    except Exception as e:
        print(f"Skipped (probably exists): {e}")

conn.commit()
conn.close()
print("Migration complete.")
