import os

# Force offline mode so no Hugging Face Hub request is ever made
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import hnswlib
from sentence_transformers import SentenceTransformer
from pathlib import Path

from database.code_database import CodeDatabase

MODEL_NAME = "all-MiniLM-L6-v2"


class SemanticSearch:
    def __init__(self):
        # Load the embedding model used for code chunks, from the local cache only
        print("Loading embedding model...")
        try:
            self.model = SentenceTransformer(
                MODEL_NAME,
                local_files_only=True
            )
        except OSError:
            raise RuntimeError(
                f"Embedding model '{MODEL_NAME}' is not cached locally, "
                f"and this program runs offline so it can't be downloaded "
                f"automatically. Run this once while online to cache it:\n\n"
                f"    python -c \"from sentence_transformers import SentenceTransformer; "
                f"SentenceTransformer('{MODEL_NAME}')\"\n\n"
                f"Then re-run this program offline."
            )

        print("Model loaded successfully.")
        self.database = CodeDatabase()
        self.index = None
        self.chunk_ids = []

        self.index_path = Path(
            "database/code_vector_index.bin"
        )

    def load_index(self):
        # Make sure the vector index file exists
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Semantic index not found: {self.index_path} - "
                f"run build_semantic_index.py first."
            )

        rows = self.database.get_all_chunks()
        if not rows:
            print("No code chunks found.")
            return

        self.chunk_ids = [
            row[0]
            for row in rows
        ]

        dimension = self.model.get_sentence_embedding_dimension()
        self.index = hnswlib.Index(
            space="cosine",
            dim=dimension
        )

        # Load the saved vector index from disk
        self.index.load_index(
            str(self.index_path)
        )

        self.index.set_ef(50)
        print("Semantic index loaded successfully.")

    def search(self, query, k=3):
        if self.index is None:
            raise RuntimeError(
                "Semantic index has not been loaded. Call load_index() first."
            )

        # Encode the query into a normalized vector
        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        )

        # Find the nearest chunks in the vector index
        labels, distances = self.index.knn_query(
            query_embedding,
            k=k
        )

        rows = {
            row[0]: row
            for row in self.database.get_all_chunks()
        }

        results = []

        # Build a result entry for each matched chunk
        for label, distance in zip(
            labels[0],
            distances[0]
        ):
            chunk_id = int(label)
            row = rows.get(chunk_id)
            if not row:
                continue

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

            if isinstance(code, bytes):
                code = code.decode(
                    "utf-8",
                    errors="replace"
                )

            behavior = behavior or ""
            # Convert cosine distance into a similarity score
            similarity = 1 - float(distance)
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
                "score": similarity,
                "language": language,
                "name": name,
                "start_line": start_line,
                "end_line": end_line,
                "code": code,
                "behavior": behavior,
                "source_type": "code"
            })
        return results
