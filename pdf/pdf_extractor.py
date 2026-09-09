import pymupdf

pdf_path = "C:/Users/anjum/OneDrive/文档/lec3.pdf"

document = pymupdf.open(pdf_path)

for page_number, page in enumerate(document):
    page_data = page.get_text("dict")
    
    for block_number, block in enumerate(page_data["blocks"]):
        if "lines" not in block:
            continue
        
        # -------------------------
        # Coordinates
        # -------------------------
        x0, y0, x1, y1 = block["bbox"]

        # -------------------------
        # Extract complete text
        # -------------------------
        block_text = ""
        for line in block["lines"]:
            for span in line["spans"]:
                block_text += span["text"]
            block_text += " "

        block_text = block_text.strip()

        # -------------------------
        # Font information
        # -------------------------

        font_sizes = []
        is_bold = False
        for line in block["lines"]:
            for span in line["spans"]:
                font_sizes.append(span["size"])
                if span["flags"] & 16:
                    is_bold = True
                    
        if not font_sizes:
            continue

        average_font_size = sum(font_sizes) / len(font_sizes)

        # -------------------------
        # Store block information
        # -------------------------
        block_data = {
            "page": page_number + 1,
            "block": block_number,
            "text": block_text,

            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,

            "font_size": average_font_size,
            "is_bold": is_bold
        }


        print(block_data)


document.close()