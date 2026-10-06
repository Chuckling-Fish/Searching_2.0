import re
from pathlib import Path

from database.code_database import CodeDatabase

def sanitize_fts_query(query):
    tokens = re.findall(r"\w+", query.lower())
    if not tokens:
        return None
    return " ".join(f'"{token}"' for token in tokens)

def keyword_search(query, extension=None, limit=10):
    safe_query = sanitize_fts_query(query)
    if safe_query is None:
        return []

    database = CodeDatabase()
    sql = """
        SELECT
            code_chunks.id,
            code_chunks.file_path,
            code_chunks.language,
            code_chunks.chunk_type,
            code_chunks.name,
            code_chunks.start_line,
            code_chunks.end_line,
            code_chunks.code,
            code_chunks.behavior,
            bm25(code_chunks_fts) AS score
        FROM code_chunks_fts
        JOIN code_chunks
            ON code_chunks.id = code_chunks_fts.rowid
        WHERE code_chunks_fts MATCH ?
    """
    parameters = [safe_query]
    if extension:
        extension = extension.lower()
        if not extension.startswith("."):
            extension = "." + extension

        sql += """
            AND lower(code_chunks.file_path) LIKE ?
        """

        parameters.append(f"%{extension}")

    sql += """
        ORDER BY score
        LIMIT ?
    """
    parameters.append(limit)

    cursor = database.connection.execute(
        sql,
        parameters
    )

    rows = cursor.fetchall()
    results = []
    for row in rows:
        (
            chunk_id,
            file_path,
            language,
            chunk_type,
            name,
            start_line,
            end_line,
            code,
            behavior,
            score
        ) = row

        if isinstance(code, bytes):
            code = code.decode(
                "utf-8",
                errors="replace"
            )

        behavior = behavior or ""

        results.append({
            "chunk_id": chunk_id,
            "file_id": None,
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "page_start": None,
            "page_end": None,
            "heading": name,
            "section_path": None,
            "chunk_type": chunk_type,
            "snippet": code,
            "score": score,
            "language": language,
            "name": name,
            "start_line": start_line,
            "end_line": end_line,
            "code": code,
            "behavior": behavior,
            "source_type": "code"
        })

    database.connection.close()
    return results