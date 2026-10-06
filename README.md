# File Indexing and Search System
Index your PDFs, and search them by keyword and semantic meaning.

## Setup
After downloading the source code, assuming your are in the root directory(Searching_2.0 folder), simply run:
```
pip install -r libraries.txt
```

## 1. Scan a Directory & Build Keyword Index
To scan your directory for searching, run the `scanner.py` file, with a prompt that looks like:
```
python scanner.py drive:/folderlocation
```
Navigating to the root directory(Searching_2.0 folder) will let you use this exact prompt. Otherwise you will have to figure out how to access `scanner.py`.

Scanning extracts the texts from supported files, splits them into chunks and stores everything in `database/index.db`. Re-running it on the same file updates it instead of duplicating it.

Your keyword searching index is thus built.

This setp will take a few minutes, depending on how large the files in a directory are.


## 2. Build the Semantic Index
To build a semantic index, you need to run `build_semantic_index.py`. If you are already in the root directory, your prompt will be this:
```
python database/build_semantic_index.py
```
This will build a semantic index, embedded as vectors in `database/vector_index.bin`.

This step takes the most amount of time.


## 3. Search
To start the search, assuming you are in the root directory, your prompt will look like this:
```
python database/hybrid_search.py
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

The prototype provides three search modes:

1. **Hybrid** — combines keyword and semantic search.
2. **Keyword** — searches matching terms in file paths, names, source code, and behavior descriptions.
3. **Semantic** — searches for code with similar meaning using vector embeddings.

Results can also be filtered by file extension:

```text
.cpp
.py
.java
```

Leave the extension field empty to search all supported code files.

The search result list displays:

* File name
* Function/code name
* Language
* Directory
* Line range

### 3.4 Inspect Search Results

After selecting a search result, the prototype provides:

```text
[1] Show code
[2] Behavior
[3] Analyze output
[4] Back
```

**Show code** displays the selected code chunk.

**Behavior** displays detected characteristics such as:

* Loops
* Conditional logic
* Comparisons
* Arithmetic operations
* Console output
* Return statements
* Function parameters

**Analyze output** can compile and run the complete supported C++ source file using user-provided input. It displays:

* Execution status
* Program output
* Compilation/runtime errors
* Return code

**Back** returns to the search result list.

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
    ↓
Select Result
    ↓
Show Code / Behavior / Analyze Output
```

The PDF/document search and code-search components are separate parts of the overall project.
The program will import a few libraries and setup the environment for searching. 

After a small delay, you will be prompted to search. Type your search term and press Enter. You will be provided the 10 most relevant files, along with previews of the matched texts and their page numbers.

The program will keep running even after you enter your search term, prompting you again and again to search. You can quit by typing `quit` or `exit`, or by simply pressing `Enter`.

Enjoy!
The code-search component operates independently from the PDF/document search component.