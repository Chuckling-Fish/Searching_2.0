import hnswlib
from sentence_transformers import SentenceTransformer
from pathlib import Path

from database.code_database import CodeDatabase


class SemanticSearch:

    def __init__(self):

        print("Loading embedding model...")

        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        print("Model loaded successfully.")

        self.database = CodeDatabase()

        self.index = None
        self.chunk_ids = []

        # Location where the code semantic index is saved
        self.index_path = Path(
            "database/code_vector_index.bin"
        )

    def build_index(self):

        rows = self.database.get_all_chunks()

        if not rows:
            print("No code chunks found.")
            return

        self.chunk_ids = []

        texts = []

        for row in rows:

            chunk_id = row[0]
            code = row[7]

            if isinstance(code, bytes):
                code = code.decode(
                    "utf-8",
                    errors="replace"
                )

            self.chunk_ids.append(chunk_id)
            texts.append(code)

        print(
            f"Creating embeddings for {len(texts)} chunks..."
        )

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True
        )

        dimension = self.model.get_embedding_dimension()

        self.index = hnswlib.Index(
            space="cosine",
            dim=dimension
        )

        self.index.init_index(
            max_elements=len(embeddings),
            ef_construction=200,
            M=16
        )

        self.index.add_items(
            embeddings,
            self.chunk_ids
        )

        self.index.set_ef(50)

        print("Semantic index built successfully.")

        self.index.save_index(
            str(self.index_path)
        )

        print(
            f"Semantic index saved to {self.index_path}"
        )

    def load_index(self):

        if not self.index_path.exists():

            raise FileNotFoundError(
                f"Semantic index not found: {self.index_path}"
            )

        rows = self.database.get_all_chunks()

        if not rows:

            print("No code chunks found.")
            return

        self.chunk_ids = [
            row[0]
            for row in rows
        ]

        dimension = self.model.get_embedding_dimension()

        self.index = hnswlib.Index(
            space="cosine",
            dim=dimension
        )

        self.index.load_index(
            str(self.index_path)
        )

        self.index.set_ef(50)

        print("Semantic index loaded successfully.")

    def search(self, query, k=3):

        if self.index is None:

            raise RuntimeError(
                "Semantic index has not been built or loaded."
            )

        query_embedding = self.model.encode(
            [query],
            normalize_embeddings=True
        )

        labels, distances = self.index.knn_query(
            query_embedding,
            k=k
        )

        rows = {
            row[0]: row
            for row in self.database.get_all_chunks()
        }

        results = []

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