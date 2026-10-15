# File Indexing and Search System
A command-line tool that indexes local **PDF documents** and **source-code files**, then searches them by keyword, by meaning (semantic search), or both. Indexes are stored on your machine. The only network access is a one-time download of the embedding model (see [Offline use](#offline-use)).

> **Status: prototype.** Both pipelines work end to end for the inputs listed below, but several behaviors can surprise you. Read [Known limitations](#known-limitations) before relying on results.

## Contents
[Overview](#overview) · [Requirements](#requirements) · [Offline use](#offline-use) · [Quick start](#quick-start) · [Document search](#document-search-pdf) · [Code search](#code-search) · [Files and privacy](#files-created-and-privacy) · [Known limitations](#known-limitations) · [Troubleshooting](#troubleshooting) · [Project structure](#project-structure) · [Development notes](#development-notes) · [License](#license)

## Overview
| | Document search | Code search |
|---|---|---|
| Content searched | Text of **PDF** files | Functions, methods and classes in **Python, C++ and Java** files |
| Other files | Searchable by **filename only** (any file type) | Not indexed |
| Keyword search | SQLite FTS5, BM25 ranking | SQLite FTS5, BM25 ranking |
| Semantic search | `all-MiniLM-L6-v2` embeddings in an HNSWlib index (cosine) | Same model and library |
| Hybrid search | Reciprocal Rank Fusion (K = 60) of keyword and semantic results | Same |
| Extras | Filename matches shown next to content matches | Behavior descriptions (C++ only); optional "Analyze output" (C++ only, **runs code**) |

The two components are independent: separate databases, separate scan commands, separate search commands. One shared script, `database/build_semantic_index.py`, builds the vector indexes for both.

## Requirements
- Python 3.9 or newer
- Dependencies: `pip install -r libraries.txt`. The code imports `pymupdf` (PyMuPDF), `sentence-transformers`, `hnswlib`, `tree-sitter`, `tree-sitter-python`, `tree-sitter-cpp` and `tree-sitter-java`. `sentence-transformers` installs PyTorch, which is a large download.
- `g++` on your `PATH`, **only** for the optional "Analyze output" feature.

## Offline use
The embedding model `all-MiniLM-L6-v2` is loaded from the local Hugging Face cache if it is already there. Otherwise it is downloaded on first use, which needs an internet connection. Once the model is cached, nothing else in the project needs the network. To guarantee nothing is fetched, set `HF_HUB_OFFLINE=1` after the first successful run.

## Quick start
Run every command **from the repository root** (`Searching_2.0/`). The code database path is relative to the working directory, so running from elsewhere breaks code search.

**Documents**
```bash
python scanner.py "<folder>"
python -m database.build_semantic_index
python -m database.hybrid_search
```

**Code**
```bash
python code_scanner.py "<folder>"
python -m database.build_semantic_index
python prototype_cli.py
```

If you use both, scan both folders first, then run `build_semantic_index` once.

## Document search (PDF)

### 1. Scan a folder

```bash
python scanner.py "<folder>" [--force]
```

If no folder is given, the script prompts for one.

- The folder is walked recursively. Skipped: subdirectories named `.git`, `.svn`, `.hg`, `node_modules`, `__pycache__`, `venv`, `.venv`, `env`, `.idea`, `.vscode`, `build` or `dist`; any hidden file or directory (name starts with `.`); empty files; files over 200 MB.
- **PDF files** are chunked and their text is stored in `database/index.db`.
- **All other files** are stored by filename and metadata only.
- Re-running is incremental. A file is skipped if its size and modification time are unchanged. If the modification time changed, a hash of the file size and first 64 KB decides whether it is re-chunked. Files deleted from disk are removed from the index (only files under the scanned folder). `--force` re-chunks every PDF.
- The scan prints a summary: indexed, filename-only, unchanged, removed, failed. A PDF that yields no text (for example a scanned image) is still counted as "indexed". Look for `(0 chunks)` in the per-file lines.
- **Scanning does not update the semantic index.** Rebuild it (step 2) after any scan that changed files.

#### How PDFs are processed

- Each text block is classified as heading, paragraph, list item or noise using layout heuristics: font size relative to the page's median, bold, spacing, numbering, and text length. Noise includes page numbers, URLs, symbol-only blocks, very small text, and text in the top or bottom 5% of a page.
- Text after a line reading "Contents" or "Table of Contents" is skipped until a numbered heading (`1. Title` or `1.2 Title`) appears. See [Known limitations](#known-limitations).
- Chunks close at roughly 180 words with roughly 40 words of overlap. Overlap is not carried across headings. Each chunk stores its heading, its section path (`Chapter > Section`) and its page range.
- There is no OCR. PDFs without a text layer produce no chunks.

#### Optional: watch a folder

```bash
python poll_watcher.py "<folder>" [interval_seconds]   # default: 5
```

Re-runs the scanner on an interval. It updates the keyword and filename indexes only; rebuild the semantic index manually. Every pass walks the whole folder and rewrites a metadata row for every file, so use a longer interval for large folders.

### 2. Build the semantic index

```bash
python -m database.build_semantic_index
```

Embeds every PDF chunk (section path + text) and writes `database/vector_index.bin`. It also builds the code index (see [Code search](#code-search)). Each run rebuilds from scratch. Whichever database is empty is skipped with a message. If that message says to run `index_pdf.py`, ignore it and run `scanner.py` instead.

### 3. Search

```bash
python -m database.hybrid_search
```

After a startup delay (the model loads) the tool prompts for:

1. **Query**: a blank line, `quit` or `exit` leaves the program.
2. **Mode**: `1` Hybrid (default), `2` Keyword, `3` Semantic.
3. **Extension**: for example `.pdf`, or Enter for all. The match is exact and case-sensitive against the stored extension.

Output:

- Up to **10 content matches**: file, heading, page range and a preview. These are *chunks*, so one file can appear several times. A `[name also matches]` marker shows when the filename also matched.
- Up to **10 filename matches**. Filename search covers every indexed file type, not only PDFs.

How matching works:

- **Keyword:** the query is split into words; every word must appear in the same chunk, in any order. This is not an exact-phrase search. There is no stemming, so `stratified` does not match `stratification`.
- **Semantic:** the query is embedded and compared with chunk embeddings by cosine similarity.
- **Hybrid:** the top 20 keyword and top 20 semantic candidates are merged with Reciprocal Rank Fusion, and the best 10 are shown.
- **Filenames:** names are split on case changes and on `_`, `-`, `.`; the extension is its own token, so searching `pdf` lists PDF files. All query words must match.

## Code search

### 1. Scan a code folder

```bash
python code_scanner.py "<folder>"
```

- **Parsed languages:** Python (`.py`, `.pyw`), C++ (`.cpp`, `.cc`, `.cxx`, `.hpp`), Java (`.java`).
- The scanner also accepts other extensions (for example `.c`, `.h`, `.js`, `.json`), but it cannot parse them. They are counted as **failed** in the summary. C and `.h` files are not supported.
- Code is parsed with tree-sitter and split into chunks:
  - Python: functions, classes
  - C++: functions, classes, structs, namespaces
  - Java: methods, constructors, classes, interfaces, enums
- For **C++ functions**, a plain-language behavior description is generated and indexed alongside the code (see below).
- Keyword data is stored in `database/code_search.db` (SQLite FTS5). The summary reports files found, files indexed, chunks created and files failed.
- Re-running re-parses every file and replaces its chunks. There is no change detection, and **files deleted from disk stay in the index** until you delete `database/code_search.db` and rescan.
- **Path caution:** the skip check looks at the *absolute* path. If the folder you scan is inside a directory named `.git`, `.svn`, `.hg`, `node_modules`, `__pycache__`, `venv`, `.venv`, `env`, `.idea`, `.vscode`, `build` or `dist`, **every file is skipped**. Hidden directories not in that list are not skipped.

### 2. Build the semantic index

```bash
python -m database.build_semantic_index
```

Embeds each code chunk (path, language, type, name, behavior, code) and writes `database/code_vector_index.bin`. Build it before starting the search CLI: the CLI initializes the semantic index at startup, even in keyword mode.

### 3. Search

```bash
python prototype_cli.py
```

Prompts: **query** (`exit` or `quit` leaves), **mode** (`1` Hybrid default, `2` Keyword, `3` Semantic), and an optional **extension** (`.py`, `.cpp`, `.java`; include the dot). The CLI returns the top **5** results with file, function or class name, language, directory and line range.

- **Keyword:** every query word must match somewhere in the file path, name, code or behavior text. camelCase identifiers are not split, so `binary search` will not match `binarySearch`.
- **Semantic and hybrid:** the extension filter is applied *after* the top candidates are retrieved, so a rare extension can return few or no results.

Select a result to open its actions:
```
[1] Show code
[2] Behavior
[3] Analyze output
[4] Back
```

| Action | What it does |
|---|---|
| Show code | Prints the chunk. |
| Behavior | Prints the generated description. **C++ functions only**; empty for Python and Java. |
| Analyze output | **C++ only.** Compiles and runs the *whole source file* and shows status, output, errors and return code. |
| Back | Returns to the result list. |

Behavior descriptions list the function name, parameter names, and any of: returns a result; addition, subtraction, multiplication, division, modulo; comparisons; `cout` output; `for`/`while`/`do` loops; `if`/`switch`. Anything else is not described.

An alternative listing-only CLI is available: `python -m database.code_hybrid_search` (hybrid mode, top 10, no inspection menu).

> **"Analyze output" executes code on your machine.**
> - Run it only on code you trust. The program has your user's full file and network access. The only protection is a 3-second limit on compilation and a separate 3-second limit on execution. There is no memory limit and no sandbox.
> - `g++` must be installed. If it is missing, the CLI crashes with `FileNotFoundError`.
> - It compiles with `g++ -std=c++17 -O0`. Only the single file is copied to a temporary directory, so files that `#include` local headers may fail to compile.
> - Input is read as lines until you enter an empty line.

## Files created and privacy
| File | Contents |
|---|---|
| `database/index.db` (+ `-wal`, `-shm` while in use) | Document metadata (absolute paths, sizes, timestamps, hashes), filename tokens, and the **full text of every indexed PDF chunk** |
| `database/vector_index.bin` | Document chunk embeddings |
| `database/code_search.db` | **Full source code** of every indexed chunk, with behavior text |
| `database/code_vector_index.bin` | Code chunk embeddings |

Everything is stored locally in plaintext and unencrypted. Do not commit or share these files if your documents or code are private.

## Known limitations

**General**
- The semantic index is a snapshot, rebuilt from scratch on every run. After a scan that adds, changes or removes files, rebuild it. Until you do, semantic and hybrid results can be missing or point to the wrong chunk.
- Keyword search requires all query words in the same chunk. There is no phrase search, stemming or typo tolerance.
- The embedding model reads only about the first 256 tokens of each chunk, so long chunks are only partly represented.
- Run commands from the repository root.
- The code database path is relative to the working directory; the document database path is not.

**Documents**
- PDFs only (no OCR). Scanned PDFs yield nothing but still count as "indexed".
- **Silent text loss after "Contents":** once a line reading "Contents" or "Table of Contents" is seen, all text is skipped until a numbered heading in the form `1. Title` or `1.2 Title` is detected. Documents with unnumbered headings or `1 Title` style headings can lose most of their text after that line.
- Multi-column pages are read top-to-bottom by block position, so columns can interleave.
- Heading and noise detection uses fixed heuristics, with font and spacing statistics computed per page. Headings can be misclassified, footnotes (small text near the bottom) may be dropped as noise, and text running headers and footers may be kept. Table and figure structure is lost.
- Paragraphs are never split, so a chunk can exceed 180 words. Overlap text can occasionally be saved as an extra duplicate chunk at a section boundary or at the end of a document.
- Results are chunks, so one file can fill several of the 10 slots.
- The extension filter is exact and case-sensitive: `.pdf` does not match a file stored as `.PDF`.
- Change detection can miss an edit that keeps the file size, leaves the first 64 KB unchanged, and changes only later bytes.

**Code**
- Only Python, C++ and Java are parsed (see the list above).
- Chunks nest: a class chunk contains its methods' code, and a C++ namespace chunk can contain most of a file. Similar results can appear more than once.
- Not indexed: Python statements outside functions and classes, and any construct not listed under Code search. A file with none of the indexed constructs is not searchable by content.
- Some C++ constructs, such as destructors and operator overloads, may be indexed without a name.
- Behavior descriptions exist only for C++ functions and cover only the constructs listed above.
- Re-scans re-parse everything, and deleted files remain searchable until the database is deleted.

## Troubleshooting
| Symptom | Cause | Fix |
|---|---|---|
| `No module named 'database'` | A script inside `database/` was run directly | Run from the repo root with `python -m database.<module>` |
| `unable to open database file` during code scan or search | Not in the repo root | `cd` to the repo root |
| `No PDF chunks found ... run index_pdf.py first` | Outdated message | Run `scanner.py` first |
| Code scan says 0 files found | A parent directory of the scanned path has a skipped name (`build`, `env`, `dist`, ...) | Copy the code elsewhere or rename the parent |
| `Files failed: N` with "Unsupported file type" | The scanner accepts extensions it cannot parse | Expected; only the 7 supported extensions are indexed |
| Keyword search returns nothing | All words must appear in one chunk | Use fewer words, or semantic or hybrid mode |
| Wrong or missing semantic results after a rescan | The vector index is stale | Rerun `python -m database.build_semantic_index` |
| Code search fails at startup | The code vector index has not been built | Run `build_semantic_index` first |
| `FileNotFoundError` in "Analyze output" | `g++` is not installed or not on `PATH` | Install `g++` and add it to `PATH` |
| A PDF shows `(0 chunks)` | No text layer (scanned) | OCR the PDF first |

## Project structure
| Path | Purpose |
|---|---|
| `scanner.py` | Document and filename indexer (`--force` supported) |
| `poll_watcher.py` | Re-runs the scanner on an interval |
| `code_scanner.py` | Code indexer |
| `prototype_cli.py` | Code search CLI |
| `index_pdf.py` | Legacy single-PDF indexer with a hardcoded sample path. Superseded by `scanner.py` |
| `pdf/pdf_extractor.py` | Extracts text blocks from PDF pages and classifies them |
| `pdf/scoring.py` | Heading and noise scoring heuristics |
| `pdf/pdf_chunker.py` | Builds heading-aware chunks |
| `core/language_registry.py` | Supported languages and extensions |
| `core/parser_manager.py` | tree-sitter parsers |
| `core/code_chunker.py` | Splits parsed code into chunks |
| `core/code_indexer.py` | Parses, analyzes and stores a code file |
| `core/code_search.py` | Empty file |
| `analysis/behavior_analyzer.py` | C++ behavior descriptions |
| `analysis/code_output_analyzer.py` | Compiles and runs C++ ("Analyze output") |
| `database/database.py` | Document database schema |
| `database/data_insertion.py` | Document database writes |
| `database/indexing.py` | File metadata, filename tokens, quick hash |
| `database/search.py` | Document keyword search |
| `database/filename_search.py` | Filename search |
| `database/semantic_search.py` | Document semantic search |
| `database/hybrid_search.py` | Document search CLI |
| `database/build_semantic_index.py` | Builds both vector indexes |
| `database/code_database.py` | Code database |
| `database/code_search.py` | Code keyword search |
| `database/code_hybrid_search.py` | Code hybrid search |
| `search/semantic_search.py` | Code semantic search |
| `tests/`, `TestFiles/` | Tests and sample inputs |

## License
No license has been specified.
