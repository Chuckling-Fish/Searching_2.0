import pymupdf
import re
import scoring

# ---------------------------------------------------------
# PDF FILE
# ---------------------------------------------------------

PDF_PATH = "C:/Users/anjum/OneDrive/文档/lec3.pdf"

# ---------------------------------------------------------
# EXTRACT BLOCKS FROM ONE PAGE
# ---------------------------------------------------------

def extract_blocks(page, page_number):

    page_data = page.get_text("dict")

    blocks = []

    for block_number, block in enumerate(page_data["blocks"]):

        # -------------------------------------------------
        # Ignore blocks that do not contain text lines
        # -------------------------------------------------

        if "lines" not in block:
            continue

        # -------------------------------------------------
        # Coordinates
        # -------------------------------------------------

        x0, y0, x1, y1 = block["bbox"]

        page_height = page.rect.height
        page_width = page.rect.width

        relative_y = y0 / page_height
        relative_x = x0 / page_width

        # -------------------------------------------------
        # Extract complete block text
        # -------------------------------------------------

        block_text = ""

        for line in block["lines"]:

            for span in line["spans"]:
                block_text += span["text"]

            block_text += " "

        block_text = block_text.strip()

        # Ignore empty blocks
        if not block_text:
            continue

        # -------------------------------------------------
        # Font information
        # -------------------------------------------------

        font_sizes = []
        is_bold = False

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

        # -------------------------------------------------
        # Average font size
        # -------------------------------------------------

        average_font_size = (
            sum(font_sizes) / len(font_sizes)
        )

        # -------------------------------------------------
        # Number of lines
        # -------------------------------------------------

        line_count = len(block["lines"])

        # -------------------------------------------------
        # Store block information
        # -------------------------------------------------

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

    blocks.sort(
        key=lambda block: (
            block["y0"],
            block["x0"]
        )
    )

    # -----------------------------------------------------
    # Add reading-order number
    # -----------------------------------------------------

    for reading_order, block in enumerate(blocks):

        block["reading_order"] = reading_order

    return blocks


# ---------------------------------------------------------
# CALCULATE SPACING BETWEEN BLOCKS
# ---------------------------------------------------------

def calculate_gaps(blocks):

    for i, block in enumerate(blocks):

        # -------------------------------------------------
        # First block
        # -------------------------------------------------

        if i == 0:

            block["gap_before"] = None

        else:

            previous = blocks[i - 1]

            gap = block["y0"] - previous["y1"]

            # Overlapping blocks
            if gap < 0:
                gap = 0

            block["gap_before"] = gap

    # -----------------------------------------------------
    # Calculate gap after
    # -----------------------------------------------------

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


# ---------------------------------------------------------
# FIND NORMAL BODY FONT SIZE
# ---------------------------------------------------------

def get_body_font_size(blocks):

    if not blocks:
        return 0

    font_sizes = []

    for block in blocks:

        # Ignore very small text such as page numbers
        # and footer text when estimating body size.
        if block["font_size"] >= 8:
            font_sizes.append(
                block["font_size"]
            )

    if not font_sizes:
        return 0

    font_sizes.sort()

    middle = len(font_sizes) // 2

    return font_sizes[middle]


# ---------------------------------------------------------
# FIND NORMAL GAP BETWEEN BLOCKS
# ---------------------------------------------------------

def get_normal_gap(blocks):
    gaps = []

    for block in blocks:

        gap = block["gap_before"]

        # Only use actual positive gaps
        if gap is not None and gap > 0:
            gaps.append(gap)

    if not gaps:
        return 0

    gaps.sort()

    middle = len(gaps) // 2

    return gaps[middle]


# ---------------------------------------------------------
# ADD BODY FONT SIZE TO EVERY BLOCK
# ---------------------------------------------------------

def add_body_font_size(blocks, body_font_size):

    for block in blocks:

        block["body_font_size"] = body_font_size

    return blocks

def is_list_item(text):

    text = text.strip()

    # -----------------------------------------------------
    # Numbered list
    #
    # Examples:
    # 1. Install Django
    # 2. Create a project
    # 1) Open the file
    # -----------------------------------------------------

    numbered_pattern = r"^(\d+(\.\d+)*[.)])\s+"

    if re.match(numbered_pattern, text):
        return True

    # -----------------------------------------------------
    # Lettered list
    #
    # Examples:
    # a. First option
    # b) Second option
    # -----------------------------------------------------

    letter_pattern = r"^[A-Za-z][.)]\s+"

    if re.match(letter_pattern, text):
        return True

    # -----------------------------------------------------
    # Bullet characters
    # -----------------------------------------------------

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

# ---------------------------------------------------------
# CLASSIFY BLOCK
# ---------------------------------------------------------

def classify_block(block, normal_gap):

    # -----------------------------------------------------
    # Calculate heading score
    # -----------------------------------------------------

    heading_score = scoring.heading_score(
        block,
        normal_gap
    )

    # -----------------------------------------------------
    # Calculate noise score
    # -----------------------------------------------------

    noise_score = scoring.noise_score(
        block
    )

    # -----------------------------------------------------
    # Noise gets highest priority
    # -----------------------------------------------------

    if noise_score >= 3:

        return (
            "NOISE",
            heading_score,
            noise_score
        )

    # -----------------------------------------------------
    # Detect list items before heading classification
    #
    # This prevents:
    #
    # 1. Install Django
    # 2. Create project
    #
    # from being classified as headings.
    # -----------------------------------------------------

    if is_list_item(block["text"]):

        return (
            "LIST_ITEM",
            heading_score,
            noise_score
        )

    # -----------------------------------------------------
    # Heading threshold
    # -----------------------------------------------------

    if heading_score >= 4:

        return (
            "HEADING",
            heading_score,
            noise_score
        )

    # -----------------------------------------------------
    # Everything else
    # -----------------------------------------------------

    return (
        "PARAGRAPH",
        heading_score,
        noise_score
    )


# ---------------------------------------------------------
# PROCESS ONE PAGE
# ---------------------------------------------------------

def process_page(page, page_number):

    # -----------------------------------------------------
    # Step 1: Extract blocks
    # -----------------------------------------------------

    blocks = extract_blocks(
        page,
        page_number
    )

    if not blocks:
        return []

    # -----------------------------------------------------
    # Step 2: Calculate vertical spacing
    # -----------------------------------------------------

    blocks = calculate_gaps(
        blocks
    )

    # -----------------------------------------------------
    # Step 3: Determine normal body font size
    # -----------------------------------------------------

    body_font_size = get_body_font_size(
        blocks
    )

    # -----------------------------------------------------
    # Step 4: Add body font size to blocks
    # -----------------------------------------------------

    blocks = add_body_font_size(
        blocks,
        body_font_size
    )

    # -----------------------------------------------------
    # Step 5: Determine normal spacing
    # -----------------------------------------------------

    normal_gap = get_normal_gap(
        blocks
    )

    # -----------------------------------------------------
    # Step 6: Classify blocks
    # -----------------------------------------------------

    for block in blocks:

        block_type, heading_score, noise_score = classify_block(
            block,
            normal_gap
        )

        block["type"] = block_type

        block["heading_score"] = heading_score

        block["noise_score"] = noise_score
    
    return blocks
# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

document = pymupdf.open(PDF_PATH)

for page_number, page in enumerate(document, start=1):

    blocks = process_page(page, page_number)

    print("\n")
    print("=" * 80)
    print(f"PAGE {page_number}")
    print("=" * 80)

    for block in blocks:
        print(block)

document.close()