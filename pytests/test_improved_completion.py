"""textext-improved: tests for LaTeX completion matching (textext/latex_completion.py)."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "latex_completion", os.path.join(os.path.dirname(__file__), "..", "textext", "latex_completion.py"))
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)


def test_prefix_after_backslash():
    assert lc.find_prefix(r"a + \fr") == ("command", r"\fr", 4)


def test_prefix_bare_backslash():
    assert lc.find_prefix("x \\") == ("command", "\\", 2)


def test_no_prefix_in_plain_text():
    assert lc.find_prefix("x + y") is None


def test_line_break_is_not_a_command():
    assert lc.find_prefix("a \\\\") is None


def test_command_after_line_break():
    assert lc.find_prefix("a \\\\\\al") == ("command", r"\al", 4)


def test_environment_prefix():
    assert lc.find_prefix(r"\begin{ali") == ("env", "ali", 7)
    assert lc.find_prefix(r"\end{") == ("env", "", 5)


def test_match_commands_order_and_filter():
    result = lc.match_commands(r"\fr")
    assert result[0] == r"\frac{}{}"
    assert all(lc.command_name(t).startswith(r"\fr") for t in result)


def test_exact_command_not_offered_back():
    assert r"\alpha" not in lc.match_commands(r"\alpha")


def test_user_commands_from_preamble_and_text():
    preamble = r"\newcommand{\E}{\mathbb{E}} \DeclareMathOperator{\Var}{Var} \newcommand\cov{Cov}"
    found = lc.user_commands(preamble, r"\hat{\beta} \myop x")
    assert {r"\E", r"\Var", r"\cov", r"\myop", r"\hat", r"\beta"} <= set(found)


def test_user_commands_added_without_duplicates():
    result = lc.match_commands(r"\Va", extra=[r"\Var", r"\frac"])
    assert r"\Var" in result
    assert lc.match_commands(r"\fra", extra=[r"\frac"]).count(r"\frac") == 0


def test_expand_command_cursor_in_first_brace():
    assert lc.expand_command(r"\frac{}{}") == (r"\frac{}{}", 6)
    assert lc.expand_command(r"\sqrt[]{}") == (r"\sqrt[]{}", 6)
    assert lc.expand_command(r"\alpha") == (r"\alpha", 6)


def test_expand_environment_begin():
    text, cursor = lc.expand_environment("align*", True)
    assert text == "align*}\n    \n\\end{align*}"
    assert text[:cursor] == "align*}\n    "


def test_expand_environment_with_column_spec():
    text, cursor = lc.expand_environment("array", True)
    assert text.startswith("array}{}\n")
    assert text[:cursor] == "array}{"


def test_expand_environment_end():
    assert lc.expand_environment("align", False) == ("align}", 6)


def test_match_environments():
    assert lc.match_environments("ali") == ["align", "align*", "aligned", "alignat", "alignat*"]
