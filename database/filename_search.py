import re
import sqlite3

from database.database import DATABASE_PATH

def sanitize_query_tokens(query):

    # Convert query into safe FTS tokens
    tokens = re.findall(r"\w+", query.lower())
    if not tokens:
        return None
    return " ".join(f'"{token}"' for token in tokens)

def filename_search(query, extension=None, limit=20):
    safe_query = sanitize_query_tokens(query)
    if safe_query is None:
        return []

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # Search file names using FTS5
    sql = """
        SELECT
            files.id AS file_id,
            files.path AS file_path,
            files.name AS file_name,
            files.extension,
            files.size,
            files.last_modified,
            files.content_indexed,
            bm25(files_fts) AS score
        FROM files_fts
        JOIN files ON files.id = files_fts.rowid
        WHERE files_fts MATCH ?
    """
    params = [safe_query]

    # Filter by extension when provided
    if extension:
        sql += " AND files.extension = ?"
        params.append(extension)
    sql += " ORDER BY score LIMIT ?"
    params.append(limit)

    cursor.execute(sql, params)
    results = [dict(row) for row in cursor.fetchall()]
    connection.close()
    return results


if __name__ == "__main__":
    import sys

    # Get the search query from arguments or input
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Search: ")

    for i, result in enumerate(filename_search(query), start=1):
        print(f"{i}. {result['file_name']}  ({result['file_path']})  score={result['score']:.3f}")