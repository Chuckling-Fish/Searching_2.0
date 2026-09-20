import pymupdf
import re

from pdf.pdf_extractor import process_page, is_numbered_heading

# PDF FILE
PDF_PATH = "C:/Users/Anjum/Downloads/Telegram Desktop/Social_Stratification.pdf"

# TEXT CLEANING
def clean_text(text):
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Remove common PDF bullet characters
        line = re.sub(r"[•●○▪▫]", "", line)
        # Normalize multiple spaces
        line = re.sub(r"\s+", " ", line)
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

# COUNT WORDS
def count_words(blocks):
    total_words = 0
    for block in blocks:
        text = clean_text(block["text"])
        total_words += len(text.split())
    return total_words

# CHECK FOR TABLE OF CONTENTS ENTRY
def is_toc_entry(text):
    text = text.strip()
    if re.search(r"\.{3,}", text):
        return True
    if re.search(r"\s{8,}\d+$", text):
        return True
    return False

# CHECK FOR TABLE OF CONTENTS TITLE
def is_toc_title(text):
    normalized = text.strip().lower()
    return normalized in (
        "table of contents",
        "contents"
    )

# DETERMINE NUMBERED HEADING LEVEL
def get_numbered_heading_level(text):
    text = text.strip()
    if re.match(
        r"^\d+\.\s+",
        text
    ):
        return 1
    if re.match(
        r"^\d+\.\d+\s+",
        text
    ):
        return 2
    if re.match(
        r"^\d+\.\d+\.\d+\s+",
        text
    ):
        return 3
    if re.match(
        r"^\d+\.\d+\.\d+\.\d+\s+",
        text
    ):
        return 4
    return None

# DETERMINE HEADING LEVEL
def determine_heading_level(
    block,
    current_section_level
):
    text = block["text"].strip()
    numbered_level = get_numbered_heading_level(text)
    if numbered_level is not None:
        return numbered_level

    if current_section_level is not None:
        return current_section_level + 1

    return 1

# UPDATE SECTION PATH
def update_section_path(
    section_path,
    heading,
    heading_level
):
    section_path = section_path[:heading_level - 1]
    section_path.append(heading)
    return section_path

# CREATE ONE CHUNK
def make_chunk(
    blocks,
    section_path
):
    text_parts = []
    for block in blocks:
        text = clean_text(
            block["text"]
        )
        if text:
            text_parts.append(text)
    text = "\n".join(text_parts)

    
    # Current heading
    if section_path:
        heading = section_path[-1]
    else:
        heading = None

    # Parent heading
    if len(section_path) >= 2:
        parent_heading = section_path[-2]
    else:
        parent_heading = None

    return {
        "page_start": blocks[0]["page"],
        "page_end": blocks[-1]["page"],
        "heading": heading,
        "parent_heading": parent_heading,
        "section_path": section_path.copy(),
        "text": text,
        "chunk_type": "text"
    }

# SAVE CURRENT CHUNK
def save_current_chunk(
    chunks,
    current_chunk,
    section_path
):
    if not current_chunk:
        return
    chunks.append(
        make_chunk(
            current_chunk,
            section_path
        )
    )

# CREATE CHUNKS
def create_chunks(
    blocks,
    max_words=250
):
    chunks = []
    current_chunk = []

    # Current document hierarchy
    section_path = []

    # Current known numbered section level
    current_section_level = None

    # TABLE OF CONTENTS STATE
    inside_toc = False
    for block in blocks:
        block_type = block["type"]
        text = clean_text(
            block["text"]
        )
                     
        # Ignore empty blocks              
        if not text:
            continue

        # Ignore extractor noise
        if block_type == "NOISE":
            continue

        # TABLE OF CONTENTS
        if is_toc_title(text):
            inside_toc = True
            continue

        # Ignore dotted TOC entries
        if inside_toc and is_toc_entry(text):
            continue
        if inside_toc:
            if (
                block_type == "HEADING"
                and is_numbered_heading(text)
                and not is_toc_entry(text)
            ):
                inside_toc = False
            else:
                continue

        # HEADING
        if block_type == "HEADING":
            # Save previous chunk
            save_current_chunk(
                chunks,
                current_chunk,
                section_path
            )
            current_chunk = []
            # Determine heading level
            heading_level = determine_heading_level(
                block,
                current_section_level
            )

            # Update hierarchy
            section_path = update_section_path(
                section_path,
                text,
                heading_level
            )
            numbered_level = get_numbered_heading_level(
                text
            )
            if numbered_level is not None:
                current_section_level = numbered_level
            continue

        # PARAGRAPH/LIST ITEM
        if block_type in (
            "PARAGRAPH",
            "LIST_ITEM"
        ):
            current_chunk.append(block)

            # Maximum chunk size
            if count_words(current_chunk) >= max_words:
                save_current_chunk(
                    chunks,
                    current_chunk,
                    section_path
                )
                current_chunk = []

     
    # SAVE FINAL CHUNK
    save_current_chunk(
        chunks,
        current_chunk,
        section_path
    )
    return chunks
   
# EXTRACT ENTIRE DOCUMENT
def extract_document(pdf_path):
    document = pymupdf.open(pdf_path)
    all_blocks = []
    for page_number, page in enumerate(
        document,
        start=1
    ):
        blocks = process_page(
            page,
            page_number
        )
        all_blocks.extend(blocks)
    document.close()
    return all_blocks


# TEST
if __name__ == "__main__":
    blocks = extract_document(
        PDF_PATH
    )
    chunks = create_chunks(
        blocks
    )

    print("\n")
    print("=" * 80)
    print("CHUNKING RESULT")
    print("=" * 80)
    print(
        "Total blocks:",
        len(blocks)
    )
    print(
        "Total chunks:",
        len(chunks)
    )
    for i, chunk in enumerate(
        chunks,
        start=1
    ):
        print("\n")
        print("-" * 80)
        print("CHUNK", i)
        print("-" * 80)
        print(
            "Page:",
            chunk["page_start"],
            "-",
            chunk["page_end"]
        )
        print(
            "Heading:",
            chunk["heading"]
        )
        print(
            "Parent heading:",
            chunk["parent_heading"]
        )
        print(
            "Section path:",
            chunk["section_path"]
        )
        print(
            "Type:",
            chunk["chunk_type"]
        )
        print("\nTEXT:")
        print(chunk["text"])
        print("\nSEARCH TEXT:")
        print(chunk["search_text"])