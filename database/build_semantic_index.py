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
        # Prefer the locally cached model
        return SentenceTransformer(MODEL_NAME, local_files_only=True)
    except OSError:
        # Fall back to downloading the model
        return SentenceTransformer(MODEL_NAME)

# PDF chunks (from the general SQLite database)
def load_pdf_chunks():
    # Open a connection to the main database
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()

    # Fetch every stored PDF chunk
    cursor.execute("SELECT id, section_path, text FROM chunks")
    rows = cursor.fetchall()

    connection.close()
    return rows

def build_pdf_search_text(section_path, text):
    # Prefix the chunk text with its section path when available
    if section_path:
        return f"{section_path} {text}"
    return text

def build_pdf_index(model, embedding_dim):
    # Load all PDF chunks to embed
    rows = load_pdf_chunks()
    if not rows:
        print("No PDF chunks found in the database - run index_pdf.py first.")
        return

    chunk_ids = [row[0] for row in rows]
    texts = [build_pdf_search_text(row[1], row[2]) for row in rows]

    print(f"Embedding {len(texts)} PDF chunks with {MODEL_NAME}...")

    # Encode chunk text into normalized embeddings
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print("Building HNSWlib index for PDF chunks...")
    # Build and populate the vector index
    index = hnswlib.Index(space="cosine", dim=embedding_dim)
    index.init_index(max_elements=len(chunk_ids), ef_construction=200, M=16)
    index.add_items(embeddings, chunk_ids)
    index.set_ef(50)

    # Persist the index to disk
    index.save_index(str(PDF_INDEX_PATH))
    print(f"Saved PDF vector index ({len(chunk_ids)} chunks) to {PDF_INDEX_PATH}")


# Code chunks (from the dedicated code database)
def load_code_chunks():
    # Fetch every stored code chunk
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
    # Combine file, type and code details into one searchable text block
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
    # Load all code chunks to embed
    rows = load_code_chunks()
    if not rows:
        print("No code chunks found in database.")
        return
    chunk_ids = [row[0] for row in rows]
    texts = [build_code_search_text(row) for row in rows]

    print(f"Embedding {len(texts)} code chunks with {MODEL_NAME}...")

    # Encode chunk text into normalized embeddings
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    print("Building HNSWlib index for code chunks...")
    # Build and populate the vector index
    index = hnswlib.Index(space="cosine", dim=embedding_dim)
    index.init_index(max_elements=len(chunk_ids), ef_construction=200, M=16)
    index.add_items(embeddings, chunk_ids)
    index.set_ef(50)

    # Persist the index to disk
    index.save_index(str(CODE_INDEX_PATH))
    print(f"Saved code vector index ({len(chunk_ids)} chunks) to {CODE_INDEX_PATH}")

# Entry point - builds both indexes, loading the model once
def build_index():
    # Load the embedding model once for both indexes
    model = load_model()
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"Embedding dimension: {embedding_dim}")

    # Build the PDF and code vector indexes
    build_pdf_index(model, embedding_dim)
    build_code_index(model, embedding_dim)

if __name__ == "__main__":
    build_index()