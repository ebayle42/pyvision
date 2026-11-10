"""Base commune : description d'un module / exercice et contexte de test.

Un module (modules/module_XX.py) décrit ses exercices en héritant de
`Exercise` et de `Module`. Les vérifications génériques (fichiers, flake8,
mypy, type hints, fonctions et imports autorisés, bloc __main__) sont
faites ici ; chaque exercice ajoute ses vérifications propres dans
`check()`.
"""
from __future__ import annotations

import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any, Iterable

from . import analysis as A
from .compare import compare_lines
from .report import KO, OK, WARN, ExerciseResult, Issue
from .runner import IGNORED_DIRS, RunResult, Sandbox, is_venv_dir, \
    run_harness, run_tool

# Fichiers jamais signalés comme « en trop ».
IGNORED_FILES = {".DS_Store", "Thumbs.db", ".gitkeep"}
TOOLS_FILES = {"main.py"}


class Exercise:
    ex_id: str = "ex?"
    title: str = ""
    directory: str = ""                 # "" = racine du rendu
    files: list[str] = []               # relatifs à `directory`
    optional_files: list[str] = []      # tolérés en plus
    # Fonctions natives autorisées (None = toutes sauf `forbidden`).
    authorized: set[str] | None = None
    authorized_line: str = ""           # citation "Authorized: ..."
    forbidden: set[str] = set()         # fonctions natives interdites
    # Modules importables (None = pas de restriction). Préfixes acceptés.
    imports: set[str] | None = None
    local_imports: bool = False         # imports de fichiers du rendu OK
    type_hints: str = "required"        # required | recommended | none
    mypy_errors_expected: bool = False  # le sujet annonce une erreur mypy
    # Regex des erreurs mypy volontaires annoncées par le sujet : elles
    # sont acceptées, les autres sont traitées normalement.
    mypy_expected: str | None = None
    # Fonctions natives non listées mais tolérées (AVERTISSEMENT seulement).
    tolerated: set[str] = set()
    mypy_note: str = ""
    main_guard: str = "allowed"         # forbidden | required | allowed
    check_extra_files: bool = True
    # Motifs glob (relatifs à `directory`) de fichiers .py supplémentaires à
    # analyser (flake8, mypy, ast), ex : "ex3/*.py".
    glob_files: list[str] = []

    def check(self, ctx: "Ctx") -> None:  # pragma: no cover - surcharge
        pass


class Module:
    id: str = "??"
    title: str = ""
    pdf: str = ""
    signature: list[str] = []           # chemins typiques du rendu
    exercises: list[Exercise] = []
    flake8_rule: str = "Your code must respect the flake8 linter standards."
    hints_rule: str = ""
    only_requested_rule: str = ("You need to submit only the files "
                                "requested by the subject of this project.")
    python: str | None = None           # interpréteur pour le code élève

    def detect(self, root: Path) -> float:
        if not self.signature:
            return 0.0
        found = sum(1 for p in self.signature if (root / p).exists())
        return found / len(self.signature)

    def exercise(self, ex_id: str) -> Exercise | None:
        for e in self.exercises:
            if e.ex_id == ex_id:
                return e
        return None


