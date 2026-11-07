"""Neutralize provider-controlled text before it reaches logs or summaries.

GitHub Actions treats any log line that begins with ``::`` as a workflow command.
Line breaks (and other control or format characters) inside a remote string could
therefore forge annotations or ``::stop-commands::``. Remote strings are reduced to
single-line printable text; codes that cannot be represented that way are rejected.
"""

import unicodedata


def is_unsafe_char(char: str) -> bool:
    """Control, format and surrogate/private chars, plus line/paragraph separators."""
    return unicodedata.category(char)[0] == "C" or unicodedata.category(char) in {
        "Zl",
        "Zp",
    }


def has_unsafe_chars(text: str) -> bool:
    return any(is_unsafe_char(char) for char in text)


def sanitize_remote_text(text: str) -> str:
    """Single-line printable text: unsafe characters become spaces, runs collapse."""
    return " ".join("".join(" " if is_unsafe_char(c) else c for c in text).split())
