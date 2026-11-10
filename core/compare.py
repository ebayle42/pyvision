"""Comparaison ligne par ligne d'une sortie avec l'exemple du sujet."""
from __future__ import annotations

import re
from dataclasses import dataclass

# Une ligne attendue peut être un texte exact, ou une regex (Pattern).
Expected = "str | re.Pattern[str]"


@dataclass
class Diff:
    ok: bool
    only_trailing_spaces: bool
    first_line: int | None
    expected: str
    got: str
    summary: str


def _match(exp: "str | re.Pattern[str]", got: str) -> bool:
    if isinstance(exp, re.Pattern):
        return exp.fullmatch(got) is not None
    return exp == got


def _show(exp: "str | re.Pattern[str]") -> str:
    if isinstance(exp, re.Pattern):
        return "<motif> " + exp.pattern
    return exp


def compare_lines(expected: list, got: list[str]) -> Diff:
    """Compare ligne par ligne, y compris les lignes en trop / manquantes.

    Renvoie un Diff avec un affichage des deux côtés où la première
    différence est marquée."""
    n = max(len(expected), len(got))
    first = None
    for i in range(n):
        e = expected[i] if i < len(expected) else None
        g = got[i] if i < len(got) else None
        if e is None or g is None or not _match(e, g):
            first = i
            break
    if first is None:
        return Diff(True, False, None, "", "", "")
    trailing = len(expected) == len(got) and all(
        _match(e, g.rstrip()) or _match(e, g) or (
            isinstance(e, str) and e.rstrip() == g.rstrip())
        for e, g in zip(expected, got))
    lo = max(0, first - 3)
    hi = n
    exp_lines, got_lines = [], []
    for i in range(lo, hi):
        mark = "→" if i == first else " "
        if i < len(expected):
            exp_lines.append("%s%3d| %s" % (mark, i + 1,
                                            _show(expected[i])))
        else:
            exp_lines.append("%s%3d| (rien)" % (mark, i + 1))
        if i < len(got):
            g = got[i]
            if g != g.rstrip():
                g = g.rstrip() + "·" * (len(g) - len(g.rstrip()))
            got_lines.append("%s%3d| %s" % (mark, i + 1, g))
        else:
            got_lines.append("%s%3d| (ligne manquante)" % (mark, i + 1))
    if first >= len(got):
        summary = "Ligne %d manquante : %s" % (first + 1,
                                               _show(expected[first]))
    elif first >= len(expected):
        summary = "Ligne en trop %d : %r" % (first + 1, got[first])
    else:
        summary = "Ligne %d différente : attendu %r, obtenu %r" % (
            first + 1, _show(expected[first]), got[first])
    return Diff(False, trailing, first + 1, "\n".join(exp_lines),
                "\n".join(got_lines), summary)


def show_str(s: str) -> str:
    """repr lisible d'un prompt (espaces visibles)."""
    return repr(s)
