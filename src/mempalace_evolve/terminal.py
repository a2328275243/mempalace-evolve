"""Terminal output utilities — ANSI colors, no external dependencies."""

import os
import sys

# Detect ANSI support
_SUPPORTS_COLOR = (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()) or os.environ.get(
    "FORCE_COLOR", ""
).lower() in ("1", "true", "yes")

# Windows: enable VT100 escape sequences and UTF-8 output
if sys.platform == "win32":
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass
    # Force UTF-8 output on Windows
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Detect if terminal supports Unicode box-drawing
_SUPPORTS_UNICODE = True
try:
    "═║─✓✗".encode(sys.stdout.encoding or "ascii")
except (UnicodeEncodeError, LookupError):
    _SUPPORTS_UNICODE = False


def _esc(code: str, text: str) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def bold(text: str) -> str:
    return _esc("1", text)


def dim(text: str) -> str:
    return _esc("2", text)


def cyan(text: str) -> str:
    return _esc("96", text)


def green(text: str) -> str:
    return _esc("92", text)


def yellow(text: str) -> str:
    return _esc("93", text)


def red(text: str) -> str:
    return _esc("91", text)


def magenta(text: str) -> str:
    return _esc("95", text)


def divider(char: str = None, width: int = 56) -> str:
    if char is None:
        char = "─" if _SUPPORTS_UNICODE else "-"
    return dim(char * width)


def step(num: int, title: str) -> str:
    """Format a numbered step header."""
    return bold(cyan(f"\n  [{num}] {title}"))


def bullet(text: str, indent: int = 6) -> str:
    mark = "✓" if _SUPPORTS_UNICODE else "+"
    return " " * indent + green(f"{mark} ") + text


def fail(text: str, indent: int = 6) -> str:
    mark = "✗" if _SUPPORTS_UNICODE else "x"
    return " " * indent + red(f"{mark} ") + text


def banner(text: str) -> str:
    if _SUPPORTS_UNICODE:
        line = "═" * (len(text) + 4)
        return bold(cyan(f"\n  {line}\n  ║ {text} ║\n  {line}\n"))
    else:
        line = "=" * (len(text) + 4)
        return bold(cyan(f"\n  {line}\n  | {text} |\n  {line}\n"))
