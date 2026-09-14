import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "index.db"

def add_file(file_data):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO files (
            path,
            name,
            extension,
            size,
            created,
            last_modified,
            last_accessed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name = excluded.name,
            extension = excluded.extension,
            size = excluded.size,
            created = excluded.created,
            last_modified = excluded.last_modified,
            last_accessed = excluded.last_accessed
    """, (
        file_data["path"],
        file_data["name"],
        file_data["extension"],
        file_data["size"],
        file_data["created"],
        file_data["last_modified"],
        file_data["last_accessed"]
    ))

    cursor.execute(
        "SELECT id FROM files WHERE path = ?",
        (file_data["path"],)
    )
    file_id = cursor.fetchone()[0]

    connection.commit()
    connection.close()

    return file_id


def delete_chunks_for_file(file_id):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM chunks WHERE file_id = ?",
        (file_id,)
    )

    connection.commit()
    connection.close()


def add_chunk(file_id, chunk):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        INSERT INTO chunks (
            file_id,
            page_start,
            page_end,
            heading,
            parent_heading,
            section_path,
            chunk_type,
            text,
            search_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        file_id,
        chunk["page_start"],
        chunk["page_end"],
        chunk["heading"],
        chunk["parent_heading"],
        " > ".join(chunk["section_path"]),
        chunk["chunk_type"],
        chunk["text"],
        chunk["search_text"]
    ))

    connection.commit()
    connection.close()


def add_chunks(file_id, chunks):
    if not chunks:
        return
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    rows = [
        (
            file_id,
            chunk["page_start"],
            chunk["page_end"],
            chunk["heading"],
            chunk["parent_heading"],
            " > ".join(chunk["section_path"]),
            chunk["chunk_type"],
            chunk["text"],
            chunk["search_text"]
        )
        for chunk in chunks
    ]
    cursor.executemany("""
        INSERT INTO chunks (
            file_id,
            page_start,
            page_end,
            heading,
            parent_heading,
            section_path,
            chunk_type,
            text,
            search_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    connection.commit()
    connection.close()