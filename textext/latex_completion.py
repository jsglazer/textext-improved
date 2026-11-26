"""
LaTeX auto-completion data and matching for TexText (textext-improved addition).

Pure module: imports nothing from inkex or gi. The GtkSourceView provider in
asktext.py is a thin shell around the functions here.

Two kinds of completion:
  * commands  -- triggered by typing a backslash: "\\fr" -> "\\frac{}{}"
  * environments -- triggered inside "\\begin{": "\\begin{ali" -> "align*"
"""

import re

# Command templates. "{}" / "[]" in a template are placeholders; after
# insertion the cursor goes inside the first "{}" (or to the end if none).
COMMANDS = [
    # structure / fractions / roots
    r"\frac{}{}", r"\dfrac{}{}", r"\tfrac{}{}", r"\cfrac{}{}", r"\binom{}{}", r"\dbinom{}{}",
    r"\sqrt{}", r"\sqrt[]{}", r"\left(", r"\right)", r"\left[", r"\right]", r"\left\{", r"\right\}",
    r"\left|", r"\right|", r"\left.", r"\right.", r"\big", r"\Big", r"\bigg", r"\Bigg",
    r"\displaystyle", r"\textstyle", r"\scriptstyle",
    # text and fonts
    r"\text{}", r"\textbf{}", r"\textit{}", r"\textrm{}", r"\texttt{}", r"\emph{}",
    r"\mathrm{}", r"\mathbf{}", r"\mathit{}", r"\mathsf{}", r"\mathtt{}", r"\mathcal{}",
    r"\mathbb{}", r"\mathfrak{}", r"\mathscr{}", r"\boldsymbol{}", r"\bm{}", r"\operatorname{}",
    # accents
    r"\hat{}", r"\widehat{}", r"\bar{}", r"\overline{}", r"\underline{}", r"\tilde{}",
    r"\widetilde{}", r"\vec{}", r"\dot{}", r"\ddot{}", r"\acute{}", r"\grave{}", r"\breve{}",
    r"\check{}", r"\overbrace{}", r"\underbrace{}", r"\overset{}{}", r"\underset{}{}",
    r"\stackrel{}{}", r"\xrightarrow{}", r"\xleftarrow{}",
    # big operators
    r"\sum", r"\prod", r"\coprod", r"\int", r"\iint", r"\iiint", r"\oint", r"\bigcup",
    r"\bigcap", r"\bigoplus", r"\bigotimes", r"\bigvee", r"\bigwedge", r"\lim", r"\limsup",
    r"\liminf", r"\sup", r"\inf", r"\max", r"\min", r"\arg", r"\argmax", r"\argmin", r"\det",
    r"\dim", r"\ker", r"\deg", r"\gcd", r"\Pr", r"\exp", r"\log", r"\ln", r"\lg",
    r"\sin", r"\cos", r"\tan", r"\cot", r"\sec", r"\csc", r"\arcsin", r"\arccos", r"\arctan",
    r"\sinh", r"\cosh", r"\tanh", r"\limits", r"\nolimits",
    # greek
    r"\alpha", r"\beta", r"\gamma", r"\delta", r"\epsilon", r"\varepsilon", r"\zeta", r"\eta",
    r"\theta", r"\vartheta", r"\iota", r"\kappa", r"\lambda", r"\mu", r"\nu", r"\xi", r"\pi",
    r"\varpi", r"\rho", r"\varrho", r"\sigma", r"\varsigma", r"\tau", r"\upsilon", r"\phi",
    r"\varphi", r"\chi", r"\psi", r"\omega", r"\Gamma", r"\Delta", r"\Theta", r"\Lambda",
    r"\Xi", r"\Pi", r"\Sigma", r"\Upsilon", r"\Phi", r"\Psi", r"\Omega",
    # relations
    r"\leq", r"\geq", r"\le", r"\ge", r"\neq", r"\ne", r"\approx", r"\equiv", r"\sim",
    r"\simeq", r"\cong", r"\propto", r"\ll", r"\gg", r"\prec", r"\succ", r"\preceq",
    r"\succeq", r"\subset", r"\supset", r"\subseteq", r"\supseteq", r"\in", r"\notin", r"\ni",
    r"\mid", r"\nmid", r"\parallel", r"\perp", r"\models", r"\vdash", r"\coloneqq",
    r"\overset{d}{\to}", r"\overset{p}{\to}", r"\xrightarrow{d}", r"\xrightarrow{p}",
    # arrows
    r"\to", r"\gets", r"\rightarrow", r"\leftarrow", r"\Rightarrow", r"\Leftarrow",
    r"\leftrightarrow", r"\Leftrightarrow", r"\implies", r"\impliedby", r"\iff", r"\mapsto",
    r"\longrightarrow", r"\longmapsto", r"\uparrow", r"\downarrow",
    # binary operators
    r"\times", r"\cdot", r"\div", r"\pm", r"\mp", r"\ast", r"\star", r"\circ", r"\bullet",
    r"\oplus", r"\ominus", r"\otimes", r"\odot", r"\cup", r"\cap", r"\setminus", r"\wedge",
    r"\vee", r"\land", r"\lor", r"\lnot", r"\neg",
    # misc symbols
    r"\infty", r"\partial", r"\nabla", r"\forall", r"\exists", r"\nexists", r"\emptyset",
    r"\varnothing", r"\ell", r"\hbar", r"\Re", r"\Im", r"\aleph", r"\prime", r"\top",
    r"\bot", r"\angle", r"\triangle", r"\square", r"\checkmark", r"\dagger", r"\ddagger",
    r"\ldots", r"\cdots", r"\vdots", r"\ddots", r"\dots", r"\langle", r"\rangle",
    r"\lfloor", r"\rfloor", r"\lceil", r"\rceil", r"\lVert", r"\rVert", r"\lvert", r"\rvert",
    r"\|", r"\{", r"\}",
    # spacing and layout
    r"\quad", r"\qquad", r"\,", r"\;", r"\!", r"\hspace{}", r"\vspace{}", r"\\", r"\newline",
    r"\phantom{}", r"\hphantom{}", r"\vphantom{}", r"\mathstrut", r"\tag{}", r"\label{}",
    r"\nonumber", r"\notag", r"\intertext{}", r"\substack{}",
    # colour and boxes
    r"\color{}", r"\textcolor{}{}", r"\colorbox{}{}", r"\boxed{}", r"\fbox{}",
    # sizes
    r"\tiny", r"\scriptsize", r"\footnotesize", r"\small", r"\normalsize", r"\large",
    r"\Large", r"\LARGE", r"\huge", r"\Huge",
    # environments
    r"\begin{}", r"\end{}",
]

