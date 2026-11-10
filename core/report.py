"""Résultats et affichage (rich)."""
from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

OK = "OK"
WARN = "AVERTISSEMENT"
KO = "KO"
_RANK = {OK: 0, WARN: 1, KO: 2}
_STYLE = {OK: "bold green", WARN: "bold yellow", KO: "bold red"}

console = Console(highlight=False)


@dataclass
class Issue:
    level: str
    title: str
    rule: str | None = None
    expected: str | None = None
    got: str | None = None
    detail: str | None = None
    file: str | None = None
    manual: str | None = None   # comment vérifier à la main


@dataclass
class ExerciseResult:
    ex_id: str
    title: str
    files: list[str]
    issues: list[Issue] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        level = OK
        for i in self.issues:
            if _RANK[i.level] > _RANK[level]:
                level = i.level
        return level


def _ellipsis(text: str, limit: int = 40) -> str:
    lines = text.splitlines()
    if len(lines) <= limit:
        return text
    half = limit // 2
    return "\n".join(lines[:half] + ["[... %d lignes ...]"
                                     % (len(lines) - limit)]
                     + lines[-half:])


def print_header(module_title: str, root: str) -> None:
    console.print(Panel(Text.assemble(("pyvision", "bold cyan"),
                                      "  ·  ", (module_title, "bold"),
                                      "\n", (root, "dim")),
                        expand=False))


def print_exercise_line(res: ExerciseResult, verbose: bool) -> None:
    status = res.status
    ko = sum(1 for i in res.issues if i.level == KO)
    warn = sum(1 for i in res.issues if i.level == WARN)
    counts = []
    if ko:
        counts.append("%d KO" % ko)
    if warn:
        counts.append("%d avert." % warn)
    line = Text.assemble((" %-4s " % res.ex_id, "bold"),
                         ("%-32s" % res.title[:32]),
                         (" %-14s" % status, _STYLE[status]),
                         (", ".join(counts), "dim"))
    console.print(line)
    if verbose:
        for p in res.passed:
            console.print(Text("        ✓ " + p, style="green"))
        for i in res.issues:
            console.print(Text("        %s %s" % (
                "✗" if i.level == KO else "!", i.title),
                style=_STYLE[i.level]))


def _issue_panel(ex: ExerciseResult, issue: Issue, verbose: bool) -> Panel:
    parts: list = []
    if issue.file:
        parts.append(Text("Fichier : " + issue.file, style="dim"))
    if issue.detail:
        parts.append(Text(issue.detail))
    limit = 200 if verbose else 40
    if issue.expected is None and issue.got is not None:
        parts.append(Text("Obtenu :", style="bold"))
        parts.append(Text(_ellipsis(issue.got, limit), style="red"))
    elif issue.expected is not None:
        table = Table(show_header=True, header_style="bold", expand=True,
                      box=None, padding=(0, 1))
        table.add_column("Attendu", style="green", ratio=1)
        table.add_column("Obtenu", style="red", ratio=1)
        table.add_row(Text(_ellipsis(issue.expected or "", limit)),
                      Text(_ellipsis(issue.got or "", limit)))
        parts.append(table)
    if issue.rule:
        parts.append(Text.assemble(("Règle du sujet : ", "bold"),
                                   ("« %s »" % issue.rule, "italic cyan")))
    if issue.manual:
        parts.append(Text.assemble(("À vérifier à la main : ", "bold"),
                                   issue.manual))
    return Panel(Group(*parts) if parts else Text(""),
                 title=Text("%s · %s · %s"
                            % (ex.ex_id, issue.level, issue.title),
                            style=_STYLE[issue.level]),
                 title_align="left", border_style=_STYLE[issue.level])


def print_final(results: list[ExerciseResult], verbose: bool) -> None:
    console.print()
    if any(r.issues for r in results):
        console.rule("[bold]Rapport détaillé")
        for level in (KO, WARN):
            for r in results:
                for i in r.issues:
                    if i.level == level:
                        console.print(_issue_panel(r, i, verbose))
    console.rule("[bold]Résumé")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Exercice")
    table.add_column("Statut")
    table.add_column("KO", justify="right")
    table.add_column("Avert.", justify="right")
    for r in results:
        table.add_row(r.ex_id + " " + r.title,
                      Text(r.status, style=_STYLE[r.status]),
                      str(sum(1 for i in r.issues if i.level == KO)),
                      str(sum(1 for i in r.issues if i.level == WARN)))
    console.print(table)
    ko = sum(1 for r in results if r.status == KO)
    warn = sum(1 for r in results if r.status == WARN)
    if ko:
        console.print(Text("%d exercice(s) en KO." % ko, style=_STYLE[KO]))
    elif warn:
        console.print(Text("Aucun KO, mais %d exercice(s) avec "
                           "avertissement(s) à vérifier." % warn,
                           style=_STYLE[WARN]))
    else:
        console.print(Text("Tout est OK.", style=_STYLE[OK]))