class Ctx:
    """Contexte d'un exercice : accès aux fichiers (copie de travail),
    exécution, comparaison et enregistrement des problèmes."""

    def __init__(self, module: Module, ex: Exercise, sandbox: Sandbox,
                 root: Path, verbose: bool = False) -> None:
        self.module = module
        self.ex = ex
        self.sandbox = sandbox
        self.root = root                  # dossier réel de l'élève
        self.work = sandbox.work          # copie de travail
        self.verbose = verbose
        self.result = ExerciseResult(ex.ex_id, ex.title, list(ex.files))
        self._sources: dict[str, A.Source] = {}
        self.stop = False

    # ---------------------------------------------------------------- issues
    def ko(self, title: str, rule: str | None = None, **kw: Any) -> None:
        self.result.issues.append(Issue(KO, title, rule, **kw))

    def warn(self, title: str, rule: str | None = None, **kw: Any) -> None:
        self.result.issues.append(Issue(WARN, title, rule, **kw))

    def issue(self, strict: bool, title: str, rule: str | None = None,
              **kw: Any) -> None:
        (self.ko if strict else self.warn)(title, rule, **kw)

    def ok(self, msg: str) -> None:
        self.result.passed.append(msg)

    def has_ko(self) -> bool:
        return any(i.level == KO for i in self.result.issues)

    # ----------------------------------------------------------------- files
    def rel(self, name: str) -> str:
        return os.path.join(self.ex.directory, name) if self.ex.directory \
            else name

    def path(self, name: str) -> Path:
        return self.work / self.rel(name)

    def real_path(self, name: str) -> Path:
        return self.root / self.rel(name)

    def exists(self, name: str) -> bool:
        return self.path(name).exists()

    def src(self, name: str) -> A.Source:
        if name not in self._sources:
            p = self.path(name)
            try:
                text = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                self._sources[name] = A.Source(str(p), "", None, str(e))
            else:
                self._sources[name] = A.parse(self.rel(name), text)
        return self._sources[name]

    def tree(self, name: str) -> Any:
        """Arbre ast du fichier (ast.Module), ou un module vide."""
        t = self.src(name).tree
        return t if t is not None else A.ast.Module(body=[], type_ignores=[])

    # ------------------------------------------------------------- execution
    def run(self, name: str, argv: list[str] | None = None,
            inputs: list[str] | None = None, stdin: str | None = None,
            stdin_echo: bool = False, files: dict[str, str] | None = None,
            timeout: float = 5.0, cwd: str | None = None,
            python: str | None = None,
            env: dict[str, str | None] | None = None,
            patch_input: bool = True, argv0: str | None = None,
            setup: Any = None) -> RunResult:
        """Exécute `python3 name argv...` dans une copie neuve du rendu.

        - inputs : réponses rejouées par le faux input() (None = stdin)
        - stdin / stdin_echo : contenu de l'entrée standard
        - files : fichiers de test à créer (relatifs au dossier courant)
        - cwd : dossier courant relatif à la racine (défaut : celui du
          fichier)
        """
        base = self.sandbox.fresh_copy()
        script = base / self.rel(name)
        workdir = base / (cwd if cwd is not None else
                          os.path.dirname(self.rel(name)))
        for fname, content in (files or {}).items():
            fp = Path(fname) if os.path.isabs(fname) else workdir / fname
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
        if setup is not None:
            setup(workdir)
        cfg: dict[str, Any] = {
            "mode": "script", "script": str(script), "argv": argv or [],
            "inputs": inputs, "patch_input": patch_input,
            "argv0": argv0 if argv0 is not None else os.path.relpath(
                script, workdir)}
        if stdin_echo:
            cfg["stdin_echo"] = stdin or ""
        res = run_harness(cfg, workdir, self.sandbox.base / "h",
                          timeout=timeout,
                          python=python or self.module.python,
                          env_extra=env, stdin_data=stdin)
        res.meta["workdir"] = str(workdir)
        return res

    def probe(self, code: str, timeout: float = 15.0,
              python: str | None = None, env: dict[str, str] | None = None,
              files: dict[str, str] | None = None) -> RunResult:
        """Exécute du code de test qui importe le code de l'élève.

        Le code dispose de : EX (dossier de l'exercice), ROOT (racine),
        load(path), capture(fn, *args, inputs=[...]), run_main(path,
        argv, inputs), report(clé, valeur)."""
        base = self.sandbox.fresh_copy()
        exdir = base / self.ex.directory if self.ex.directory else base
        for fname, content in (files or {}).items():
            fp = exdir / fname
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
        head = "import os, sys\nEX = %r\nROOT = %r\nos.chdir(EX)\n" % (
            str(exdir), str(base))
        cfg = {"mode": "probe", "probe": head + textwrap.dedent(code),
               "sys_path": [str(exdir), str(base)], "inputs": []}
        res = run_harness(cfg, exdir, self.sandbox.base / "h",
                          timeout=timeout,
                          python=python or self.module.python,
                          env_extra=env)
        if res.timeout or res.killed:
            self.ko("Les tests de comportement ne se terminent pas : "
                    + ("délai dépassé" if res.timeout else "processus "
                       "arrêté"),
                    detail=(res.killed or "Délai de %ss dépassé pendant "
                            "les appels directs aux fonctions/classes "
                            "(boucle infinie ?)." % timeout),
                    got=res.stdout[-800:] or None)
        elif res.meta.get("probe_error"):
            self.warn("Test de comportement interrompu",
                      detail="Erreur interne du test (souvent une "
                             "signature inattendue) :\n"
                             + str(res.meta["probe_error"])[-1500:])
        return res

    def call(self, name: str, func: str, scenarios: list[dict[str, Any]],
             timeout: float = 15.0) -> list[dict[str, Any]] | None:
        """Importe `name` et appelle `func` pour chaque scénario
        {args, kwargs, inputs}. Renvoie la liste des résultats capturés
        (out, prompts, exc, value...) ou None si l'import échoue."""
        code = """
        import json
        SC = json.loads(%r)
        try:
            m = load(os.path.join(EX, %r))
        except ImportError as e:
            report("import_error", str(e))
        else:
            report("import_out", m.__pyvision_import_output__)
            fn = getattr(m, %r, None)
            report("exists", callable(fn))
            out = []
            if callable(fn):
                for sc in SC:
                    c = capture(fn, *sc.get("args", []),
                                inputs=sc.get("inputs", []),
                                **sc.get("kwargs", {}))
                    out.append(c.as_dict())
            report("results", out)
        """ % (__import__("json").dumps(scenarios), name, func)
        res = self.probe(code, timeout=timeout)
        p = res.probe
        if res.timeout or res.killed:
            return None
        if "import_error" in p:
            self.ko("Impossible d'importer " + self.rel(name),
                    got=p["import_error"], file=self.rel(name),
                    rule="Your programs must always run without errors")
            return None
        if not p.get("exists"):
            self.ko("Fonction %s() introuvable" % func,
                    "Function names must match exactly what is requested.",
                    file=self.rel(name))
            return None
        out = p.get("results")
        return out if isinstance(out, list) else None

    def expect_calls(self, name: str, cases: list[dict[str, Any]],
                     timeout: float = 20.0) -> None:
        """Appels directs déclaratifs. Chaque cas :
          call    : "fonction" ou "Classe.méthode" (attribut pointé)
          args    : arguments (JSON)
          returns : valeur attendue (facultatif)
          raises  : nom d'exception attendu, ou "*" pour n'importe laquelle
          message : str(exception) attendu (facultatif)
          out     : lignes attendues sur la sortie (facultatif)
          no_raise: True pour exiger l'absence d'exception
          rule    : phrase du sujet ; label : description
          strict  : False -> AVERTISSEMENT au lieu de KO
        """
        import json as _json
        code = """
        import json
        CASES = json.loads(%r)
        try:
            m = load(os.path.join(EX, %r))
        except ImportError as e:
            report("import_error", str(e))
        else:
            out = []
            for c in CASES:
                obj, missing = m, None
                for part in c["call"].split("."):
                    if not hasattr(obj, part):
                        missing = part
                        break
                    obj = getattr(obj, part)
                if missing is not None or not callable(obj):
                    out.append({"missing": True})
                    continue
                r = capture(obj, *c.get("args", []),
                            inputs=c.get("inputs", []),
                            **c.get("kwargs", {}))
                d = r.as_dict()
                d["exc_msg"] = str(r.exc_obj) if r.exc_obj is not None \\
                    else None
                d["exc_mro"] = [k.__name__ for k in type(r.exc_obj).__mro__] \\
                    if r.exc_obj is not None else []
                d["value_repr"] = repr(r.value)
                out.append(d)
            report("results", out)
        """ % (_json.dumps(cases), name)
        res = self.probe(code, timeout=timeout)
        p = res.probe
        if res.timeout or res.killed:
            return
        if "import_error" in p:
            self.ko("Impossible d'importer " + self.rel(name),
                    got=p["import_error"], file=self.rel(name))
            return
        for c, r in zip(cases, p.get("results", [])):
            label = c.get("label") or "%s(%s)" % (
                c["call"], ", ".join(repr(a) for a in c.get("args", [])))
            strict = c.get("strict", True)
            rule = c.get("rule")
            f = self.rel(name)
            if r.get("missing"):
                self.ko("%s introuvable" % c["call"], rule, file=f,
                        detail="Nom exact attendu : %s" % c["call"])
                continue
            if r["timeout"]:
                self.ko(label + " : délai dépassé", rule, file=f,
                        got=r["out"][-800:])
                continue
            if "raises" in c:
                want = c["raises"]
                if not r["exc_type"] or r["exc_type"] in (
                        "InputExhausted", "Timeout"):
                    self.issue(strict, label + " : aucune exception levée",
                               rule, file=f,
                               expected="exception %s" % (
                                   want if want != "*" else ""),
                               got="renvoie %s" % r["value_repr"])
                    continue
                if want != "*" and want not in r["exc_mro"]:
                    self.issue(strict, label + " : mauvaise exception", rule,
                               file=f, expected=want, got=r["exc"])
                    continue
                if "message" in c and r["exc_msg"] != c["message"]:
                    self.issue(strict, label + " : message d'erreur "
                               "différent", rule, file=f,
                               expected=c["message"], got=r["exc_msg"])
                    continue
            elif r["exc"]:
                self.issue(strict, label + " : exception inattendue", rule,
                           file=f, got=r["exc"])
                continue
            if "returns" in c and not (
                    r["value"] == c["returns"]
                    and type(r["value"]) is type(c["returns"])):
                self.issue(strict, label + " : valeur renvoyée incorrecte",
                           rule, file=f, expected=repr(c["returns"]),
                           got=r["value_repr"])
                continue
            if "out" in c:
                if not self.compare(label, c["out"], r["out"].splitlines(),
                                    rule, strict=strict, file=f):
                    continue
            self.ok(label)

    # ------------------------------------------------------------ comparison
    def compare(self, label: str, expected: list, got: list[str],
                rule: str | None, strict: bool = True,
                file: str | None = None, detail: str | None = None
                ) -> bool:
        d = compare_lines(expected, got)
        if d.ok:
            self.ok(label + " : sortie conforme")
            return True
        if d.only_trailing_spaces:
            self.warn(label + " : espaces en fin de ligne", rule,
                      expected=d.expected, got=d.got, file=file,
                      detail="Seuls des espaces invisibles en fin de ligne"
                             " diffèrent (· = espace).")
            return True
        self.issue(strict, label + " : sortie différente du sujet", rule,
                   expected=d.expected, got=d.got, file=file,
                   detail=(detail + "\n" if detail else "") + d.summary)
        return False

    def check_prompts(self, label: str, expected: list[str],
                      got: list[str], rule: str | None,
                      file: str | None = None, strict: bool = True
                      ) -> bool:
        if not got:
            self.issue(strict, label + " : input() n'est jamais appelé",
                       rule, expected="\n".join(repr(p) for p in expected),
                       got="(aucun appel à input())", file=file,
                       detail="La sortie est peut-être écrite en dur : le "
                              "sujet demande de lire une saisie.")
            return False
        if got[:len(expected)] != expected or len(got) != len(expected):
            self.issue(strict, label + " : texte du prompt incorrect", rule,
                       expected="\n".join(repr(p) for p in expected),
                       got="\n".join(repr(p) for p in got), file=file,
                       detail="Les prompts sont comparés caractère par "
                              "caractère (espaces compris).")
            return False
        self.ok(label + " : prompts exacts")
        return True

    def check_crash(self, label: str, res: RunResult, rule: str | None,
                    file: str | None = None, strict: bool = True) -> bool:
        """KO propre si l'exécution a planté / bouclé."""
        if res.timeout or res.killed:
            self.ko(label + " : " + ("délai dépassé" if res.timeout
                                     else "processus arrêté"), rule,
                    got=res.stdout[-1500:], detail=res.crash_text(),
                    file=file)
            return False
        if res.exception:
            self.issue(strict, label + " : le programme plante", rule,
                       got=res.crash_text(), file=file)
            return False
        return True

    def crash_rule(self) -> str:
        return ""


