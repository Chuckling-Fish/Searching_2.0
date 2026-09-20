import os
import sqlite3

# Skip the "has this model changed on the Hub?" network check that
# sentence-transformers/huggingface_hub normally does on every load,
# even when the model is already cached locally. Must be set BEFORE
# sentence_transformers is imported - it's read at import time.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import hnswlib
from sentence_transformers import SentenceTransformer

from database import DATABASE_PATH
from build_semantic_index import MODEL_NAME, EMBEDDING_DIM, INDEX_PATH

# Loaded once per process and reused - loading the model and the
# index file are the slow parts, so we don't want to redo them on
# every call to semantic_search().
_model = None
_index = None


def _load():
    global _model, _index

    if _model is None:
        # local_files_only as a second guarantee alongside HF_HUB_OFFLINE -
        # this fails fast with a clear error if the model was never
        # downloaded, instead of silently trying to reach the network.
        _model = SentenceTransformer(MODEL_NAME, local_files_only=True)

    if _index is None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                "No vector index found - run build_semantic_index.py first."
            )

        _index = hnswlib.Index(space="cosine", dim=EMBEDDING_DIM)
        _index.load_index(str(INDEX_PATH))

    return _model, _index


def semantic_search(query, extension=None, limit=10):
    """
    Returns the `limit` chunks whose meaning is closest to the query,
    even if they don't share exact words with it. Lower score = more
    similar (cosine distance), same convention as bm25 in
    keyword_search - both sort ascending.

    HNSWlib has no notion of "only search chunks from .pdf files" -
    it just returns the k nearest vectors, full stop. So when an
    extension filter is given, more neighbors are requested from
    HNSWlib than needed (OVER_FETCH_MULTIPLIER x) and the extras are
    filtered out in SQL afterwards. This means a very rare extension
    among a huge, mostly-different-type corpus could still return
    fewer than `limit` results - a real limitation of bolting a
    metadata filter onto an ANN index after the fact, not a bug.
    """

    model, index = _load()

    query_vector = model.encode([query], normalize_embeddings=True)

    OVER_FETCH_MULTIPLIER = 5
    k = limit * OVER_FETCH_MULTIPLIER if extension else limit
    k = min(k, index.get_current_count())

    labels, distances = index.knn_query(query_vector, k=k)

    chunk_ids = labels[0].tolist()
    scores = distances[0].tolist()

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    results = []

    for chunk_id, score in zip(chunk_ids, scores):
        sql = """
            SELECT
                chunks.id AS chunk_id,
                files.id AS file_id,
                files.path AS file_path,
                files.name AS file_name,
                chunks.page_start,
                chunks.page_end,
                chunks.heading,
                chunks.section_path,
                chunks.text
            FROM chunks
            JOIN files ON files.id = chunks.file_id
            WHERE chunks.id = ?
        """
        params = [chunk_id]

        if extension:
            sql += " AND files.extension = ?"
            params.append(extension)

        cursor.execute(sql, params)
        row = cursor.fetchone()

        if row:
            result = dict(row)
            result["score"] = score
            results.append(result)

        if len(results) >= limit:
            break

    connection.close()

    return results


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Search: ")

    for i, result in enumerate(semantic_search(query), start=1):
        print(f"\n{i}. {result['file_name']} (page {result['page_start']}-{result['page_end']})")
        print(f"   Section: {result['section_path']}")
        print(f"   Distance: {result['score']:.4f}")
        print(f"   {result['text'][:200]}...")
