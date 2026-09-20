
import sqlite3


class CodeDatabase:

    def __init__(self, db_path="database/code_search.db"):
        self.connection = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):

        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS code_chunks (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                language TEXT NOT NULL,

                chunk_type TEXT NOT NULL,

                name TEXT,

                start_line INTEGER,

                end_line INTEGER,

                code TEXT NOT NULL
            )
        """)

        self.connection.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS code_chunks_fts
            USING fts5(
                name,
                code,
                content='code_chunks',
                content_rowid='id'
            )
        """)

        # Rebuild FTS5 index from existing code_chunks
        self.connection.execute("""
            INSERT INTO code_chunks_fts(code_chunks_fts)
            VALUES('rebuild')
        """)

        self.connection.commit()

    def insert_chunk(self, chunk):

        cursor = self.connection.execute("""
            INSERT INTO code_chunks (
                language,
                chunk_type,
                name,
                start_line,
                end_line,
                code
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            chunk.language,
            chunk.chunk_type,
            chunk.name,
            chunk.start_line,
            chunk.end_line,
            chunk.code
        ))

        chunk_id = cursor.lastrowid

        self.connection.execute("""
            INSERT INTO code_chunks_fts (
                rowid,
                name,
                code
            )
            VALUES (?, ?, ?)
        """, (
            chunk_id,
            chunk.name,
            chunk.code
        ))

        self.connection.commit()

    def get_all_chunks(self):

        cursor = self.connection.execute("""
            SELECT
                id,
                language,
                chunk_type,
                name,
                start_line,
                end_line,
                code
            FROM code_chunks
        """)

        return cursor.fetchall()

    def search(self, query):

        cursor = self.connection.execute("""
            SELECT
                code_chunks.id,
                code_chunks.language,
                code_chunks.chunk_type,
                code_chunks.name,
                code_chunks.start_line,
                code_chunks.end_line,
                code_chunks.code
            FROM code_chunks_fts
            JOIN code_chunks
                ON code_chunks.id = code_chunks_fts.rowid
            WHERE code_chunks_fts MATCH ?
        """, (query,))

        return cursor.fetchall()