# ====================================================================
# Vérifications génériques
# ====================================================================

def list_files(directory: Path) -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS
                       and not is_venv_dir(Path(dirpath) / d)]
        for f in filenames:
            if f not in IGNORED_FILES:
                out.append(Path(dirpath) / f)
    return out


def _flake8(ctx: Ctx, pyfiles: list[str]) -> None:
    cmd = [sys.executable, "-m", "flake8", "--isolated"]
    code, out = run_tool(cmd + [ctx.rel(f) for f in pyfiles], ctx.work)
    if code == -2 or "No module named flake8" in out:
        ctx.warn("flake8 introuvable", detail="Relancez ./install.sh.")
        return
    if code != 0 and out:
        ctx.ko("flake8 : erreurs de style", ctx.module.flake8_rule,
               got=out, detail="Corrigez toutes les erreurs signalées par "
                               "flake8 (sans configuration locale).")
    else:
        ctx.ok("flake8 : aucune erreur")


def _mypy(ctx: Ctx, pyfiles: list[str]) -> None:
    ex = ctx.ex
    if ex.type_hints == "none":
        return
    outputs = []
    for f in pyfiles:
        cmd = [sys.executable, "-m", "mypy", "--cache-dir",
               str(ctx.sandbox.mypy_cache), "--no-error-summary",
               "--no-color-output", "--ignore-missing-imports",
               "--follow-imports=silent", ctx.rel(f)]
        code, out = run_tool(cmd, ctx.work)
        if "No module named mypy" in out:
            ctx.warn("mypy introuvable", detail="Relancez ./install.sh.")
            return
        lines = [ln for ln in out.splitlines()
                 if ": error:" in ln or ": note:" not in ln and ln.strip()]
        lines = [ln for ln in lines if ": error:" in ln]
        if lines:
            outputs.extend(lines)
    if ex.mypy_expected:
        rx_ = re.compile(ex.mypy_expected)
        accepted = [ln for ln in outputs if rx_.search(ln)]
        outputs = [ln for ln in outputs if not rx_.search(ln)]
        if accepted:
            ctx.ok("mypy : erreur volontaire annoncée par le sujet ("
                   + accepted[0].split(": error: ")[-1] + ")")
        if not outputs:
            return
        got = "\n".join(outputs)
        if ex.type_hints == "required":
            ctx.ko("mypy : erreurs de typage", ctx.module.hints_rule,
                   got=got, detail="En plus de l'erreur volontaire "
                                   "annoncée par le sujet.")
        else:
            ctx.warn("mypy : erreurs de typage", ctx.module.hints_rule,
                     got=got)
        return
    if not outputs:
        ctx.ok("mypy : aucune erreur")
        return
    got = "\n".join(outputs)
    if ex.mypy_errors_expected:
        ctx.warn("mypy : erreurs (une erreur est attendue par le sujet)",
                 ex.mypy_note or None, got=got,
                 detail="Le sujet annonce une erreur mypy volontaire dans "
                        "cet exercice : vérifiez que seules les erreurs "
                        "attendues apparaissent.")
    elif ex.type_hints == "required":
        ctx.ko("mypy : erreurs de typage", ctx.module.hints_rule, got=got)
    else:
        ctx.warn("mypy : erreurs de typage (type hints seulement "
                 "recommandés)", ctx.module.hints_rule, got=got)


