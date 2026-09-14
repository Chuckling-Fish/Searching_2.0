# File Indexing and Search System
Index your PDFs and search them by keyword, for now.

## Setup
```
pip install -r libraries.txt
```

## Folder structure
```
Searching_2.0/
├── database/
│   ├── database.py
│   ├── data_insertion.py
│   ├── indexing.py
│   ├── search.py              
│   └── index.db            (created automatically)
├── pdf/
│   ├── pdf_chunker.py
│   ├── pdf_extractor.py
│   └── scoring.py
└── index_pdf.py
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

## 3. Search
**Keyword search** (exact words/phrases):
```
cd database
python search.py your search terms here
```

Use keyword search when you know the exact wording you're looking for.