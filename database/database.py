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
    last_accessed REAL,
    hash TEXT,
    indexed_at REAL,
    content_indexed INTEGER NOT NULL DEFAULT 0,
    name_tokens TEXT
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

    FOREIGN KEY (file_id) REFERENCES files(id)
);

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    heading,
    section_path,
    text,
    content='chunks',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS chunks_after_insert AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts(rowid, heading, section_path, text)
    VALUES (new.id, new.heading, new.section_path, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_after_delete AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, heading, section_path, text)
    VALUES ('delete', old.id, old.heading, old.section_path, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_after_update AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts(chunks_fts, rowid, heading, section_path, text)
    VALUES ('delete', old.id, old.heading, old.section_path, old.text);
    INSERT INTO chunks_fts(rowid, heading, section_path, text)
    VALUES (new.id, new.heading, new.section_path, new.text);
END;

-- -----------------------------------------------------------
-- Filename search, over ALL files (including types with no
-- content extractor - images, videos, archives, etc). name_tokens
-- is precomputed in Python (indexing.tokenize_filename: split on
-- _/-/./camelCase) and stored as a real column, because FTS5's
-- own tokenizer can't do camelCase splitting - by the time it sees
-- the text, the splitting has already happened.
-- -----------------------------------------------------------

CREATE VIRTUAL TABLE IF NOT EXISTS files_fts USING fts5(
    name_tokens,
    content='files',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS files_after_insert AFTER INSERT ON files BEGIN
    INSERT INTO files_fts(rowid, name_tokens)
    VALUES (new.id, new.name_tokens);
END;

CREATE TRIGGER IF NOT EXISTS files_after_delete AFTER DELETE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, name_tokens)
    VALUES ('delete', old.id, old.name_tokens);
END;

CREATE TRIGGER IF NOT EXISTS files_after_update AFTER UPDATE ON files BEGIN
    INSERT INTO files_fts(files_fts, rowid, name_tokens)
    VALUES ('delete', old.id, old.name_tokens);
    INSERT INTO files_fts(rowid, name_tokens)
    VALUES (new.id, new.name_tokens);
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

    cursor.execute("SELECT COUNT(*) FROM files")
    files_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM files_fts")
    files_fts_count = cursor.fetchone()[0]
    if files_count > 0 and files_fts_count == 0:
        cursor.execute("INSERT INTO files_fts(files_fts) VALUES ('rebuild')")
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