def _hints(ctx: Ctx, pyfiles: list[str]) -> None:
    ex = ctx.ex
    if ex.type_hints == "none":
        return
    missing = []
    for f in pyfiles:
        for name, line, what in A.missing_annotations(ctx.tree(f)):
            missing.append("%s:%d %s() : %s"
                           % (ctx.rel(f), line, name, what))
    if not missing:
        ctx.ok("type hints présents partout")
        return
    if ex.type_hints == "required":
        ctx.ko("Type hints manquants", ctx.module.hints_rule,
               got="\n".join(missing))
    else:
        ctx.warn("Type hints manquants (recommandés)",
                 ctx.module.hints_rule, got="\n".join(missing))


def _builtins(ctx: Ctx, pyfiles: list[str]) -> None:
    ex = ctx.ex
    bad: list[str] = []
    tolerated: list[str] = []
    skip = {"True", "False", "None", "NotImplemented", "Ellipsis",
            "__name__", "__file__"}
    for f in pyfiles:
        tree = ctx.tree(f)
        for name, line in A.builtin_calls(tree) + A.builtin_refs(tree):
            if name in skip:
                continue
            if name in ex.forbidden:
                bad.append("%s:%d %s()" % (ctx.rel(f), line, name))
            elif name in ex.tolerated and (ex.authorized is None or name
                                           not in ex.authorized):
                tolerated.append("%s:%d %s()" % (ctx.rel(f), line, name))
            elif ex.authorized is not None and name not in ex.authorized \
                    and name not in A.EXCEPTION_NAMES:
                bad.append("%s:%d %s()" % (ctx.rel(f), line, name))
    if tolerated:
        ctx.warn("Fonction non listée dans les fonctions autorisées",
                 ex.authorized_line or None,
                 got="\n".join(sorted(set(tolerated))),
                 detail="Elle n'apparaît pas dans « Authorized » mais fait "
                        "partie des bases déjà vues (ex : super() pour "
                        "hériter) : à justifier en évaluation.")
    if bad:
        ctx.ko("Fonction non autorisée utilisée",
               ex.authorized_line or None, got="\n".join(sorted(set(bad))))
    else:
        ctx.ok("uniquement des fonctions autorisées")


