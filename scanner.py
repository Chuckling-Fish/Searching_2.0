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

CONTENT_SUPPORTED_EXTENSIONS = {".pdf"}

SKIP_DIRECTORIES = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__",
    "venv", ".venv", "env",
    ".idea", ".vscode",
    "build", "dist",
}

MAX_FILE_SIZE = 200 * 1024 * 1024

# Commit after x changes
COMMIT_EVERY = 50

# Check for excluded or hidden directories
def should_skip_directory(path):
    return any(part in SKIP_DIRECTORIES or part.startswith(".") for part in path.parts)

def find_files(folder):
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


def needs_reindex(path, metadata, known, force=False):
    key = metadata["path"]

    # Force mode
    if force:
        return True, quick_hash(path)

    # New files always need indexing
    if key not in known:
        return True, quick_hash(path)

    old_size, old_mtime, old_hash = known[key]

    if old_size == metadata["size"] and old_mtime == metadata["last_modified"]:
        return False, old_hash

    # Hash check avoids reindexing unchanged content
    new_hash = quick_hash(path)

    if old_hash is not None and new_hash == old_hash:
        return False, new_hash
    return True, new_hash


def extract_chunks(path):
    suffix = path.suffix.lower()

    # Extract and chunk PDF content
    if suffix == ".pdf":
        blocks = extract_document(str(path))
        return create_chunks(blocks)
    raise ValueError(f"No extractor for {suffix}")

def scan_folder(folder, verbose=True, force=False):
    folder = Path(folder).resolve()
    if not folder.is_dir():
        print(f"Not a folder: {folder}")
        return

    init_db()
    started = time.time()
    stats = {"indexed": 0, "filename_only": 0, "skipped": 0, "removed": 0, "failed": 0}

    if force and verbose:
        print("Force mode: re-chunking every content-supported file, ignoring change detection.\n")

    # Load existing indexed files
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

            # Check whether the PDF needs reindexing
            reindex, file_hash = needs_reindex(path, metadata, known, force=force)

            if not reindex:
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

            # Periodically save database changes
            if pending >= COMMIT_EVERY:
                connection.commit()
                pending = 0

        # Remove files that no longer exist
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
    args = [a for a in sys.argv[1:] if a != "--force"]
    force = "--force" in sys.argv[1:]

    target = args[0] if args else input("Folder to index: ")
    scan_folder(target, force=force)
