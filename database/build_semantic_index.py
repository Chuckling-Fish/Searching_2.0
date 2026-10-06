import sqlite3
from pathlib import Path

import hnswlib
from sentence_transformers import SentenceTransformer

from database.database import DATABASE_PATH
from database.code_database import CodeDatabase

BASE_DIR = Path(__file__).resolve().parent

PDF_INDEX_PATH = BASE_DIR / "vector_index.bin"
CODE_INDEX_PATH = BASE_DIR / "code_vector_index.bin"


INDEX_PATH = PDF_INDEX_PATH
EMBEDDING_DIM = 384  

MODEL_NAME = "all-MiniLM-L6-v2"



# Shared model loading
def load_model():
    try:
        return SentenceTransformer(MODEL_NAME, local_files_only=True)
    except OSError:
        return SentenceTransformer(MODEL_NAME)


# PDF chunks (from the general SQLite database)
def load_pdf_chunks():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    cursor.execute("SELECT id, section_path, text FROM chunks")
    rows = cursor.fetchall()

    connection.close()
    return rows


def build_pdf_search_text(section_path, text):
    if section_path:
        return f"{section_path} {text}"
    return text

def build_pdf_index(model, embedding_dim):
    rows = load_pdf_chunks()
    if not rows:
        print("No PDF chunks found in the database - run index_pdf.py first.")
        return

    chunk_ids = [row[0] for row in rows]
    texts = [build_pdf_search_text(row[1], row[2]) for row in rows]

    print(f"Embedding {len(texts)} PDF chunks with {MODEL_NAME}...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print("Building HNSWlib index for PDF chunks...")
    index = hnswlib.Index(space="cosine", dim=embedding_dim)
    index.init_index(max_elements=len(chunk_ids), ef_construction=200, M=16)
    index.add_items(embeddings, chunk_ids)
    index.set_ef(50)

    index.save_index(str(PDF_INDEX_PATH))
    print(f"Saved PDF vector index ({len(chunk_ids)} chunks) to {PDF_INDEX_PATH}")


# Code chunks (from the dedicated code database)

def load_code_chunks():
    database = CodeDatabase()
    rows = database.get_all_chunks()
    return rows

def build_code_search_text(row):
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
    ) = row

    # Convert bytes to text if necessary
    if isinstance(code, bytes):
        code = code.decode("utf-8", errors="replace")

    behavior = behavior or ""
    return f"""
File: {file_path}
Language: {language}
Type: {chunk_type}
Name: {name}
Behavior: {behavior}
Code:
{code}
"""

def build_code_index(model, embedding_dim):
    rows = load_code_chunks()
    if not rows:
        print("No code chunks found in database.")
        return
    chunk_ids = [row[0] for row in rows]
    texts = [build_code_search_text(row) for row in rows]

    print(f"Embedding {len(texts)} code chunks with {MODEL_NAME}...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print("Building HNSWlib index for code chunks...")
    index = hnswlib.Index(space="cosine", dim=embedding_dim)
    index.init_index(max_elements=len(chunk_ids), ef_construction=200, M=16)
    index.add_items(embeddings, chunk_ids)
    index.set_ef(50)

    index.save_index(str(CODE_INDEX_PATH))
    print(f"Saved code vector index ({len(chunk_ids)} chunks) to {CODE_INDEX_PATH}")


# Entry point - builds both indexes, loading the model once
def build_index():
    model = load_model()
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"Embedding dimension: {embedding_dim}")

    build_pdf_index(model, embedding_dim)
    build_code_index(model, embedding_dim)

if __name__ == "__main__":
    build_index()