def _local_module_names(ctx: Ctx) -> set[str]:
    names = set()
    for p in list_files(ctx.work):
        rel = p.relative_to(ctx.work)
        if p.suffix == ".py":
            names.add(rel.parts[0].removesuffix(".py"))
            names.add(p.stem)
    for d in ctx.work.iterdir():
        if d.is_dir():
            names.add(d.name)
    return names


def _imports(ctx: Ctx, pyfiles: list[str]) -> None:
    ex = ctx.ex
    if ex.imports is None:
        return
    local = _local_module_names(ctx) if ex.local_imports else set()
    bad = []
    for f in pyfiles:
        for imp in A.imports(ctx.tree(f)):
            if imp.level > 0:
                if not ex.local_imports:
                    bad.append("%s:%d import relatif %s" % (
                        ctx.rel(f), imp.lineno, imp.module))
                continue
            full = imp.module
            if full == "__future__":
                continue
            ok = any(full == m or full.startswith(m + ".")
                     for m in ex.imports)
            if not ok and imp.kind == "from":
                ok = any(full + "." + n in ex.imports for n in imp.names)
            if not ok and imp.root in local:
                ok = True
            if not ok:
                bad.append("%s:%d import %s" % (ctx.rel(f), imp.lineno,
                                                full))
    if bad:
        ctx.ko("Import non autorisé", ex.authorized_line or None,
               got="\n".join(bad))
    else:
        ctx.ok("imports autorisés")


