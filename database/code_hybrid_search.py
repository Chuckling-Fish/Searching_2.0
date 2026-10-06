from database.code_search import keyword_search
from search.semantic_search import SemanticSearch

RRF_K = 60

class CodeHybridSearch:
    def __init__(self):
        print("Initializing code hybrid search...")
        self.semantic_search = SemanticSearch()
        self.semantic_search.load_index()
        print("Code hybrid search ready.")

    def reciprocal_rank_fusion(self, result_lists, limit=10):
        combined = {}
        for results in result_lists:
            for rank, result in enumerate(results, start=1):
                chunk_id = result["chunk_id"]
                if chunk_id not in combined:
                    combined[chunk_id] = {
                        "result": result,
                        "rrf_score": 0.0
                    }
                combined[chunk_id]["rrf_score"] += (
                    1.0 / (RRF_K + rank)
                )
        fused = sorted(
            combined.values(),
            key=lambda item: item["rrf_score"],
            reverse=True
        )
        results = []
        for item in fused[:limit]:
            result = dict(item["result"])
            result["rrf_score"] = item["rrf_score"]
            results.append(result)
        return results

    def search(
        self,
        query,
        mode="hybrid",
        extension=None,
        limit=10
    ):

        if mode == "keyword":
            return keyword_search(
                query,
                extension=extension,
                limit=limit
            )

        if mode == "semantic":
            results = self.semantic_search.search(
                query,
                k=limit
            )

            if extension:
                results = [
                    result
                    for result in results
                    if result["file_path"]
                    .lower()
                    .endswith(extension.lower())
                ]

            return results[:limit]
        
        if mode == "hybrid":
            keyword_results = keyword_search(
                query,
                extension=extension,
                limit=limit * 2
            )

            semantic_results = self.semantic_search.search(
                query,
                k=limit * 2
            )

            if extension:
                semantic_results = [
                    result
                    for result in semantic_results
                    if result["file_path"]
                    .lower()
                    .endswith(extension.lower())
                ]

            return self.reciprocal_rank_fusion(
                [
                    keyword_results,
                    semantic_results
                ],
                limit=limit
            )

        raise ValueError(
            f"Unknown search mode: {mode!r}"
        )

_searcher = None

def get_code_searcher():
    global _searcher
    if _searcher is None:
        _searcher = CodeHybridSearch()
    return _searcher


def hybrid_search(
    query,
    mode="hybrid",
    extension=None,
    limit=10
):
    searcher = get_code_searcher()

    return searcher.search(
        query=query,
        mode=mode,
        extension=extension,
        limit=limit
    )


if __name__ == "__main__":
    print("Code Search")
    print("Type 'quit' to exit.\n")
    while True:
        query = input("Search: ").strip()
        if not query:
            continue

        if query.lower() in {"quit", "exit"}:
            print("Bye.")
            break

        results = hybrid_search(
            query,
            mode="hybrid",
            limit=10
        )

        print(
            f"\nFound {len(results)} results:\n"
        )

        for index, result in enumerate(
            results,
            start=1
        ):

            print(
                f"{index}. {result['file_name']}"
            )

            print(
                f"   Name: {result.get('name')}"
            )

            print(
                f"   Type: {result.get('chunk_type')}"
            )

            print(
                f"   Language: {result.get('language')}"
            )

            print(
                f"   Lines: "
                f"{result.get('start_line')}"
                f"-"
                f"{result.get('end_line')}"
            )

            print(
                f"   Score: "
                f"{result.get('rrf_score', result.get('score')):.4f}"
            )

            print()