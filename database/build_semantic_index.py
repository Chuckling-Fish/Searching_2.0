import hnswlib
from sentence_transformers import SentenceTransformer
from pathlib import Path

from database.code_database import CodeDatabase


BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "code_vector_index.bin"

MODEL_NAME = "all-MiniLM-L6-v2"


def load_all_chunks():

    database = CodeDatabase()

    rows = database.get_all_chunks()

    return rows


def build_search_text(row):

    (
        chunk_id,
        file_path,
        language,
        chunk_type,
        name,
        start_line,
        end_line,
        code,
        behavior
    ) = row

    # Convert bytes to text if necessary
    if isinstance(code, bytes):

        code = code.decode(
            "utf-8",
            errors="replace"
        )

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


def build_index():

    rows = load_all_chunks()

    if not rows:

        print(
            "No code chunks found in database."
        )

        return

    chunk_ids = [
        row[0]
        for row in rows
    ]

    texts = [
        build_search_text(row)
        for row in rows
    ]

    print(
        f"Embedding {len(texts)} chunks "
        f"with {MODEL_NAME}..."
    )

    try:

        model = SentenceTransformer(
            MODEL_NAME,
            local_files_only=True
        )

    except OSError:

        model = SentenceTransformer(
            MODEL_NAME
        )

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    dimension = model.get_embedding_dimension()

    print(
        f"Embedding dimension: {dimension}"
    )

    print(
        "Building HNSWlib index..."
    )

    index = hnswlib.Index(
        space="cosine",
        dim=dimension
    )

    index.init_index(
        max_elements=len(chunk_ids),
        ef_construction=200,
        M=16
    )

    index.add_items(
        embeddings,
        chunk_ids
    )

    index.set_ef(50)

    index.save_index(
        str(INDEX_PATH)
    )

    print(
        f"Saved vector index "
        f"({len(chunk_ids)} chunks) "
        f"to {INDEX_PATH}"
    )


if __name__ == "__main__":

    build_index()