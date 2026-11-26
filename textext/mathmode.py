"""
Automatic math-mode wrapping for TexText (textext-improved addition).

Lets the user type a formula without the surrounding ``$...$``. The text the
user typed is what gets stored in the node; the delimiters are added only at
compile time, and only when the text contains no math delimiters of its own.

Pure module: imports nothing from inkex or gi, so it can be unit-tested.
"""

import re

MATH_MODES = ["off", "inline", "display"]
DEFAULT_MATH_MODE = "inline"

# Delimiters that mean "the user already chose math/text mode themselves".
# An unescaped $ (covers $...$ and $$...$$), \( \[ , any \begin{...}
# environment, and \ensuremath.
_LATEX_DELIMITERS = re.compile(r"(?<!\\)\$|\\\(|\\\[|\\begin\s*\{|\\ensuremath\b")
_TYPST_DELIMITERS = re.compile(r"(?<!\\)\$")


def normalize_mode(mode):
    """Return a valid mode name, falling back to 'off' for anything unknown."""
    if isinstance(mode, str) and mode.lower() in MATH_MODES:
        return mode.lower()
    return "off"


def has_math_delimiters(text, tex_command="pdflatex"):
    """True if the text already contains its own math (or environment) delimiters."""
    pattern = _TYPST_DELIMITERS if tex_command == "typst" else _LATEX_DELIMITERS
    return pattern.search(text) is not None


def wrap(text, mode, tex_command="pdflatex"):
    """
    Return the text to compile.

    :param text: the text exactly as typed by the user
    :param mode: 'off', 'inline' or 'display'
    :param tex_command: the compiler in use ('typst' or a LaTeX engine)
    :return: the text, wrapped in math delimiters when mode is on and the text
             has none of its own; otherwise the text unchanged
    """
    mode = normalize_mode(mode)
    if mode == "off" or not text or not text.strip():
        return text
    if has_math_delimiters(text, tex_command):
        return text
    body = text.strip()
    if tex_command == "typst":
        # Typst: "$x$" is inline, "$ x $" (spaces inside) is display.
        return "$%s$" % body if mode == "inline" else "$ %s $" % body
    if mode == "inline":
        return "$%s$" % body
    return "$\\displaystyle %s$" % body
