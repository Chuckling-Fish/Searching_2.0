import os
import sqlite3

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import hnswlib
from sentence_transformers import SentenceTransformer, CrossEncoder

from database.database import DATABASE_PATH
from database.build_semantic_index import MODEL_NAME, EMBEDDING_DIM, INDEX_PATH

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

RERANK_POOL_MULTIPLIER = 4

_model = None
_index = None
_cross_encoder = None


def _load():
    global _model, _index

    # Load the embedding model once
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME, local_files_only=True)

    # Load the vector index once
    if _index is None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                "No vector index found - run build_semantic_index.py first."
            )

        _index = hnswlib.Index(space="cosine", dim=EMBEDDING_DIM)
        _index.load_index(str(INDEX_PATH))

    return _model, _index


def _load_cross_encoder():
    global _cross_encoder
    # Load the cross-encoder once, from the local cache only
    if _cross_encoder is None:
        try:
            _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL, local_files_only=True)
        except OSError:
            raise RuntimeError(
                f"Cross-encoder model '{CROSS_ENCODER_MODEL}' is not cached locally, "
                f"and this program runs with HF_HUB_OFFLINE=1 so it can't be downloaded "
                f"automatically. Run this once while online to cache it:\n\n"
                f"    python -c \"from sentence_transformers import CrossEncoder; "
                f"CrossEncoder('{CROSS_ENCODER_MODEL}')\"\n\n"
                f"Then re-run this program offline."
            )

    return _cross_encoder

RERANK_POOL_MULTIPLIER = 2

RERANK_TEXT_WORDS = 120

def semantic_search(query, extension=None, limit=10, rerank=False):
    model, index = _load()
    # Encode the query into a normalized vector
    query_vector = model.encode([query], normalize_embeddings=True)

    EXTENSION_OVER_FETCH_MULTIPLIER = 5
    # Fetch a larger candidate pool when reranking or filtering by extension
    pool_size = limit * RERANK_POOL_MULTIPLIER if rerank else limit
    if extension:
        pool_size = max(pool_size, limit * EXTENSION_OVER_FETCH_MULTIPLIER)

    k = min(pool_size, index.get_current_count())

    # Find the nearest chunks in the vector index
    labels, distances = index.knn_query(query_vector, k=k)

    chunk_ids = labels[0].tolist()
    vector_scores = distances[0].tolist()

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    candidates = []

    # Look up each matched chunk's full data
    for chunk_id, vector_score in zip(chunk_ids, vector_scores):
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

        # Restrict to a specific file extension if requested
        if extension:
            sql += " AND files.extension = ?"
            params.append(extension)

        cursor.execute(sql, params)
        row = cursor.fetchone()

        if row:
            result = dict(row)
            result["vector_score"] = vector_score
            candidates.append(result)
    connection.close()

    # Skip reranking and return the raw vector results
    if not rerank:
        return candidates[:limit]

    if not candidates:
        return []

    cross_encoder = _load_cross_encoder()

    # Score each query-candidate pair with the cross-encoder
    pairs = [
        [query, " ".join(candidate["text"].split()[:RERANK_TEXT_WORDS])]
        for candidate in candidates
    ]
    rerank_scores = cross_encoder.predict(pairs)

    for candidate, rerank_score in zip(candidates, rerank_scores):
        candidate["score"] = float(rerank_score)
        
    # Sort candidates by the reranked score
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates[:limit]


if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else input("Search: ")
    # Print each result with its relevance score
    for i, result in enumerate(semantic_search(query), start=1):
        print(f"\n{i}. {result['file_name']} (page {result['page_start']}-{result['page_end']})")
        print(f"   Section: {result['section_path']}")
        print(f"   Relevance: {result['score']:.4f}  (vector distance: {result['vector_score']:.4f})")
        print(f"   {result['text'][:200]}...")