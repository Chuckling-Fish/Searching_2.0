from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "index.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    extension TEXT,
    size INTEGER,
    created REAL,
    last_modified REAL,
    last_accessed REAL
);

CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY,
    file_id INTEGER NOT NULL,
    page_start INTEGER,
    page_end INTEGER,
    heading TEXT,
    parent_heading TEXT,
    section_path TEXT,
    chunk_type TEXT,
    text TEXT NOT NULL,
    search_text TEXT NOT NULL,

    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    heading,
    section_path,
    text,
    search_text,
    content='chunks',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS chunks_after_insert AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, heading, section_path, text, search_text)
    VALUES (new.id, new.heading, new.section_path, new.text, new.search_text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_after_delete AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, heading, section_path, text, search_text)
    VALUES ('delete', old.id, old.heading, old.section_path, old.text, old.search_text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_after_update AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, heading, section_path, text, search_text)
    VALUES ('delete', old.id, old.heading, old.section_path, old.text, old.search_text);
    INSERT INTO chunks_fts(rowid, heading, section_path, text, search_text)
    VALUES (new.id, new.heading, new.section_path, new.text, new.search_text);
END;
"""


def _sync_fts_if_needed(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM chunks")
    chunks_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM chunks_fts")
    fts_count = cursor.fetchone()[0]
    if chunks_count > 0 and fts_count == 0:
        cursor.execute("INSERT INTO chunks_fts(chunks_fts) VALUES ('rebuild')")
        connection.commit()

def init_db():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.executescript(SCHEMA)
    connection.commit()
    _sync_fts_if_needed(connection)
    connection.close()


if __name__ == "__main__":
    init_db()
    print(f"Database ready at {DATABASE_PATH}")