import re

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
    ratio = font_size / body_font_size
    if ratio >= 1.5:
        return 2
    if ratio >= 1.2:
        return 1
    return 0

def spacing_score(gap_before, gap_after):
    score = 0
    if gap_before >= 15:
        score += 1
    if gap_after >= 15:
        score += 1
    return score

def numbering_score(text):
    pattern = r"^(\d+(\.\d+)*)[\.\s]"
    if re.match(pattern, text):
        return 2
    return 0

def uppercase_score(text):
    if len(text) > 3 and text.isupper():
        return 1
    return 0

def heading_score(block):
    score = 0
    score += short_text_score(block["text"])
    score += bold_score(block["is_bold"])
    score += font_size_score(
        block["font_size"],
        block["body_font_size"]
    )
    score += spacing_score(
        block["gap_before"],
        block["gap_after"]
    )
    score += numbering_score(block["text"])
    score += uppercase_score(block["text"])
    return score