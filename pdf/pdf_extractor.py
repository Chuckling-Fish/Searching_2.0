import pymupdf
import re
from pdf import scoring

# PDF FILE
PDF_PATH = ".pdf"

# EXTRACT BLOCKS FROM ONE PAGE
def extract_blocks(page, page_number):
    page_data = page.get_text("dict")
    blocks = []
    # Walk through every raw block on the page
    for block_number, block in enumerate(page_data["blocks"]):
        # Ignore blocks that do not contain text lines
        if "lines" not in block:
            continue

        # Coordinates
        x0, y0, x1, y1 = block["bbox"]
        page_height = page.rect.height
        page_width = page.rect.width
        relative_y = y0 / page_height
        relative_x = x0 / page_width

        # Extract complete block text
        block_text = ""
        for line in block["lines"]:
            for span in line["spans"]:
                block_text += span["text"]
            block_text += " "
        block_text = block_text.strip()

        # Ignore empty blocks
        if not block_text:
            continue

        # Font information
        font_sizes = []
        is_bold = False
        # Collect font sizes and detect bold spans
        for line in block["lines"]:
            for span in line["spans"]:
                font_sizes.append(
                    span["size"]
                )
                # PyMuPDF flag 16 = bold
                if span["flags"] & 16:
                    is_bold = True

        # Ignore blocks without font information
        if not font_sizes:
            continue

        # Average font size
        average_font_size = (
            sum(font_sizes) / len(font_sizes)
        )

        # Number of lines
        line_count = len(block["lines"])

        # Store block information
        block_data = {
            "page": page_number,

            # Original PyMuPDF block number
            "block": block_number,
            "text": block_text,
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "relative_x": relative_x,
            "relative_y": relative_y,
            "font_size": average_font_size,
            "is_bold": is_bold,
            "line_count": line_count,
        }
        blocks.append(block_data)
    # Order blocks top-to-bottom, left-to-right
    blocks.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    # Add reading-order number
    for reading_order, block in enumerate(blocks):
        block["reading_order"] = reading_order
    return blocks


# CALCULATE SPACING BETWEEN BLOCKS
def calculate_gaps(blocks):
    # Calculate the gap before each block
    for i, block in enumerate(blocks):
        # First block
        if i == 0:

            block["gap_before"] = None
        else:

            previous = blocks[i - 1]

            gap = block["y0"] - previous["y1"]

            # Overlapping blocks
            if gap < 0:
                gap = 0

            block["gap_before"] = gap
     
    # Calculate gap after
    for i, block in enumerate(blocks):
        if i == len(blocks) - 1:

            block["gap_after"] = None
        else:
            next_block = blocks[i + 1]
            gap = next_block["y0"] - block["y1"]
            if gap < 0:
                gap = 0
            block["gap_after"] = gap
    return blocks

# FIND NORMAL BODY FONT SIZE
def get_body_font_size(blocks):
    if not blocks:
        return 0
    font_sizes = []
    # Collect font sizes, ignoring unreasonably tiny text
    for block in blocks:
        if block["font_size"] >= 8:
            font_sizes.append(
                block["font_size"]
            )
    if not font_sizes:
        return 0
    font_sizes.sort()
    # The median font size is treated as the body text size
    middle = len(font_sizes) // 2
    return font_sizes[middle]

# FIND NORMAL GAP BETWEEN BLOCKS
def get_normal_gap(blocks):
    gaps = []
    # Collect all positive gaps between blocks
    for block in blocks:
        gap = block["gap_before"]
        if gap is not None and gap > 0:
            gaps.append(gap)
    if not gaps:
        return 0
    gaps.sort()
    # The median gap is treated as the normal spacing
    middle = len(gaps) // 2
    return gaps[middle]

# ADD BODY FONT SIZE TO EVERY BLOCK
def add_body_font_size(blocks, body_font_size):
    for block in blocks:
        block["body_font_size"] = body_font_size
    return blocks

# LIST DETECTION
def is_list_item(text):
    # Numbered List
    text = text.strip()
    numbered_pattern = r"^(\d+(\.\d+)*[.)])\s+"
    if re.match(numbered_pattern, text):
        return True
     
    # Lettered list
    letter_pattern = r"^[A-Za-z][.)]\s+"
    if re.match(letter_pattern, text):
        return True
    
    # Bullet characters
    bullet_characters = (
        "•",
        "●",
        "○",
        "▪",
        "▫",
        "–",
        "—"
    )
    if text.startswith(bullet_characters):
        return True
    return False

def is_numbered_heading(text):
    text = text.strip()
    # Match numbering patterns from top level to four levels deep
    patterns = [
        r"^\d+\.\s+.+",                    
        r"^\d+\.\d+\s+.+",                 
        r"^\d+\.\d+\.\d+\s+.+",            
        r"^\d+\.\d+\.\d+\.\d+\s+.+",       
    ]
    for pattern in patterns:
        if re.match(pattern, text):
            return True
    return False

# CLASSIFY BLOCK
def classify_block(block, normal_gap):
    heading_score = scoring.heading_score(block, normal_gap)
    noise_score = scoring.noise_score(block)
    text = block["text"]
    # Treat clearly noisy blocks as noise regardless of other signals
    if noise_score >= 3:
        return ("NOISE", heading_score, noise_score)
    # Numbered headings need either multi-level numbering or visual heading cues
    if is_numbered_heading(text):
        is_multi_level = bool(re.match(r"^\d+\.\d+", text))
        visual_heading_score = (
            scoring.bold_score(block["is_bold"])
            + scoring.font_size_score(block["font_size"], block["body_font_size"])
            + scoring.spacing_score(block, normal_gap)
        )
        if is_multi_level or visual_heading_score >= 1:
            return ("HEADING", heading_score, noise_score)
    if is_list_item(text):
        return ("LIST_ITEM", heading_score, noise_score)
    if is_numbered_heading(text):
        return ("HEADING", heading_score, noise_score)
    # Fall back to the general heading score threshold
    if heading_score >= 4:
        return ("HEADING", heading_score, noise_score)
    return ("PARAGRAPH", heading_score, noise_score)

# PROCESS ONE PAGE
def process_page(page, page_number):
    # Extract blocks
    blocks = extract_blocks(
        page,
        page_number
    )
    if not blocks:
        return []

    # Calculate vertical spacing
    blocks = calculate_gaps(
        blocks
    )

    # Determine normal body font size
    body_font_size = get_body_font_size(
        blocks
    )

    # Add body font size to blocks
    blocks = add_body_font_size(
        blocks,
        body_font_size
    )

    # Determine normal spacing
    normal_gap = get_normal_gap(
        blocks
    )

    # Classify blocks
    for block in blocks:
        block_type, heading_score, noise_score = classify_block(
            block,
            normal_gap
        )
        block["type"] = block_type
        block["heading_score"] = heading_score
        block["noise_score"] = noise_score
    return blocks

# TEST
if __name__ == "__main__":
    document = pymupdf.open(PDF_PATH)
    # Process and print every page's classified blocks
    for page_number, page in enumerate(document, start=1):
        blocks = process_page(page, page_number)
        print("\n")
        print("=" * 80)
        print(f"PAGE {page_number}")
        print("=" * 80)
        for block in blocks:
            print(block)
    document.close()