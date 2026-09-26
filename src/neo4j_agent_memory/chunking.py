from __future__ import annotations

import hashlib


def checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, max_chars: int = 1800) -> list[tuple[str, str]]:
    """Split plain text/Markdown on paragraph boundaries and label line ranges."""
    if max_chars < 200:
        raise ValueError("max_chars must be at least 200")
    lines = text.splitlines()
    chunks: list[tuple[str, str]] = []
    current: list[str] = []
    start_line = 1
    current_chars = 0

    def flush(end_line: int) -> None:
        nonlocal current, current_chars, start_line
        value = "\n".join(current).strip()
        if value:
            chunks.append((value, f"lines {start_line}-{end_line}"))
        current = []
        current_chars = 0

    for line_number, line in enumerate(lines, start=1):
        pieces = [line]
        if len(line) > max_chars:
            pieces = [line[i : i + max_chars] for i in range(0, len(line), max_chars)]
        for piece in pieces:
            extra = len(piece) + (1 if current else 0)
            if current and current_chars + extra > max_chars:
                flush(line_number - 1 if start_line < line_number else line_number)
                start_line = line_number
            current.append(piece)
            current_chars += len(piece) + (1 if len(current) > 1 else 0)
    if current:
        flush(len(lines))
    return chunks
