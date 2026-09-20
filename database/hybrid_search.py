import time
_import_started = time.time()

from search import keyword_search
from semantic_search import semantic_search
from filename_search import filename_search

_import_elapsed = time.time() - _import_started

# Standard constant from the original RRF paper (Cormack et al.) - not
# sensitive to tuning, 60 is the conventional default almost everyone uses.
RRF_K = 60


def reciprocal_rank_fusion(result_lists, id_key):
    """
    Combines multiple ranked lists into one, using each item's RANK
    POSITION in its own list rather than its raw score.

    This matters because bm25 (from keyword_search) and cosine distance
    (from semantic_search) are not on comparable scales - one is
    unbounded and more-negative-is-better, the other is bounded 0-2
    and lower-is-better. Averaging or adding them directly would be
    meaningless. Rank position sidesteps that entirely: "how good was
    this result relative to everything else in the SAME list" is
    comparable across lists even when the underlying scores aren't.

    An item that appears in both lists accumulates score from both,
    so it naturally rises above items that only one method found.
    """

    combined = {}

    for results in result_lists:
        for rank, result in enumerate(results, start=1):
            key = result[id_key]

            if key not in combined:
                combined[key] = {"result": result, "rrf_score": 0.0}

            combined[key]["rrf_score"] += 1.0 / (RRF_K + rank)

    fused = sorted(
        combined.values(),
        key=lambda entry: entry["rrf_score"],
        reverse=True  # higher combined score = better, unlike bm25/cosine
    )

    return [
        {**entry["result"], "rrf_score": entry["rrf_score"]}
        for entry in fused
    ]


def hybrid_search(query, mode="hybrid", extension=None, limit=10):
    """
    mode:
      "hybrid"        - keyword + semantic, fused with RRF (default)
      "keyword_only"  - pure FTS5, for when the user wants exact-word
                         matching only (e.g. a UI toggle)
      "semantic_only" - pure vector search

    Filename matches are always returned as a SEPARATE group, never
    fused into the content ranking - a filename match and a content
    match aren't measuring the same thing, and most filename-only
    files (images, archives, ...) have no content score to fuse with
    in the first place. Instead, a content result gets flagged
    `name_also_matches: True` when its file's name also matched -
    a cheap, cheap-to-reason-about signal rather than a real fusion.
    """

    if mode == "keyword_only":
        content_results = keyword_search(query, extension=extension, limit=limit)
    elif mode == "semantic_only":
        content_results = semantic_search(query, extension=extension, limit=limit)
    elif mode == "hybrid":
        # Over-fetch a bit before fusing/trimming, so RRF has enough
        # material from each side to produce a meaningful combined order.
        keyword_results = keyword_search(query, extension=extension, limit=limit * 2)
        semantic_results = semantic_search(query, extension=extension, limit=limit * 2)

        content_results = reciprocal_rank_fusion(
            [keyword_results, semantic_results],
            id_key="chunk_id"
        )[:limit]
    else:
        raise ValueError(f"Unknown mode: {mode!r}")

    filename_results = filename_search(query, extension=extension, limit=limit)
    filename_file_ids = {result["file_id"] for result in filename_results}

    for result in content_results:
        result["name_also_matches"] = result.get("file_id") in filename_file_ids

    return {
        "content": content_results,
        "filenames": filename_results,
    }


def get_preview(result, max_chars=600):
    """
    Normalizes the two different shapes a content result can have:
    - from keyword_search: a 'snippet' field (FTS5-highlighted excerpt)
    - from semantic_search: a 'text' field (full chunk text, no
      highlighting, since semantic matches don't correspond to
      specific literal words to highlight)
    """

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
        pages = f"p.{r['page_start']}-{r['page_end']}" if r.get("page_start") else ""

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

    print("Ready. Type a query and press Enter (blank line or 'quit' to exit).\n")

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