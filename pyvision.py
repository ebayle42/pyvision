#!/usr/bin/env python3
"""pyvision : testeur des modules Python de 42 qui vérifie vraiment le
respect du sujet. Usage : se placer à la racine d'un module et lancer
`pyvision`."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True

from rich.prompt import Prompt  # noqa: E402

from core import report as R  # noqa: E402
from core.base import Module, run_exercise  # noqa: E402
from core.runner import Sandbox  # noqa: E402
from modules import load_modules  # noqa: E402

VERSION = "1.0"


def _pycache_dirs(root: Path) -> set[Path]:
    out = set()
    for dirpath, dirnames, _ in os.walk(root):
        if ".git" in dirnames:
            dirnames.remove(".git")
        for d in dirnames:
            if d == "__pycache__":
                out.add(Path(dirpath) / d)
    return out


def detect(modules: list[Module], root: Path, interactive: bool
           ) -> Module | None:
    scored = sorted(((m.detect(root), m) for m in modules),
                    key=lambda x: -x[0])
    scored = [(s, m) for s, m in scored if s > 0]
    if not scored:
        return None
    best_score, best = scored[0]
    close = [m for s, m in scored if s >= best_score - 0.15]
    if best_score >= 0.5 and len(close) == 1:
        return best
    if not interactive:
        return best
    R.console.print("[yellow]Module incertain[/yellow] d'après les "
                    "fichiers présents :")
    for s, m in scored[:5]:
        R.console.print("  %-6s %-40s (%d%% des fichiers trouvés)"
                        % (m.id, m.title, int(s * 100)))
    choice = Prompt.ask("Quel module tester ?",
                        choices=[m.id for m in modules],
                        default=best.id)
    return next(m for m in modules if m.id == choice)


def update() -> int:
    if (HERE / ".git").exists():
        R.console.print("Mise à jour de pyvision (git pull)...")
        code = subprocess.call(["git", "-C", str(HERE), "pull", "--ff-only"])
        if code != 0:
            return code
    else:
        R.console.print("[yellow]pyvision n'a pas été installé depuis git :"
                        " impossible de télécharger une mise à jour. "
                        "Réinstallation des dépendances seulement.")
    return subprocess.call([str(HERE / "install.sh")])


def main(argv: list[str] | None = None) -> int:
    modules = load_modules()
    ap = argparse.ArgumentParser(
        prog="pyvision",
        description="Testeur des modules Python de 42 (sujet vérifié pour "
                    "de vrai). Lancez-le à la racine d'un module.")
    ap.add_argument("exercises", nargs="*", metavar="exN",
                    help="exercice(s) à tester (défaut : tous)")
    ap.add_argument("-m", "--module", help="forcer le module (%s)"
                    % ", ".join(m.id for m in modules))
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="afficher le détail de chaque vérification")
    ap.add_argument("-u", "--update", action="store_true",
                    help="mettre à jour pyvision")
    ap.add_argument("-C", "--directory", default=".",
                    help="dossier du module (défaut : dossier courant)")
    ap.add_argument("--json", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--version", action="version", version=VERSION)
    args = ap.parse_args(argv)

    if args.update:
        return update()

    root = Path(args.directory).resolve()
    interactive = sys.stdin.isatty() and not args.json
    if args.module:
        mid = args.module.lower().removeprefix("module").lstrip("_ ")
        module = next((m for m in modules if m.id == mid
                       or m.id == mid.zfill(2)), None)
        if module is None:
            R.console.print("[red]Module inconnu : %s. Modules : %s"
                            % (args.module, ", ".join(m.id for m in
                                                      modules)))
            return 2
    else:
        module = detect(modules, root, interactive)
        if module is None and detect(modules, root.parent, False):
            R.console.print("[yellow]Aucun module ici ; je teste le "
                            "dossier parent %s" % root.parent)
            root = root.parent
            module = detect(modules, root, interactive)
        if module is None:
            R.console.print("[red]Aucun module Python reconnu dans %s.[/]\n"
                            "Placez-vous à la racine du module (le dossier "
                            "qui contient ex0/, ex1/...) ou utilisez -m."
                            % root)
            return 2

    selected = module.exercises
    if args.exercises:
        wanted = [e.lower() for e in args.exercises]
        wanted = ["ex" + w if w.isdigit() else w for w in wanted]
        selected = [e for e in module.exercises if e.ex_id in wanted]
        unknown = set(wanted) - {e.ex_id for e in selected}
        if unknown:
            R.console.print("[red]Exercice(s) inconnu(s) : %s"
                            % ", ".join(sorted(unknown)))
            return 2

    before = _pycache_dirs(root)
    sandbox = Sandbox(root)
    results = []
    try:
        if not args.json:
            R.print_header("Module %s · %s" % (module.id, module.title),
                           str(root))
        for ex in selected:
            if not args.json:
                with R.console.status("Test de %s..." % ex.ex_id):
                    res = run_exercise(module, ex, sandbox, root,
                                       args.verbose)
                R.print_exercise_line(res, args.verbose)
            else:
                res = run_exercise(module, ex, sandbox, root, args.verbose)
            results.append(res)
    finally:
        sandbox.cleanup()
        for d in _pycache_dirs(root) - before:
            shutil.rmtree(d, ignore_errors=True)
    if args.json:
        print(json.dumps({"module": module.id, "results": [
            {"ex": r.ex_id, "status": r.status,
             "issues": [{"level": i.level, "title": i.title}
                        for i in r.issues]} for r in results]}))
    else:
        R.print_final(results, args.verbose)
    return 1 if any(r.status == R.KO for r in results) else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
