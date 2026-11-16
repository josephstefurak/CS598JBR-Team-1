"""Regex-level Rust lexing: blank out comments and literal contents, collect string literals.

Not a parser. `strip(text)` returns text of the same length and line layout in
which comments are spaces and string/char literal contents are spaces (the
quotes stay). That lets the safety, interface and integrity scans run regexes
on code only, and keeps every offset and line number valid.
"""


def _blank(chars, start, end):
    for i in range(start, end):
        if chars[i] != "\n":
            chars[i] = " "


def scan(text):
    """Return (stripped_text, literals) where literals is [(value, line_no)] for string literals."""
    chars = list(text)
    literals = []
    n = len(text)
    i = 0
    line = 1
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1
            i += 1
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            _blank(chars, i, j)
            i = j
            continue
        if text.startswith("/*", i):
            depth, j = 1, i + 2
            while j < n and depth:
                if text.startswith("/*", j):
                    depth, j = depth + 1, j + 2
                elif text.startswith("*/", j):
                    depth, j = depth - 1, j + 2
                else:
                    j += 1
            line += text.count("\n", i, j)
            _blank(chars, i, j)
            i = j
            continue
        prev_word = i > 0 and (text[i - 1].isalnum() or text[i - 1] == "_")
        # raw strings: r"..", r#".."#, br#".."#
        if not prev_word and (text.startswith("r", i) or text.startswith("br", i)):
            k = i + (2 if text[i] == "b" else 1)
            hashes = 0
            while k < n and text[k] == "#":
                hashes += 1
                k += 1
            if k < n and text[k] == '"' and (hashes or k == i + (2 if text[i] == "b" else 1)):
                close = '"' + "#" * hashes
                end = text.find(close, k + 1)
                end = n if end < 0 else end
                literals.append((text[k + 1:end], line))
                line += text.count("\n", i, end)
                _blank(chars, k + 1, end)
                i = end + len(close)
                continue
        if c == '"' or (c == "b" and not prev_word and text.startswith('b"', i)):
            k = i + 1 if c == '"' else i + 2
            j = k
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            end = min(j, n)
            literals.append((_unescape(text[k:end]), line))
            line += text.count("\n", i, end)
            _blank(chars, k, end)
            i = end + 1
            continue
        if c == "'":
            # char literal vs lifetime
            if i + 1 < n and text[i + 1] == "\\":
                j = i + 2
                while j < n and text[j] != "'":
                    j += 1
                _blank(chars, i + 1, j)
                i = j + 1
                continue
            if i + 2 < n and text[i + 2] == "'":
                _blank(chars, i + 1, i + 2)
                i += 3
                continue
        i += 1
    return "".join(chars), literals


def strip(text):
    return scan(text)[0]


def string_literals(text):
    return scan(text)[1]


def _unescape(s):
    if "\\" not in s:
        return s
    out = []
    i = 0
    simple = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt in simple:
                out.append(simple[nxt])
                i += 2
                continue
            if nxt == "\n":  # line continuation: skip newline and leading whitespace
                i += 2
                while i < len(s) and s[i] in " \t\n":
                    i += 1
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


def line_of(text, offset):
    return text.count("\n", 0, offset) + 1


def match_brace(text, open_idx):
    """Index of the '}' matching the '{' at open_idx in stripped text, or -1."""
    depth = 0
    for j in range(open_idx, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return j
    return -1
