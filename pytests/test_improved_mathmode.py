"""textext-improved: tests for automatic math-mode wrapping (textext/mathmode.py)."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "mathmode", os.path.join(os.path.dirname(__file__), "..", "textext", "mathmode.py"))
mathmode = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mathmode)


def test_inline_wraps_plain_formula():
    assert mathmode.wrap(r"\frac{a}{b}", "inline") == r"$\frac{a}{b}$"


def test_display_uses_displaystyle():
    assert mathmode.wrap(r"\sum_i x_i", "display") == r"$\displaystyle \sum_i x_i$"


def test_off_leaves_text_alone():
    assert mathmode.wrap(r"\frac{a}{b}", "off") == r"\frac{a}{b}"


def test_existing_delimiters_are_respected():
    for text in [r"$x$", r"$$x$$", r"\(x\)", r"\[x\]", r"\begin{align}x\end{align}", r"\ensuremath{x}",
                 r"Price: $5"]:
        assert mathmode.wrap(text, "inline") == text


def test_escaped_dollar_is_not_a_delimiter():
    assert mathmode.wrap(r"5\$", "inline") == r"$5\$$"


def test_blank_text_is_not_wrapped():
    assert mathmode.wrap("", "inline") == ""
    assert mathmode.wrap("   ", "display") == "   "


def test_surrounding_whitespace_is_trimmed_inside_delimiters():
    assert mathmode.wrap("  x^2 \n", "inline") == "$x^2$"


def test_typst():
    assert mathmode.wrap("x^2", "inline", "typst") == "$x^2$"
    assert mathmode.wrap("x^2", "display", "typst") == "$ x^2 $"
    # \begin is LaTeX-only; typst only looks at $
    assert mathmode.wrap("$x$", "inline", "typst") == "$x$"


def test_unknown_mode_is_off():
    assert mathmode.normalize_mode("bogus") == "off"
    assert mathmode.normalize_mode(None) == "off"
    assert mathmode.normalize_mode("Inline") == "inline"
    assert mathmode.wrap("x", "bogus") == "x"
