import time

_import_started = time.time()

from database.search import keyword_search
from database.semantic_search import semantic_search
from database.filename_search import filename_search

_import_elapsed = time.time() - _import_started

# RRF constant for rank weighting
RRF_K = 60

def reciprocal_rank_fusion(result_lists, id_key):
    combined = {}
    # Accumulate a reciprocal rank score for each item across result lists
    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            key = result[id_key]

            if key not in combined:
                combined[key] = {"result": result, "rrf_score": 0.0}

            combined[key]["rrf_score"] += 1.0 / (RRF_K + rank)

    # Sort results by combined score
    fused = sorted(
        combined.values(),
        key=lambda entry: entry["rrf_score"],
        reverse=True
    )
    return [
        {**entry["result"], "rrf_score": entry["rrf_score"]}
        for entry in fused
    ]

def hybrid_search(query, mode="hybrid", extension=None, limit=10):
    # Select the requested search mode
    if mode == "keyword_only":
        content_results = keyword_search(
            query, extension=extension, limit=limit
        )
    elif mode == "semantic_only":
        content_results = semantic_search(
            query, extension=extension, limit=limit
        )
    elif mode == "hybrid":
        keyword_results = keyword_search(
            query, extension=extension, limit=limit * 2
        )
        semantic_results = semantic_search(
            query, extension=extension, limit=limit * 2
        )
        # Combine keyword and semantic rankings
        content_results = reciprocal_rank_fusion(
            [keyword_results, semantic_results],
            id_key="chunk_id"
        )[:limit]
    else:
        raise ValueError(f"Unknown mode: {mode!r}")
    # Search filenames separately
    filename_results = filename_search(
        query, extension=extension, limit=limit
    )
    filename_file_ids = {
        result["file_id"] for result in filename_results
    }
    # Mark content results whose filename also matches
    for result in content_results:
        result["name_also_matches"] = (
            result.get("file_id") in filename_file_ids
        )
    return {
        "content": content_results,
        "filenames": filename_results,
    }

def get_preview(result, max_chars=600):
    # Prefer an existing search snippet
    if result.get("snippet"):
        return result["snippet"]

    text = result.get("text", "")

    # Truncate long text at a word boundary
    if len(text) > max_chars:
        return text[:max_chars].rsplit(" ", 1)[0] + " ..."

    return text

def print_results(results, elapsed):
    print(f"{elapsed:.2f}s\n")

    print("=== Content matches ===")

    # Print each content match with its location and preview
    for i, r in enumerate(results["content"], start=1):
        marker = " [name also matches]" if r.get("name_also_matches") else ""
        heading = r.get("heading") or "(no heading)"
        pages = (
            f"p.{r['page_start']}-{r['page_end']}"
            if r.get("page_start")
            else ""
        )

        print(f"\n{i}. {r['file_name']}{marker}")
        print(f"   Location: {r['file_path']}")
        print(f"   {heading}  {pages}")
        print(f"   {get_preview(r)}")

    print("\n=== Filename matches ===")

    # Print each filename match
    for i, r in enumerate(results["filenames"], start=1):
        print(f"{i}. {r['file_name']}")
        print(f"   Location: {r['file_path']}")


def choose_mode():
    # Prompt the user to pick a search mode
    print()
    print("Search mode:")
    print("1. Hybrid")
    print("2. Keyword")
    print("3. Semantic")

    choice = input("Choose [1]: ").strip()

    if choice == "2":
        return "keyword_only"

    if choice == "3":
        return "semantic_only"

    return "hybrid"


if __name__ == "__main__":
    print(f"{_import_elapsed:.2f}s")

    # Load the semantic model once before the search loop
    from database.semantic_search import _load as _load_semantic_model
    _load_semantic_model()

    print(
        "Ready. Type a query and press Enter "
        "(blank line or 'quit' to exit).\n"
    )

    while True:
        # Read the next search query
        query = input("Search: ").strip()

        if not query or query.lower() in ("quit", "exit"):
            print("Bye.")
            break

        mode = choose_mode()

        extension = input(
            "File extension (example: .pdf; press Enter for all): "
        ).strip()

        if not extension:
            extension = None

        # Run the search and time it
        started = time.time()
        results = hybrid_search(query, mode=mode, extension=extension)
        elapsed = time.time() - started

        print_results(results, elapsed)
        print()