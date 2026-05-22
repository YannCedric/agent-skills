"""Shared diagram sizing, text, and edge-label metrics."""

WIDTH = 2200
HEIGHT = 820

CHAR_W = 10.8
DETAIL_CHAR_W = 7.6
EDGE_CHAR_W = 8.2
PAD_X = 20

EDGE_LABEL_PAD_X = 8
EDGE_LABEL_INLINE_PAD_X = 4
EDGE_LABEL_PAD_Y = 4
EDGE_LABEL_LINE_H = 16
EDGE_LABEL_MIN_W = 42
EDGE_LABEL_SEGMENT_PAD = 8
EDGE_LABEL_MAX_LINES = 6
EDGE_HORIZONTAL_INLINE_MAX_TEXT_WIDTH = 96
EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH = 124
EDGE_VERTICAL_LABEL_MAX_WIDTH = 116
EDGE_FLOATING_LABEL_MAX_WIDTH = 180
EDGE_INLINE_MIN_SEGMENT = 160
EDGE_INLINE_MIN_READABLE = 54
EDGE_INLINE_MIN_VISIBLE_RUN = 24


def text_width(value, char_width=CHAR_W):
    return max(1, len(str(value))) * char_width


def wrap_label(value, max_chars=22, max_lines=3):
    words = str(value).split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines[:max_lines]


def wrap_text_to_width(value, max_width, char_width=CHAR_W, max_lines=3):
    max_chars = max(4, int(max_width / char_width))
    return wrap_label(value, max_chars=max_chars, max_lines=max_lines)


def candidate_line_groups(words, max_lines):
    if max_lines <= 1 or len(words) <= 1:
        return [[" ".join(words)]]
    groups = []

    def walk(start, lines):
        remaining_words = len(words) - start
        remaining_lines = max_lines - len(lines)
        if remaining_words == 0:
            groups.append(lines)
            return
        if remaining_lines <= 0:
            return
        groups.append(lines + [" ".join(words[start:])])
        if remaining_lines == 1:
            return
        for end in range(start + 1, len(words) + 1):
            if len(words) - end < remaining_lines - 1:
                break
            walk(end, lines + [" ".join(words[start:end])])

    walk(0, [])
    return groups


def wrap_edge_label(value, max_width=None, allow_soft_two_line=True):
    label = str(value).strip()
    if not label:
        return [""]
    words = label.split()
    if len(words) == 1:
        return [label]
    single_width = text_width(label, EDGE_CHAR_W)
    if max_width is None or single_width <= max_width:
        return [label]

    max_lines = min(EDGE_LABEL_MAX_LINES, len(words))
    best = None
    best_score = None
    for lines in candidate_line_groups(words, max_lines):
        line_widths = [text_width(line, EDGE_CHAR_W) for line in lines]
        max_line_width = max(line_widths)
        balance = max(len(line) for line in lines) - min(len(line) for line in lines)
        allowed_width = max_width
        if allow_soft_two_line and len(lines) == 2:
            allowed_width = max(max_width, EDGE_LABEL_TWO_LINE_SOFT_MAX_WIDTH)
        overflow = max(0, max_line_width - allowed_width)
        score = (overflow, len(lines), max_line_width, balance)
        if best is None or score < best_score:
            best = lines
            best_score = score
    return best or [label]


def shape_text_width(shape, width, height):
    if shape == "cloud":
        return max(82, width * 0.68)
    if shape == "shield":
        return max(76, width * 0.58)
    if shape == "diamond":
        return max(72, width * 0.54)
    if shape == "user":
        return max(80, width - 92)
    if shape == "document":
        return max(86, width - 54)
    if shape == "horizontal-cylinder":
        cap_rx = height * 0.24
        cap_left = width - cap_rx * 2
        text_x = width / 2 - cap_rx * 0.35
        return max(80, min(width - cap_rx - 36, (cap_left + 4 - text_x) * 2))
    if shape == "database-cylinder":
        return max(86, width - PAD_X * 2)
    return max(80, width - PAD_X * 2)
