import hashlib
import re
from pathlib import Path

HASH_SAMPLE_BYTES = 65536

def tokenize_filename(name):
    path = Path(name)
    stem = path.stem
    suffix = path.suffix.lstrip(".")

    # Split camelCase words
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)

    # Replace filename separators
    text = re.sub(r"[_\-.]+", " ", text)
    tokens = text.split()

    # Include the extension as a searchable token
    if suffix:
        tokens.append(suffix)
    return " ".join(tokens).lower()

def metadata_extractor(file_path):
    file = Path(file_path)
    info = file.stat()

    # Collect file metadata
    metadata = {
        "name": file.name,
        "extension": file.suffix,
        "path": str(file.resolve()),
        "parent": str(file.parent),
        "size": info.st_size,
        "created": info.st_ctime,
        "last_modified": info.st_mtime,
        "last_accessed": info.st_atime,
        "is_file": file.is_file(),
        "name_tokens": tokenize_filename(file.name),
    }
    return metadata

def quick_hash(file_path):
    file = Path(file_path)
    hasher = hashlib.sha256()

    # Hash size and the first 64 KB
    hasher.update(str(file.stat().st_size).encode())

    with open(file, "rb") as f:
        hasher.update(f.read(HASH_SAMPLE_BYTES))

    return hasher.hexdigest()

if __name__ == "__main__":
    print(metadata_extractor(__file__))