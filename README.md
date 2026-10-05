# File Indexing and Search System
Index your PDFs and search them by keyword, for now.

## Setup
```
pip install -r libraries.txt
```

## 1. Index a file
Open `index_pdf.py` and set the path to the PDF you want to search, at the bottom:
```python
if __name__ == "__main__":
    init_db()
    index_pdf("C:/path/to/your/file.pdf")
```

Then run it:
```
python index_pdf.py
```

This extracts the text, splits it into chunks and stores everything in `database/index.db`. Re-running it on the same file updates it instead of duplicating it.

## 2. Search
**Keyword search** (exact words/phrases):
```
cd database
python search.py your search terms here
```

Use keyword search when you know the exact wording you're looking for.


## 3. Code File Indexing and Search

The code-search part of the system allows you to search source-code files by keyword, semantic meaning, or a combination of both.

### Supported Languages

- C++
- Python
- Java

### 3.1 Scan a Code Directory

To scan a directory containing source-code files, run:

```bash
python code_scanner.py "/path/to/your/folder"
```

For example:

```bash
python code_scanner.py "/Users/saraarpa/Desktop/DSA copy"
```

The scanner recursively searches the selected directory, detects supported programming languages, parses the source code, and divides it into searchable code chunks such as functions and classes.

The keyword index is stored locally in:

```text
database/code_search.db
```

The scanner also reports the number of files found, successfully indexed files, code chunks created, and failed files.

### 3.2 Build the Code Semantic Index

After scanning the code directory, build the semantic index:

```bash
python -m database.build_semantic_index
```

This creates vector embeddings for the indexed code chunks using the `all-MiniLM-L6-v2` model.

The generated vector index is stored locally as:

```text
database/code_vector_index.bin
```

The semantic index allows the system to search code by meaning rather than requiring an exact keyword match.

### 3.3 Search Code

Start the code-search prototype with:

```bash
python prototype_cli.py
```

The program provides three search modes:

1. **Hybrid** — combines keyword and semantic search.
2. **Keyword** — searches matching terms in file paths, names, source code, and behavior descriptions.
3. **Semantic** — searches for code with similar meaning using vector embeddings.

You can also filter results by file extension, such as:

```text
.cpp
.py
.java
```

or leave the field empty to search all supported code files.

### 3.4 Inspect Search Results

After selecting a result, the prototype provides:

```text
[1] Show code
[2] Behavior
[3] Analyze output
[4] Back
```

**Show code** displays the indexed code chunk and its file, language, type, name, and line range.

**Behavior** displays detected characteristics such as loops, conditional logic, comparisons, arithmetic operations, console output, return statements, and function parameters.

**Analyze output** can compile and run supported C++ source files with user-provided input and display the program output or errors.

### 3.5 Code Search Workflow

```text
Code Folder
    ↓
code_scanner.py
    ↓
Parse & Extract Code Chunks
    ↓
SQLite + FTS5 Keyword Index
    ↓
database/code_search.db
    ↓
build_semantic_index.py
    ↓
Vector Embeddings
    ↓
database/code_vector_index.bin
    ↓
prototype_cli.py
    ↓
Keyword / Semantic / Hybrid Search
```

The PDF/document search and code-search components are separate parts of the overall project.
