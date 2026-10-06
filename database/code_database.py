import sqlite3

class CodeDatabase:
    def __init__(self, db_path="database/code_search.db"):
        self.connection = sqlite3.connect(db_path)
        self.create_tables()
        self.ensure_behavior_column()
        self.ensure_fts_table()

    def create_tables(self):
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS code_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                language TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                name TEXT,
                start_line INTEGER,
                end_line INTEGER,
                code TEXT NOT NULL,
                behavior TEXT DEFAULT ''
            )
        """)

        self.connection.commit()

    def ensure_behavior_column(self):
        columns = self.connection.execute("""
            PRAGMA table_info(code_chunks)
        """).fetchall()

        column_names = [
            column[1]
            for column in columns
        ]

        if "behavior" not in column_names:
            self.connection.execute("""
                ALTER TABLE code_chunks
                ADD COLUMN behavior TEXT DEFAULT ''
            """)
            self.connection.commit()

    def ensure_fts_table(self):
        # Check existing FTS columns
        rows = self.connection.execute("""
            PRAGMA table_info(code_chunks_fts)
        """).fetchall()

        existing_columns = [
            row[1]
            for row in rows
        ]

        # If FTS table does not exist, create it
        if not existing_columns:
            self.connection.execute("""
                CREATE VIRTUAL TABLE code_chunks_fts
                USING fts5(
                    file_path,
                    name,
                    code,
                    behavior,
                    content='code_chunks',
                    content_rowid='id'
                )
            """)

            self.connection.commit()
            self.rebuild_fts()
            return

        # Existing FTS table does not contain behavior.
        if "behavior" not in existing_columns:
            self.connection.execute("""
                DROP TABLE code_chunks_fts
            """)

            self.connection.execute("""
                CREATE VIRTUAL TABLE code_chunks_fts
                USING fts5(
                    file_path,
                    name,
                    code,
                    behavior,
                    content='code_chunks',
                    content_rowid='id'
                )
            """)

            self.connection.commit()
            self.rebuild_fts()

    def rebuild_fts(self):
        self.connection.execute("""
            INSERT INTO code_chunks_fts (
                rowid,
                file_path,
                name,
                code,
                behavior
            )
            SELECT
                id,
                file_path,
                name,
                code,
                behavior
            FROM code_chunks
        """)
        self.connection.commit()

    def delete_file_chunks(self, file_path):
        file_path = str(file_path)

        # Find existing chunk IDs
        rows = self.connection.execute("""
            SELECT id
            FROM code_chunks
            WHERE file_path = ?
        """, (file_path,)).fetchall()

        # Remove corresponding FTS rows
        for (chunk_id,) in rows:
            self.connection.execute("""
                DELETE FROM code_chunks_fts
                WHERE rowid = ?
            """, (chunk_id,))

        # Remove chunks from main table
        self.connection.execute("""
            DELETE FROM code_chunks
            WHERE file_path = ?
        """, (file_path,))
        self.connection.commit()

    def insert_chunk(self, chunk, file_path):
        file_path = str(file_path)
        cursor = self.connection.execute("""
            INSERT INTO code_chunks (
                file_path,
                language,
                chunk_type,
                name,
                start_line,
                end_line,
                code,
                behavior
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_path,
            chunk.language,
            chunk.chunk_type,
            chunk.name,
            chunk.start_line,
            chunk.end_line,
            chunk.code,
            chunk.behavior
        ))

        chunk_id = cursor.lastrowid
        self.connection.execute("""
            INSERT INTO code_chunks_fts (
                rowid,
                file_path,
                name,
                code,
                behavior
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            chunk_id,
            file_path,
            chunk.name,
            chunk.code,
            chunk.behavior
        ))
        self.connection.commit()

    def get_all_chunks(self):
        cursor = self.connection.execute("""
            SELECT
                id,
                file_path,
                language,
                chunk_type,
                name,
                start_line,
                end_line,
                code,
                behavior
            FROM code_chunks
        """)
        return cursor.fetchall()

    def search(self, query):
        cursor = self.connection.execute("""
            SELECT
                code_chunks.id,
                code_chunks.file_path,
                code_chunks.language,
                code_chunks.chunk_type,
                code_chunks.name,
                code_chunks.start_line,
                code_chunks.end_line,
                code_chunks.code,
                code_chunks.behavior
            FROM code_chunks_fts
            JOIN code_chunks
                ON code_chunks.id = code_chunks_fts.rowid
            WHERE code_chunks_fts MATCH ?
        """, (query,))
        return cursor.fetchall()