def _main_guard(ctx: Ctx, pyfiles: list[str]) -> None:
    ex = ctx.ex
    if ex.main_guard == "allowed":
        return
    for f in pyfiles:
        tree = ctx.tree(f)
        guard = A.main_guard(tree)
        if ex.main_guard == "forbidden":
            if guard is not None:
                ctx.ko("Bloc if __name__ == \"__main__\" interdit",
                       'Do not write if __name__ == "__main__": blocks, do '
                       'not call the function directly in your file, do not'
                       ' write code outside functions.',
                       file=ctx.rel(f), got=ctx.src(f).segment(guard))
            code = [n for n in A.toplevel_code(tree) if n is not guard]
            if code:
                ctx.ko("Code en dehors de la fonction",
                       'Do not write if __name__ == "__main__": blocks, do '
                       'not call the function directly in your file, do not'
                       ' write code outside functions.', file=ctx.rel(f),
                       got="\n".join(ctx.src(f).segment(n) for n in code))
            if guard is None and not code:
                ctx.ok("pas de bloc __main__ ni de code hors fonction")
        elif ex.main_guard == "required":
            if guard is None:
                ctx.ko("Bloc if __name__ == \"__main__\": absent",
                       'Use the special if __name__ == "__main__": '
                       'pattern.', file=ctx.rel(f))
            else:
                ctx.ok("bloc __main__ présent")


def _extra_files(ctx: Ctx) -> None:
    ex = ctx.ex
    if not ex.directory or not ex.check_extra_files:
        return
    d = ctx.real_path("")
    if not d.is_dir():
        return
    expected = {os.path.normpath(f) for f in ex.files + ex.optional_files}
    extra = []
    for p in list_files(d):
        rel = os.path.normpath(str(p.relative_to(d)))
        if rel in expected or p.name in TOOLS_FILES:
            continue
        extra.append(rel)
    if extra:
        ctx.warn("Fichiers non demandés dans %s/" % ex.directory,
                 ctx.module.only_requested_rule, got="\n".join(sorted(extra)),
                 detail="Ils ne font pas partie des fichiers à rendre. "
                        "Vérifiez qu'ils ne sont pas commités.")


