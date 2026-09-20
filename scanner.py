import sys
import time
from pathlib import Path

from database.database import init_db
from database.indexing import metadata_extractor, quick_hash
from database.data_insertion import (
    scan_connection,
    get_indexed_files,
    add_file,
    add_chunks,
    delete_chunks_for_file,
    delete_file,
)
from pdf.pdf_chunker import extract_document, create_chunks

# -----------------------------------------------------------
# Extensions with a working content extractor. Everything else
# still gets indexed for filename search (see scan_folder) - just
# with no chunks. Add a new extension here (and to extract_chunks
# below) once its extractor is ready; nothing else in the scan
# loop needs to change.
# -----------------------------------------------------------

CONTENT_SUPPORTED_EXTENSIONS = {".pdf"}

SKIP_DIRECTORIES = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__",
    "venv", ".venv", "env",
    ".idea", ".vscode",
    "build", "dist",
}

# A single enormous file can stall an entire scan.
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB

COMMIT_EVERY = 50


def should_skip_directory(path):
    return any(part in SKIP_DIRECTORIES or part.startswith(".")
               for part in path.parts)


def find_files(folder):
    """
    Walk the folder and yield every real, readable file - regardless
    of extension. Filename search covers all file types, so nothing
    is filtered out by type here; scan_folder decides per-file
    whether content extraction also applies. Junk directories, hidden
    files, empty files, and oversized files are still skipped, since
    those are hygiene filters rather than content-type filters.
    """

    folder = Path(folder)

    for path in folder.rglob("*"):
        if not path.is_file():
            continue

        if should_skip_directory(path.relative_to(folder).parent):
            continue

        if path.name.startswith("."):
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size == 0 or size > MAX_FILE_SIZE:
            continue

        yield path


def needs_reindex(path, metadata, known):
    """
    Three-tier change detection:

      1. Not in the database at all      -> index it
      2. size AND mtime both unchanged   -> skip without opening the file
      3. something looks different       -> hash to confirm

    Tier 2 is where nearly all the speed comes from: on a re-scan, an
    unchanged file costs one stat() call and a dict lookup, and is never
    opened, parsed, or hashed.

    Tier 3 exists because mtime can lie (restored backups, copied files,
    clock changes). Hashing only the files that already look changed
    keeps that safety without paying the read cost on every file.
    """

    key = metadata["path"]

    if key not in known:
        # Hash on first index too, so later scans have a baseline to
        # compare against. Without this, the tier-3 tiebreaker below
        # has nothing to check and any mtime change forces a full
        # re-index even when the content is untouched.
        return True, quick_hash(path)

    old_size, old_mtime, old_hash = known[key]

    if old_size == metadata["size"] and old_mtime == metadata["last_modified"]:
        return False, old_hash

    new_hash = quick_hash(path)

    if old_hash is not None and new_hash == old_hash:
        # Metadata shifted but content is the same - refresh the stored
        # metadata, but don't re-extract or re-chunk.
        return False, new_hash

    return True, new_hash


def extract_chunks(path):
    """
    Dispatch point for per-filetype extraction. Add code/text handling
    here when those extractors are ready.
    """

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        blocks = extract_document(str(path))
        return create_chunks(blocks)

    raise ValueError(f"No extractor for {suffix}")


def scan_folder(folder, verbose=True):
    folder = Path(folder).resolve()

    if not folder.is_dir():
        print(f"Not a folder: {folder}")
        return

    init_db()

    started = time.time()

    stats = {"indexed": 0, "filename_only": 0, "skipped": 0, "removed": 0, "failed": 0}

    with scan_connection() as connection:
        known = get_indexed_files(connection)
        seen_paths = set()

        pending = 0

        for path in find_files(folder):
            try:
                metadata = metadata_extractor(str(path))
            except OSError:
                stats["failed"] += 1
                continue

            seen_paths.add(metadata["path"])

            extension = path.suffix.lower()
            content_supported = extension in CONTENT_SUPPORTED_EXTENSIONS

            if not content_supported:
                # Filename-only file (image, video, archive, etc): no
                # extraction to guard against, so just check whether
                # the cheap metadata actually changed before writing.
                old = known.get(metadata["path"])
                if old and old[0] == metadata["size"] and old[1] == metadata["last_modified"]:
                    stats["skipped"] += 1
                    continue

                add_file(metadata, file_hash=None, content_indexed=0, connection=connection)
                stats["filename_only"] += 1
                pending += 1

                if pending >= COMMIT_EVERY:
                    connection.commit()
                    pending = 0

                continue

            reindex, file_hash = needs_reindex(path, metadata, known)

            if not reindex:
                # Metadata may still have shifted (e.g. mtime changed but
                # content didn't), so refresh the row - it's one cheap
                # UPDATE with no extraction behind it.
                add_file(metadata, file_hash, content_indexed=1, connection=connection)
                stats["skipped"] += 1
                continue

            try:
                chunks = extract_chunks(path)
            except Exception as error:
                stats["failed"] += 1
                if verbose:
                    print(f"  FAILED {path.name}: {error}")
                continue

            file_id = add_file(metadata, file_hash, content_indexed=1, connection=connection)
            delete_chunks_for_file(file_id, connection)
            add_chunks(file_id, chunks, connection)

            stats["indexed"] += 1
            pending += 1

            if verbose:
                print(f"  indexed {path.name} ({len(chunks)} chunks)")

            if pending >= COMMIT_EVERY:
                connection.commit()
                pending = 0

        # ---------------------------------------------------
        # Files that are in the database but no longer on disk.
        # Only paths under the folder being scanned are removed,
        # so scanning one folder never deletes another folder's
        # entries.
        # ---------------------------------------------------

        for known_path in known:
            if known_path in seen_paths:
                continue

            if Path(known_path).is_relative_to(folder) and not Path(known_path).exists():
                delete_file(known_path, connection)
                stats["removed"] += 1

                if verbose:
                    print(f"  removed {Path(known_path).name} (deleted from disk)")

    elapsed = time.time() - started

    print(
        f"\nScan complete in {elapsed:.2f}s - "
        f"{stats['indexed']} indexed, {stats['filename_only']} filename-only, "
        f"{stats['skipped']} unchanged, {stats['removed']} removed, {stats['failed']} failed"
    )

    if stats["indexed"] or stats["removed"]:
        print("Run build_semantic_index.py to refresh the vector index.")

    return stats


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else input("Folder to index: ")
    scan_folder(target)
