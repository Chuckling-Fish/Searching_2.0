from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "index.db"

connection = sqlite3.connect(DATABASE_PATH)

cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        file_id INTEGER PRIMARY KEY,
        name TEXT,
        extension TEXT,
        path TEXT,
        parent TEXT,
        size INTEGER,
        created TEXT,
        last_modified TEXT,
        last_accessed TEXT,
        is_file INTEGER
    )
""")

connection.commit()
connection.close()