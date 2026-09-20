import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

DATABASE_PATH = Path(__file__).resolve().parent / "index.db"


@contextmanager
def scan_connection():
    """
    One connection for an entire scan.

    Previously every add_file/add_chunks call opened its own connection,
    committed, and closed it. Across thousands of files that's thousands
    of connection setups and thousands of disk syncs, which dominates
    runtime on a bulk scan. Holding one connection open and committing
    in batches avoids nearly all of that.

    WAL + synchronous=NORMAL cut fsync overhead further. The tradeoff is
    that a hard crash mid-scan could lose the last uncommitted batch -
    acceptable here, since the index is always rebuildable from the
    source files.
    """

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=NORMAL")

    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _connect(connection):
    """
    Lets every function below work either standalone (opens and closes
    its own connection, as before) or inside a scan (reuses the shared
    one). Returns (connection, should_close).
    """

    if connection is not None:
        return connection, False

    return sqlite3.connect(DATABASE_PATH), True


def add_file(file_data, file_hash=None, content_indexed=0, connection=None):
    conn, should_close = _connect(connection)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO files (
            path, name, extension, size,
            created, last_modified, last_accessed,
            hash, indexed_at, content_indexed, name_tokens
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name = excluded.name,
            extension = excluded.extension,
            size = excluded.size,
            created = excluded.created,
            last_modified = excluded.last_modified,
            last_accessed = excluded.last_accessed,
            hash = excluded.hash,
            indexed_at = excluded.indexed_at,
            content_indexed = excluded.content_indexed,
            name_tokens = excluded.name_tokens
    """, (
        file_data["path"],
        file_data["name"],
        file_data["extension"],
        file_data["size"],
        file_data["created"],
        file_data["last_modified"],
        file_data["last_accessed"],
        file_hash,
        time.time(),
        content_indexed,
        file_data["name_tokens"],
    ))

    cursor.execute("SELECT id FROM files WHERE path = ?", (file_data["path"],))
    file_id = cursor.fetchone()[0]

    if should_close:
        conn.commit()
        conn.close()

    return file_id


def get_indexed_files(connection=None):
    """
    Returns {path: (size, last_modified, hash)} for everything already
    indexed. Loaded once at the start of a scan so change detection is
    a dict lookup per file instead of a SQL query per file.
    """

    conn, should_close = _connect(connection)
    cursor = conn.cursor()

    cursor.execute("SELECT path, size, last_modified, hash FROM files")
    state = {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}

    if should_close:
        conn.close()

    return state


def delete_file(path, connection=None):
    """
    Remove a file and its chunks (used when a file disappears from disk).
    Chunks are deleted first so the FTS sync triggers fire for each one.
    """

    conn, should_close = _connect(connection)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM files WHERE path = ?", (path,))
    row = cursor.fetchone()

    if row:
        cursor.execute("DELETE FROM chunks WHERE file_id = ?", (row[0],))
        cursor.execute("DELETE FROM files WHERE id = ?", (row[0],))

    if should_close:
        conn.commit()
        conn.close()


def delete_chunks_for_file(file_id, connection=None):
    conn, should_close = _connect(connection)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))

    if should_close:
        conn.commit()
        conn.close()


def add_chunks(file_id, chunks, connection=None):
    if not chunks:
        return

    conn, should_close = _connect(connection)
    cursor = conn.cursor()

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
        )
        for chunk in chunks
    ]

    cursor.executemany("""
        INSERT INTO chunks (
            file_id, page_start, page_end,
            heading, parent_heading, section_path,
            chunk_type, text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)

    if should_close:
        conn.commit()
        conn.close()
