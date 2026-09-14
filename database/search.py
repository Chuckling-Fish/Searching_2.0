import re
import sqlite3

from database import DATABASE_PATH


def sanitize_fts_query(query):
    tokens = re.findall(r"\w+", query.lower())
    if not tokens:
        return None
    return " ".join(f'"{token}"' for token in tokens)


def keyword_search(query, limit=10):
    safe_query = sanitize_fts_query(query)
    if safe_query is None:
        return []
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            chunks.id AS chunk_id,
            files.path AS file_path,
            files.name AS file_name,
            chunks.page_start,
            chunks.page_end,
            chunks.heading,
            chunks.section_path,
            chunks.chunk_type,
            snippet(chunks_fts, 2, '[', ']', ' ... ', 12) AS snippet,
            bm25(chunks_fts) AS score
        FROM chunks_fts
        JOIN chunks ON chunks.id = chunks_fts.rowid
        JOIN files ON files.id = chunks.file_id
        WHERE chunks_fts MATCH ?
        ORDER BY score
        LIMIT ?
    """, (safe_query, limit))
    results = [dict(row) for row in cursor.fetchall()]
    connection.close()

    return results


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Search: ")
    results = keyword_search(query)
    if not results:
        print("No results.")
    for i, result in enumerate(results, start=1):
        print("\n" + "-" * 80)
        print(f"{i}. {result['file_name']}  (page {result['page_start']}-{result['page_end']})")
        print(f"   Section: {result['section_path']}")
        print(f"   Score:   {result['score']:.3f}")
        print(f"   {result['snippet']}")