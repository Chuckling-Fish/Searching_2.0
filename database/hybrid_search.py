import time

_import_started = time.time()

from search import keyword_search
from semantic_search import semantic_search
from filename_search import filename_search

_import_elapsed = time.time() - _import_started

# RRF constant for rank weighting
RRF_K = 60

def reciprocal_rank_fusion(result_lists, id_key):
    combined = {}
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

    if len(text) > max_chars:
        return text[:max_chars].rsplit(" ", 1)[0] + " ..."

    return text

def print_results(results, elapsed):
    print(f"{elapsed:.2f}s\n")

    print("=== Content matches ===")

    for i, r in enumerate(results["content"], start=1):
        marker = " [name also matches]" if r.get("name_also_matches") else ""
        heading = r.get("heading") or "(no heading)"
        pages = (
            f"p.{r['page_start']}-{r['page_end']}"
            if r.get("page_start")
            else ""
        )

        print(f"\n{i}. {r['file_name']}{marker}")
        print(f"   {heading}  {pages}")
        print(f"   {get_preview(r)}")

    print("\n=== Filename matches ===")

    for i, r in enumerate(results["filenames"], start=1):
        print(f"{i}. {r['file_name']}  ({r['file_path']})")


if __name__ == "__main__":
    print(f"{_import_elapsed:.2f}s")

    from semantic_search import _load as _load_semantic_model
    _load_semantic_model()

    print(
        "Ready. Type a query and press Enter "
        "(blank line or 'quit' to exit).\n"
    )

    while True:
        query = input("Search: ").strip()

        if not query or query.lower() in ("quit", "exit"):
            print("Bye.")
            break

        started = time.time()
        results = hybrid_search(query)
        elapsed = time.time() - started

        print_results(results, elapsed)
        print()