ENVIRONMENTS = [
    "align", "align*", "aligned", "alignat", "alignat*", "array", "bmatrix", "Bmatrix",
    "cases", "center", "dcases", "enumerate", "equation", "equation*", "flalign", "gather",
    "gather*", "gathered", "itemize", "matrix", "multline", "multline*", "pmatrix",
    "smallmatrix", "split", "subarray", "tabular", "vmatrix", "Vmatrix",
]

# Environments that need a column spec right after \begin{name}
_ENV_ARGS = {"array": "{}", "tabular": "{}", "alignat": "{}", "alignat*": "{}", "subarray": "{}"}

_DEFINITION_RE = re.compile(
    r"\\(?:newcommand|renewcommand|providecommand|DeclareMathOperator\*?|def)\s*\{?\s*(\\[A-Za-z@]+)")
_USED_COMMAND_RE = re.compile(r"\\[A-Za-z]{2,}")


def command_name(template):
    """The bare command a template inserts, e.g. '\\frac{}{}' -> '\\frac'."""
    match = re.match(r"\\[A-Za-z]+|\\.", template)
    return match.group(0) if match else template


def find_prefix(text_before_cursor):
    """
    Decide what, if anything, to complete.

    :param text_before_cursor: the text of the current line up to the cursor
    :return: ("env", partial_name, start_offset) when inside "\\begin{" / "\\end{",
             ("command", "\\partial", start_offset) when after a backslash,
             or None. start_offset is the index in text_before_cursor where the
             text to be replaced begins.
    """
    env = re.search(r"\\(begin|end)\s*\{([A-Za-z*]*)$", text_before_cursor)
    if env:
        return "env", env.group(2), env.start(2)
    cmd = re.search(r"\\([A-Za-z]*)$", text_before_cursor)
    if cmd:
        # An even number of backslashes before this one means it is escaped ("\\\\" line break)
        start = cmd.start()
        run = 0
        while start - run - 1 >= 0 and text_before_cursor[start - run - 1] == "\\":
            run += 1
        if run % 2 == 1:
            return None
        return "command", "\\" + cmd.group(1), start
    return None


def user_commands(*texts):
    """
    Commands the user defines or already uses, found in the preamble and the
    text being edited, so that they are offered too.
    """
    found = set()
    for text in texts:
        if not text:
            continue
        found.update(_DEFINITION_RE.findall(text))
        found.update(_USED_COMMAND_RE.findall(text))
    return sorted(found)


def match_commands(prefix, extra=()):
    """
    Command templates matching a prefix such as '\\fr'.

    Built-in templates come first (in their curated order), then the user's
    own commands not already covered. The exact command being typed is not
    offered back by itself (nothing to complete).
    """
    seen = set()
    results = []
    for template in list(COMMANDS) + list(extra):
        name = command_name(template)
        if not name.startswith(prefix) or template in seen:
            continue
        if template == prefix:
            continue
        if template in extra and name in seen:
            continue
        seen.add(template)
        seen.add(name)
        results.append(template)
    return results


def match_environments(prefix):
    return [env for env in ENVIRONMENTS if env.startswith(prefix) and env != prefix]


def expand_command(template):
    """
    The text to insert for a command template and the cursor offset within it.

    Placeholders are left as empty braces; the cursor goes inside the first
    "{}" or "[]".
    """
    positions = [p for p in (template.find("{}"), template.find("[]")) if p != -1]
    if positions:
        return template, min(positions) + 1
    return template, len(template)


def expand_environment(name, is_begin, indent=""):
    """
    The text to insert when an environment name is chosen after "\\begin{" or
    "\\end{", and the cursor offset within it. After "\\begin{" the matching
    "\\end{name}" is added with an empty body line where the cursor lands.

    Any characters already present after the cursor (such as an auto-closed
    "}") are handled by the caller.
    """
    if not is_begin:
        return name + "}", len(name) + 1
    args = _ENV_ARGS.get(name, "")
    head = name + "}" + args
    body_indent = indent + "    "
    text = head + "\n" + body_indent + "\n" + indent + "\\end{" + name + "}"
    if args:
        cursor = len(name) + 2  # inside the column-spec braces
    else:
        cursor = len(head) + 1 + len(body_indent)
    return text, cursor
