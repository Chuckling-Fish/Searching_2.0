import sqlite3
from pathlib import Path

import hnswlib
from sentence_transformers import SentenceTransformer

from database import DATABASE_PATH

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "vector_index.bin"

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # output size of all-MiniLM-L6-v2


def load_all_chunks():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT id, section_path, text FROM chunks")
    rows = cursor.fetchall()

    connection.close()

    return rows


def build_search_text(section_path, text):
    """
    Rebuilds the "heading context + content" text used for embeddings,
    on the fly, from columns that are already stored (section_path,
    text). This used to be a separate search_text column, but that
    was just this same combination persisted a second time - storing
    it was pure duplication, so it's built here instead, only for as
    long as it takes to hand it to the embedding model.
    """

    if section_path:
        return f"{section_path} {text}"

    return text


def build_index():
    rows = load_all_chunks()

    if not rows:
        print("No chunks found in the database - run index_pdf.py first.")
        return

    chunk_ids = [row[0] for row in rows]
    texts = [build_search_text(row[1], row[2]) for row in rows]

    print(f"Embedding {len(texts)} chunks with {MODEL_NAME}...")

    try:
        # Fast path: model already downloaded, skip the network
        # cache-check entirely.
        model = SentenceTransformer(MODEL_NAME, local_files_only=True)
    except OSError:
        # First-ever run: nothing cached yet, so this one time has to
        # actually reach the network to download it.
        model = SentenceTransformer(MODEL_NAME)

    # normalize_embeddings=True makes cosine similarity == dot product,
    # which is what HNSWlib's "cosine" space actually computes internally
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print("Building HNSWlib index...")
    index = hnswlib.Index(space="cosine", dim=EMBEDDING_DIM)
    index.init_index(max_elements=len(chunk_ids), ef_construction=200, M=16)
    index.add_items(embeddings, chunk_ids)
    index.set_ef(50)

    index.save_index(str(INDEX_PATH))
    print(f"Saved vector index ({len(chunk_ids)} chunks) to {INDEX_PATH}")


if __name__ == "__main__":
    build_index()
