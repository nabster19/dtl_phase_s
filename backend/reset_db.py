import sqlite3, os

db_path = 'curaai.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted {db_path}")
else:
    print("No existing DB found")
