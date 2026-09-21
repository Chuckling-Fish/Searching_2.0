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
To start the search, assuming you are in the root directory, your prompt wll look like this:
```
python database/hybrid_search.py
```

The program will import a few libraries and setup the environment for searching. 

After a small delay, you will be prompted to search. Type your search term and press Enter. You will be provided the 10 most relevant files, along with previews of the matched texts and their page numbers.

The program will keep running even after you enter your search term, prompting you again and again to search. You can quit by typing `quit` or `exit`, or by simply pressing `Enter`.

Enjoy!