def run_exercise(module: Module, ex: Exercise, sandbox: Sandbox,
                 root: Path, verbose: bool = False) -> ExerciseResult:
    ctx = Ctx(module, ex, sandbox, root, verbose)
    missing = [f for f in ex.files if not ctx.exists(f)]
    for f in missing:
        ctx.ko("Fichier manquant : " + ctx.rel(f),
               "Files to Submit: " + ", ".join(ex.files),
               detail="Vérifiez le nom exact du fichier et du dossier.")
    present = [f for f in ex.files if f not in missing]
    if not present:
        return ctx.result
    _extra_files(ctx)
    pyfiles = [f for f in present if f.endswith(".py")]
    base_dir = ctx.path("")
    for pattern in ex.glob_files:
        for p in sorted(base_dir.glob(pattern)):
            rel = str(p.relative_to(base_dir))
            if rel not in pyfiles and "__pycache__" not in rel:
                pyfiles.append(rel)
    broken = False
    for f in pyfiles:
        s = ctx.src(f)
        if s.tree is None:
            ctx.ko("Le fichier ne se compile pas", file=ctx.rel(f),
                   got=s.error, rule="Your programs must always run "
                                     "without errors")
            broken = True
    if broken:
        return ctx.result
    if pyfiles:
        _flake8(ctx, pyfiles)
        _hints(ctx, pyfiles)
        _mypy(ctx, pyfiles)
        _builtins(ctx, pyfiles)
        _imports(ctx, pyfiles)
        _main_guard(ctx, pyfiles)
    if missing:
        return ctx.result
    try:
        ex.check(ctx)
    except Exception as e:  # erreur interne du testeur : ne pas planter
        import traceback
        ctx.warn("Erreur interne de pyvision pendant ce test",
                 detail="%s\n%s" % (e, traceback.format_exc()[-1500:]))
    return ctx.result


# ====================================================================
# Petits utilitaires pour écrire les modules
# ====================================================================

def lines(text: str) -> list[str]:
    """Bloc d'exemple du sujet -> liste de lignes (indentation commune
    retirée, première/dernière ligne vide ignorées)."""
    text = textwrap.dedent(text)
    out = text.split("\n")
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1].strip() == "":
        out.pop()
    return out


def rx(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


def first_line_matching(lines_: Iterable[str], pattern: str
                        ) -> re.Match[str] | None:
    r = re.compile(pattern)
    for ln in lines_:
        m = r.search(ln)
        if m:
            return m
    return None


__all__ = ["Exercise", "Module", "Ctx", "run_exercise", "lines", "rx",
           "first_line_matching", "OK", "KO", "WARN", "A"]


def check_script(ctx: Ctx, file: str, expected: list | None,
                 rule: str | None, strict: bool = True,
                 argv: list[str] | None = None,
                 inputs: list[str] | None = None,
                 label: str | None = None, crash_rule: str | None = None,
                 must_exit_zero: bool = True, **kw: Any) -> RunResult:
    """Lance `python3 file argv...`, signale plantage / boucle infinie et
    compare la sortie à `expected` (si fourni)."""
    res = ctx.run(file, argv=argv, inputs=inputs, **kw)
    label = (label or "python3 %s %s" % (
        os.path.basename(file), " ".join(argv or []))).rstrip()
    if res.timeout or res.killed:
        ctx.ko(label + " : " + ("délai dépassé" if res.timeout else
                                "processus arrêté"), crash_rule,
               got=res.stdout[-1500:] or None, detail=res.crash_text(),
               file=ctx.rel(file))
        return res
    if res.exception and res.exception.get("type") == "InputExhausted":
        ctx.ko(label + " : input() appelé plus de fois que prévu",
               crash_rule, got=res.stdout[-1500:], file=ctx.rel(file))
        return res
    if res.exception or (must_exit_zero and res.returncode not in (0,
                                                                   None)):
        ctx.ko(label + " : le programme plante", crash_rule,
               got=(res.stdout[-800:] + "\n" + (
                   res.crash_text() or res.stderr[-800:])).strip(),
               file=ctx.rel(file))
        return res
    if expected is not None:
        ctx.compare(label, expected, res.lines(), rule, strict=strict,
                    file=ctx.rel(file))
    return res
