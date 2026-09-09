import re

# Heading Detection

def short_text_score(text):
    word_count = len(text.split())
    if word_count <= 10:
        return 2
    if word_count <= 15:
        return 1
    return 0

def bold_score(is_bold):
    if is_bold:
        return 2
    return 0

def font_size_score(font_size, body_font_size):

    if body_font_size <= 0:
        return 0

    ratio = font_size / body_font_size

    if ratio >= 1.5:
        return 2

    if ratio >= 1.2:
        return 1

    return 0

def spacing_score(block, normal_gap):
    score = 0

    if normal_gap <= 0:
        return score

    if block["gap_before"] is not None:
        if block["gap_before"] > normal_gap * 1.8:
            score += 1

    if block["gap_after"] is not None:
        if block["gap_after"] > normal_gap * 1.8:
            score += 1

    return score

def line_count_score(block):
    """
    Headings are usually short and contain
    only a small number of lines.
    """

    if block["line_count"] <= 2:
        return 1

    return 0

def numbering_score(text):
    pattern = r"^(\d+(\.\d+)*)[\.\s]"
    if re.match(pattern, text):
        return 2
    return 0

def uppercase_score(text):
    if len(text) > 3 and text.isupper():
        return 1
    return 0

def heading_score(block, normal_gap):
    score = 0

    score += short_text_score(block["text"])

    score += bold_score(block["is_bold"])

    score += font_size_score(
        block["font_size"],
        block["body_font_size"]
    )

    score += spacing_score(
        block,
        normal_gap
    )

    score += numbering_score(
        block["text"]
    )

    score += uppercase_score(
        block["text"]
    )

    score += line_count_score(
        block
    )

    return score



# Noise Detection

def noise_score(block):
    score = 0
    text = block["text"]
    
    # Very small text
    if block["font_size"] < block["body_font_size"] * 0.7:
        score += 2

    # Very short
    if len(text.strip()) <= 2:
        score += 2

    # URL
    if text.startswith("http://") or text.startswith("https://"):
        score += 3

    # Page number
    if text.strip().isdigit():
        score += 3

    # Symbol-only text
    if not any(char.isalnum() for char in text):
        score += 3

    # At the extreme top/bottom of page
    if block["relative_y"] < 0.05:
        score += 2

    if block["relative_y"] > 0.95:
        score += 2

    return score