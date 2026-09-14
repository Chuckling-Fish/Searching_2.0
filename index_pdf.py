from pathlib import Path
from database.database import init_db
from database.indexing import metadata_extractor
from pdf.pdf_chunker import extract_document, create_chunks
from database.data_insertion import add_file, add_chunks, delete_chunks_for_file

def index_pdf(pdf_path):
    pdf_path = str(Path(pdf_path).resolve())

    # 1. Store file metadata, get its id
    file_data = metadata_extractor(pdf_path)
    file_id = add_file(file_data)

    # 2. Clear any chunks from a previous run of this file, so re-indexing doesn't leave stale/duplicate chunks
    delete_chunks_for_file(file_id)
     
    # 3. Extract blocks and build chunks
    blocks = extract_document(pdf_path)
    chunks = create_chunks(blocks)

    # 4. Store chunks
    add_chunks(file_id, chunks)
    print(f"Indexed '{pdf_path}': {len(chunks)} chunks")
    return file_id

if __name__ == "__main__":
    init_db()
    index_pdf("C:/Users/Anjum/Downloads/Telegram Desktop/Social_Stratification.pdf")