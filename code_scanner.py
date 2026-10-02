from pathlib import Path
import sys

from core.code_indexer import CodeIndexer


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".sh",
    ".bash",
    ".sql",
    ".html",
    ".css",
    ".scss",
    ".vue",
    ".dart",
    ".r",
    ".lua",
    ".pl",
    ".ex",
    ".exs",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".toml",
    ".ini",
    ".md",
}


SKIP_DIRECTORIES = {
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".idea",
    ".vscode",
    "build",
    "dist",
}


def scan_code_folder(folder_path):
    folder = Path(folder_path).expanduser().resolve()

    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    if not folder.is_dir():
        raise NotADirectoryError(f"Not a folder: {folder}")

    indexer = CodeIndexer()

    files_found = 0
    files_indexed = 0
    chunks_indexed = 0
    files_failed = 0

    print(f"\nScanning code folder: {folder}\n")

    for file_path in folder.rglob("*"):

        if not file_path.is_file():
            continue

        if any(
            part in SKIP_DIRECTORIES
            for part in file_path.parts
        ):
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        files_found += 1

        try:
            chunks = indexer.index_file(file_path)

            files_indexed += 1
            chunks_indexed += len(chunks)

            print(
                f"Indexed: {file_path} "
                f"({len(chunks)} chunks)"
            )

        except Exception as error:
            files_failed += 1

            print(
                f"FAILED: {file_path}\n"
                f"Reason: {error}"
            )

    print("\n========== CODE SCAN COMPLETE ==========")
    print(f"Code files found:    {files_found}")
    print(f"Code files indexed:  {files_indexed}")
    print(f"Code chunks created: {chunks_indexed}")
    print(f"Files failed:        {files_failed}")


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python code_scanner.py <folder_path>"
        )
        sys.exit(1)

    scan_code_folder(sys.argv[1])