import hashlib
import re
from pathlib import Path

# Only the first slice of a file is hashed. Reading a whole 200MB PDF
# just to notice it hasn't changed defeats the point of a cheap check -
# and this hash is only ever used as a tiebreaker after mtime/size
# already looked suspicious, never as the sole signal.
HASH_SAMPLE_BYTES = 65536


def tokenize_filename(name):
    """
    Turns a filename into space-separated search words, so FTS5's
    plain word-tokenizer can match "tree lab" against
    "tree_lab_final.cpp" or "myFileName.txt".

    FTS5 has no built-in awareness of camelCase or of underscores/
    hyphens/dots as word separators - by the time this string reaches
    FTS5, the splitting has already happened here.
    """

    path = Path(name)
    stem = path.stem
    suffix = path.suffix.lstrip(".")

    # camelCase -> camel Case (insert a space before an uppercase
    # letter that immediately follows a lowercase letter or digit)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", stem)

    # common filename separators -> spaces
    text = re.sub(r"[_\-.]+", " ", text)

    tokens = text.split()

    if suffix:
        tokens.append(suffix)

    return " ".join(tokens).lower()


def metadata_extractor(file_path):
    file = Path(file_path)
    info = file.stat()

    # NOTE: timestamps are stored as raw epoch floats, NOT formatted
    # date strings. Change detection compares these directly against
    # os.stat().st_mtime, so they must stay numeric - formatting them
    # would make every file look changed on every scan.
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
    """
    Hash of (file size + first HASH_SAMPLE_BYTES of content).
    Including the size means two files that share an identical opening
    chunk but differ in length still produce different hashes.
    """

    file = Path(file_path)
    hasher = hashlib.sha256()

    hasher.update(str(file.stat().st_size).encode())

    with open(file, "rb") as f:
        hasher.update(f.read(HASH_SAMPLE_BYTES))

    return hasher.hexdigest()


if __name__ == "__main__":
    print(metadata_extractor(__file__))
