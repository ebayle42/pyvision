"""Module 05bis : The Codex (Packages, Environments and the Alchemist's
Toolchain)."""
from __future__ import annotations

import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines

SYS_PATH_RULE = "It is forbidden to modify sys.path anywhere in this project."
NO_SUBMIT = ("Place the expected file tree at the root of your Git "
             "repository, and do not submit any virtual environment or .env "
             "file.")
OWN_IMPORTS = ("Authorized: builtins, standard types, and only the modules "
               "you create in this project")
CONFIG_VARS = ["MATRIX_MODE", "DATABASE_URL", "API_KEY", "LOG_LEVEL",
               "ZION_ENDPOINT"]


# ---------------------------------------------------------------- outils
def git_tracked(root: Path) -> set[str] | None:
    """Fichiers suivis par git (relatifs à root), None hors dépôt."""
    try:
        proc = subprocess.run(["git", "-C", str(root), "ls-files", "-z"],
                              capture_output=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return {p for p in proc.stdout.decode(errors="replace").split("\0") if p}


def base_python() -> str | None:
    """Interpréteur Python système (hors venv)."""
    cands = [getattr(sys, "_base_executable", None),
             os.path.join(sys.base_prefix, "bin", "python3"),
             shutil.which("python3")]
    for c in cands:
        if not c or not os.path.exists(c):
            continue
        try:
            out = subprocess.run(
                [c, "-I", "-c", "import sys; print(sys.prefix != "
                 "sys.base_prefix)"], capture_output=True, text=True,
                timeout=20).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            continue
        if out == "False":
            return c
    return None


def make_venv(base: Path, name: str = "lab_env") -> Path | None:
    py = base_python()
    if py is None:
        return None
    dest = base / name
    proc = subprocess.run([py, "-m", "venv", "--without-pip", str(dest)],
                          capture_output=True, timeout=120)
    if proc.returncode != 0:
        return None
    return dest


FAKE_LIB = '''"""Faux paquet installé par pyvision (test hors réseau)."""
__version__ = %r


class _Any:
    def __init__(self, *a, **k):
        pass

    def __call__(self, *a, **k):
        return _Any()

    def __getattr__(self, name):
        return _Any()

    def __iter__(self):
        return iter([])

    def __repr__(self):
        return "<pyvision-fake>"


def __getattr__(name):
    return _Any()
'''


def install_fake(venv: Path, libs: dict[str, str]) -> None:
    py = venv / "bin" / "python"
    site = subprocess.run([str(py), "-I", "-c", "import sysconfig; print("
                           "sysconfig.get_paths()['purelib'])"],
                          capture_output=True, text=True,
                          timeout=30).stdout.strip()
    sp = Path(site)
    sp.mkdir(parents=True, exist_ok=True)
    for name, version in libs.items():
        pkg = sp / name
        pkg.mkdir(exist_ok=True)
        (pkg / "__init__.py").write_text(FAKE_LIB % version)
        info = sp / ("%s-%s.dist-info" % (name, version))
        info.mkdir(exist_ok=True)
        (info / "METADATA").write_text("Metadata-Version: 2.1\nName: %s\n"
                                       "Version: %s\n" % (name, version))
        (info / "RECORD").write_text("")
        (info / "INSTALLER").write_text("pip\n")


def requirement_names(text: str) -> set[str]:
    out = set()
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"[A-Za-z0-9_.\-]+", line)
        if m:
            out.add(m.group(0).lower().replace("_", "-"))
    return out


def pyproject_deps(text: str) -> tuple[set[str] | None, str | None]:
    try:
        import tomllib
    except ImportError:  # Python 3.10
        names = set(re.findall(r'^\s*"?([A-Za-z0-9_.\-]+)"?\s*=',
                               text, re.M))
        names |= {m.group(1) for m in re.finditer(
            r'"([A-Za-z0-9_.\-]+)\s*[<>=~!]', text)}
        return {n.lower() for n in names} - {"python", "name", "version",
                                             "description"}, None
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        return None, str(e)
    deps: set[str] = set()
    poetry = data.get("tool", {}).get("poetry", {})
    for key in ("dependencies",):
        deps |= {k.lower() for k in poetry.get(key, {})}
    for group in poetry.get("group", {}).values():
        deps |= {k.lower() for k in group.get("dependencies", {})}
    for spec in data.get("project", {}).get("dependencies", []):
        m = re.match(r"[A-Za-z0-9_.\-]+", spec)
        if m:
            deps.add(m.group(0).lower())
    deps.discard("python")
    return {d.replace("_", "-") for d in deps}, None


def gitignore_ignores(text: str, name: str) -> bool:
    ignored = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        neg = line.startswith("!")
        pat = line[1:] if neg else line
        pat = pat.lstrip("/").rstrip("/")
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(name, "*/" + pat):
            ignored = not neg
    return ignored


class M05Exercise(Exercise):
    type_hints = "required"
    forbidden = {"eval", "exec"}

    def check(self, ctx: Ctx) -> None:
        bad = []
        for f in self.files:
            if not f.endswith(".py"):
                continue
            tree = ctx.tree(f)
            for n in A.ast.walk(tree):
                target = None
                if isinstance(n, A.ast.Call) and isinstance(
                        n.func, A.ast.Attribute):
                    target = n.func.value
                elif isinstance(n, (A.ast.Assign, A.ast.AugAssign)):
                    ts = n.targets if isinstance(n, A.ast.Assign) \
                        else [n.target]
                    for t in ts:
                        if isinstance(t, A.ast.Subscript):
                            t = t.value
                        if A.ast.unparse(t) in ("sys.path", "path"):
                            bad.append("%s:%d %s" % (f, n.lineno,
                                                     A.ast.unparse(n)))
                if target is not None and A.ast.unparse(target) in (
                        "sys.path",):
                    bad.append("%s:%d %s" % (f, n.lineno, A.ast.unparse(n)))
        if bad:
            ctx.ko("sys.path modifié", SYS_PATH_RULE, got="\n".join(bad))
        self.run_checks(ctx)

    def run_checks(self, ctx: Ctx) -> None:
        pass

    def tracked_check(self, ctx: Ctx, rel: str, what: str) -> None:
        """KO si `rel` (fichier ou dossier) est commité."""
        tracked = git_tracked(ctx.root)
        real = ctx.root / rel
        if not real.exists():
            return
        if tracked is None:
            ctx.warn("%s présent (dépôt git introuvable)" % what, NO_SUBMIT,
                     got=rel, manual="vérifiez avec « git ls-files %s » qu'il"
                                     " n'est pas commité." % rel)
            return
        prefix = rel.rstrip("/") + "/"
        if rel in tracked or any(t.startswith(prefix) for t in tracked):
            ctx.ko("%s commité dans le dépôt" % what, NO_SUBMIT, got=rel)
        else:
            ctx.ok("%s présent localement mais non commité" % what)


# ====================================================================
LAB_RULE = ("Your program must work both inside and outside a virtual "
            "environment, and produce a clearly different output in each "
            "case.")
LOAD_RULE = ("Your program must detect which reagents are available and, if "
             "one is missing, print a helpful message with the install "
             "command for both pip and Poetry. It must not crash.")


class Ex0(M05Exercise):
    ex_id, title, directory = "ex0", "The Sealed Laboratory", "ex0"
    files = ["construct.py", "loading.py", "requirements.txt",
             "pyproject.toml"]
    optional_files = ["poetry.lock"]
    imports = {"os", "sys", "site", "importlib", "pandas", "numpy"}
    authorized_line = "Authorized: os, sys, site, importlib, pandas, numpy"

    def run_checks(self, ctx: Ctx) -> None:
        for d in sorted(ctx.real_path("").iterdir()) + sorted(
                ctx.root.iterdir()):
            if d.is_dir() and (d / "pyvenv.cfg").exists():
                self.tracked_check(ctx, str(d.relative_to(ctx.root)),
                                   "Environnement virtuel")
        self.declarations(ctx)
        self.construct(ctx)
        self.loading(ctx)

    def declarations(self, ctx: Ctx) -> None:
        req = requirement_names(ctx.path("requirements.txt").read_text(
            errors="replace"))
        deps, err = pyproject_deps(ctx.path("pyproject.toml").read_text(
            errors="replace"))
        if err:
            ctx.ko("pyproject.toml invalide", "Declares a couple of external "
                   "reagents ... in both ex0/requirements.txt (for pip) and "
                   "ex0/pyproject.toml (for Poetry).", got=err)
            deps = None
        imported = set()
        for imp in A.imports(ctx.tree("loading.py")):
            if imp.root in ("pandas", "numpy"):
                imported.add(imp.root)
        src = ctx.src("loading.py").text
        for lib in ("pandas", "numpy"):
            if re.search(r"""["']%s["']""" % lib, src):
                imported.add(lib)
        rule = ("Declares a couple of external reagents (libraries such as "
                "pandas and numpy) in both ex0/requirements.txt (for pip) and"
                " ex0/pyproject.toml (for Poetry).")
        if len(req) < 2:
            ctx.ko("requirements.txt déclare moins de 2 bibliothèques", rule,
                   got=", ".join(sorted(req)) or "(vide)")
        if deps is not None and len(deps) < 2:
            ctx.ko("pyproject.toml déclare moins de 2 dépendances", rule,
                   got=", ".join(sorted(deps)) or "(aucune)",
                   detail="Attendu dans [tool.poetry.dependencies] ou "
                          "[project] dependencies.")
        if deps is not None and req and deps and req != deps:
            ctx.ko("requirements.txt et pyproject.toml ne déclarent pas les "
                   "mêmes bibliothèques", rule,
                   expected="requirements.txt : %s" % ", ".join(sorted(req)),
                   got="pyproject.toml : %s" % ", ".join(sorted(deps)))
        missing = {lib for lib in imported if lib not in req}
        if missing:
            ctx.ko("loading.py utilise des bibliothèques non déclarées", rule,
                   got=", ".join(sorted(missing)))
        if not imported:
            ctx.ko("loading.py n'importe aucune bibliothèque déclarée",
                   "Imports each declared reagent and reports its installed "
                   "version.")

    def construct(self, ctx: Ctx) -> None:
        tmp = ctx.sandbox.tmpdir()
        venv = make_venv(tmp)
        outside_py = base_python()
        if venv is None or outside_py is None:
            ctx.warn("Impossible de créer un venv de test", LAB_RULE,
                     manual="python3 ex0/construct.py puis dans un venv "
                            "activé : comparez les deux sorties.")
            return
        clear = {"VIRTUAL_ENV": None, "CONDA_PREFIX": None,
                 "CONDA_DEFAULT_ENV": None}
        out = ctx.run("construct.py", cwd="", python=outside_py, env=clear,
                      argv0="ex0/construct.py")
        inside_env: dict[str, str | None] = {
            "VIRTUAL_ENV": str(venv),
            "PATH": str(venv / "bin") + os.pathsep + os.environ.get(
                "PATH", ""), "CONDA_PREFIX": None}
        ins = ctx.run("construct.py", cwd="", python=str(venv / "bin" /
                                                         "python"),
                      env=inside_env, argv0="ex0/construct.py")
        for label, res in (("hors venv", out), ("dans un venv", ins)):
            if res.crashed or res.returncode:
                ctx.ko("construct.py plante %s" % label, LAB_RULE,
                       got=(res.stdout + "\n" + res.crash_text()).strip())
                return
        if out.stdout == ins.stdout:
            ctx.ko("Même sortie dans et hors d'un venv", LAB_RULE,
                   got=out.stdout)
            return
        low = out.stdout.lower()
        if "venv" not in low or "activate" not in low:
            ctx.ko("Pas d'instructions pour créer/activer un venv hors venv",
                   "Provides instructions for creating and activating a "
                   "virtual environment if none is detected",
                   expected="python3 -m venv lab_env\nsource "
                            "lab_env/bin/activate", got=out.stdout)
        if "lab_env" not in ins.stdout and str(venv) not in ins.stdout:
            ctx.warn("Le nom/chemin du venv n'est pas affiché dans le venv",
                     "Displays information about the current Python "
                     "environment", expected="Virtual Environment: lab_env",
                     got=ins.stdout)
        if "site-packages" not in out.stdout + ins.stdout:
            ctx.warn("Emplacement des paquets (site-packages) non affiché",
                     "Shows the difference between global and virtual "
                     "environment package locations", got=ins.stdout)
        ctx.compare("construct.py dans un venv", [
            "LABORATORY STATUS: The laboratory is sealed", "",
            re.compile(r"Current Python: .*"),
            "Virtual Environment: lab_env",
            re.compile(r"Environment Path: .*lab_env"), "",
            "SUCCESS: You are working in an isolated environment!",
            "Safe to install reagents without affecting",
            "the global system.", "", "Reagent installation path:",
            re.compile(r".*lab_env/lib(64)?/python3\.\d+/site-packages")],
            ins.lines(), "Expected output ... And inside the sealed "
            "laboratory:", strict=False)
        ctx.ok("construct.py : sorties différentes dans/hors venv")

    def loading(self, ctx: Ctx) -> None:
        tmp = ctx.sandbox.tmpdir()
        venv = make_venv(tmp, "empty_env")
        if venv is None:
            ctx.warn("Impossible de créer un venv de test", LOAD_RULE,
                     manual="python3 ex0/loading.py sans pandas/numpy, puis "
                            "après pip install -r ex0/requirements.txt.")
            return
        py = str(venv / "bin" / "python")
        env: dict[str, str | None] = {"VIRTUAL_ENV": str(venv)}
        res = ctx.run("loading.py", cwd="", python=py, env=env,
                      argv0="ex0/loading.py")
        if res.crashed or res.returncode:
            ctx.ko("loading.py plante sans les bibliothèques", LOAD_RULE,
                   got=(res.stdout + "\n" + res.crash_text()).strip())
        else:
            low = res.stdout.lower()
            missing = [w for w in ("pip install", "poetry") if w not in low]
            if missing:
                ctx.ko("Pas de commande d'installation pip et Poetry quand "
                       "une bibliothèque manque", LOAD_RULE,
                       expected="pip install ... / poetry add|install ...",
                       got=res.stdout, detail="Introuvable : "
                       + ", ".join(missing))
            else:
                ctx.ok("loading.py sans bibliothèques : instructions pip et "
                       "Poetry")
        # Bibliothèques « installées » (faux paquets locaux, sans réseau)
        tmp2 = ctx.sandbox.tmpdir()
        venv2 = make_venv(tmp2, "full_env")
        if venv2 is None:
            return
        req = requirement_names(ctx.path("requirements.txt").read_text(
            errors="replace"))
        versions = {"pandas": "2.1.0", "numpy": "1.25.0"}
        libs = {n: versions.get(n, "9.8.7") for n in req
                if re.fullmatch(r"[a-z0-9]+", n)} or versions
        install_fake(venv2, libs)
        res = ctx.run("loading.py", cwd="", python=str(venv2 / "bin" /
                                                       "python"),
                      env={"VIRTUAL_ENV": str(venv2)},
                      argv0="ex0/loading.py")
        manual = ("pip install -r ex0/requirements.txt puis python3 "
                  "ex0/loading.py : les versions installées doivent "
                  "s'afficher (et avec poetry install / poetry run).")
        if res.crashed or res.returncode:
            ctx.warn("loading.py n'a pas pu être testé avec les "
                     "bibliothèques installées", "Imports each declared "
                     "reagent and reports its installed version.",
                     got=(res.stdout + "\n" + res.crash_text()).strip(),
                     detail="Test fait avec de faux paquets locaux (pas de "
                            "réseau) : le plantage peut venir de là.",
                     manual=manual)
            return
        absent = [f"{n} {v}" for n, v in libs.items() if v not in res.stdout]
        if absent:
            ctx.ko("Versions installées non affichées", "Imports each "
                   "declared reagent and reports its installed version.",
                   expected="\n".join(f"{n} ({v})" for n, v in libs.items()),
                   got=res.stdout, detail="Testé avec des paquets factices "
                   "de versions connues.")
        else:
            ctx.ok("loading.py affiche les versions installées")
        low = res.stdout.lower()
        if "poetry" not in low or "pip" not in low:
            ctx.ko("La différence pip / Poetry n'est pas expliquée",
                   "Shows, in its output, the difference between pip and "
                   "Poetry dependency management.", got=res.stdout)
        ctx.warn("Installation réelle avec pip et Poetry non testée "
                 "(réseau nécessaire)", "Installing with pip: $> pip "
                 "install -r ex0/requirements.txt ... Installing with "
                 "Poetry: $> poetry install", manual=manual)


# ====================================================================
ORACLE_RULE = ("Create a program called ex1/oracle.py that: Loads its "
               "configuration from environment variables; Uses a .env file "
               "for development settings; Behaves differently in a "
               "development and in a production configuration; Handles "
               "missing configuration properly, without crashing")


class Ex1(M05Exercise):
    ex_id, title, directory = "ex1", "The Oracle", "ex1"
    files = ["oracle.py", "requirements.txt", ".env.example", ".gitignore"]
    optional_files = [".env"]
    imports = {"os", "sys", "dotenv"}
    authorized_line = "Authorized: os, sys, python-dotenv, file operations"

    def run_checks(self, ctx: Ctx) -> None:
        req = requirement_names(ctx.path("requirements.txt").read_text(
            errors="replace"))
        if "python-dotenv" not in req:
            ctx.ko("python-dotenv absent de requirements.txt",
                   "Use the python-dotenv library to load environment "
                   "variables from a .env file.", got=", ".join(sorted(req))
                   or "(vide)")
        gi = ctx.path(".gitignore").read_text(errors="replace")
        if not gitignore_ignores(gi, ".env"):
            ctx.ko(".env n'est pas ignoré par ex1/.gitignore", "Never commit "
                   "real secrets to version control! Your .env file must be "
                   "listed in ex1/.gitignore", got=gi)
        else:
            ctx.ok(".env listé dans .gitignore")
        if gitignore_ignores(gi, ".env.example"):
            ctx.ko(".env.example est ignoré par .gitignore", "Files to "
                   "Submit: oracle.py, requirements.txt, .env.example, "
                   ".gitignore", got=gi)
        example = ctx.path(".env.example").read_text(errors="replace")
        missing = [v for v in CONFIG_VARS
                   if not re.search(r"^\s*(export\s+)?%s\s*=" % v, example,
                                    re.M)]
        if missing:
            ctx.warn("Variables absentes de .env.example", "Your program "
                     "should handle the following configuration variables: "
                     "MATRIX_MODE, DATABASE_URL, API_KEY, LOG_LEVEL, "
                     "ZION_ENDPOINT", got=", ".join(missing))
        self.tracked_check(ctx, "ex1/.env", "Fichier .env")
        tree = ctx.tree("oracle.py")
        if not any(i.root == "dotenv" for i in A.imports(tree)):
            ctx.ko("oracle.py n'utilise pas python-dotenv", "Use the "
                   "python-dotenv library to load environment variables from"
                   " a .env file. The goal is to learn how .env files are "
                   "used for configuration, not to write your own parser.")
        src = ctx.src("oracle.py").text
        for v in CONFIG_VARS:
            if v not in src:
                ctx.ko("Variable %s non gérée par oracle.py" % v,
                       "Your program should handle the following "
                       "configuration variables: " + ", ".join(CONFIG_VARS))
        self.behaviour(ctx)

    def behaviour(self, ctx: Ctx) -> None:
        try:
            import dotenv  # noqa: F401
        except ImportError:
            ctx.warn("python-dotenv absent de l'environnement de pyvision",
                     ORACLE_RULE, manual="relancez ./install.sh, ou testez "
                                         "python3 ex1/oracle.py à la main.")
            return
        clean: dict[str, str | None] = {v: None for v in CONFIG_VARS}

        def env_file(values: dict[str, str]) -> Any:
            def setup(workdir: Path) -> None:
                p = workdir / "ex1" / ".env"
                if p.exists():
                    p.unlink()
                if values:
                    p.write_text("".join("%s=%s\n" % kv
                                         for kv in values.items()))
            return setup

        dev = {"MATRIX_MODE": "development",
               "DATABASE_URL": "sqlite:///pyvision_dev.db",
               "API_KEY": "pyvision-dev-key", "LOG_LEVEL": "DEBUG",
               "ZION_ENDPOINT": "http://localhost:4242"}
        prod = dict(dev, MATRIX_MODE="production", LOG_LEVEL="ERROR",
                    DATABASE_URL="postgresql://prod.example/db",
                    ZION_ENDPOINT="https://zion.example")

        def run(values: dict[str, str], env: dict[str, str | None]
                ) -> Any:
            e = dict(clean)
            e.update(env)
            return ctx.run("oracle.py", cwd="", env=e,
                           setup=env_file(values), argv0="ex1/oracle.py")

        r0 = run({}, {})
        r_dev = run(dev, {})
        r_prod = run(prod, {})
        r_over = run(dev, {"MATRIX_MODE": "production",
                           "API_KEY": "secret123"})
        for label, res in (("sans configuration", r0),
                           ("avec ex1/.env", r_dev),
                           ("en production", r_prod),
                           ("avec variables d'environnement", r_over)):
            if res.crashed or res.returncode:
                ctx.ko("oracle.py plante %s" % label, ORACLE_RULE,
                       got=(res.stdout + "\n" + res.crash_text()).strip())
                return
        low = r0.stdout.lower()
        if not any(w in low for w in ("missing", "default", "warn", "not "
                                      "set", "manquant", "défaut")):
            ctx.warn("Aucun avertissement sans configuration", "Testing "
                     "without any configuration: # Should show default "
                     "values and warn about the missing configuration",
                     got=r0.stdout)
        if r_dev.stdout == r0.stdout:
            ctx.ko("Le fichier ex1/.env n'est pas chargé", "Using a .env "
                   "file: $> cp ex1/.env.example ex1/.env ... $> python3 "
                   "ex1/oracle.py # Should load the configuration from the "
                   ".env file", got=r_dev.stdout,
                   detail="Lancé depuis la racine du dépôt (python3 "
                          "ex1/oracle.py) : la sortie est identique avec et "
                          "sans .env.")
        if r_prod.stdout == r_dev.stdout:
            ctx.ko("Même comportement en développement et en production",
                   "Behaves differently in a development and in a "
                   "production configuration", got=r_dev.stdout)
        if r_over.stdout == r_dev.stdout:
            ctx.ko("Les variables d'environnement ne priment pas sur .env",
                   "Overriding through the environment: $> "
                   "MATRIX_MODE=production API_KEY=secret123 python3 "
                   "ex1/oracle.py # Should prefer the environment variables "
                   "over the .env file", got=r_over.stdout)
        if "pyvision-dev-key" in r_dev.stdout or "secret123" in \
                r_over.stdout:
            ctx.warn("La clé API est affichée en clair", "Never commit real "
                     "secrets to version control!", got=r_dev.stdout)
        if not ctx.has_ko():
            ctx.ok("oracle.py : .env chargé, dev/prod différents, "
                   "environnement prioritaire")


# ====================================================================
class Ex2(M05Exercise):
    ex_id, title, directory = "ex2", "The Alembic", ""
    files = ["elements.py", "alchemy/__init__.py", "alchemy/elements.py",
             "ft_alembic_0.py", "ft_alembic_1.py"]
    imports: set[str] | None = set()
    local_imports = True
    authorized_line = OWN_IMPORTS
    mypy_expected = r'has no attribute "create_earth"'
    mypy_note = "A mypy error is expected here, on purpose."
    INIT_RULE = ("alchemy/__init__.py will contain: Whatever is needed to "
                 "expose create_air through the alchemy package interface, "
                 "and nothing that exposes create_earth.")

    def run_checks(self, ctx: Ctx) -> None:
        ctx.expect_calls("elements.py", [
            {"call": "create_fire", "returns": "Fire element created",
             "rule": "A function create_fire() that just returns the string "
                     "“Fire element created”."},
            {"call": "create_water", "returns": "Water element created",
             "rule": "A function create_water() that just returns the "
                     "string “Water element created”."}])
        code = """
        import importlib
        out = {}
        try:
            el = importlib.import_module("alchemy.elements")
            for f in ("create_earth", "create_air"):
                fn = getattr(el, f, None)
                out[f] = capture(fn).value if callable(fn) else None
        except Exception as e:
            out["error"] = repr(e)
        report("elements", out)
        import sys
        for k in list(sys.modules):
            if k.startswith("alchemy"):
                del sys.modules[k]
        try:
            al = importlib.import_module("alchemy")
            report("pkg", {"air": capture(al.create_air).value
                           if hasattr(al, "create_air") else None,
                           "earth": hasattr(al, "create_earth")})
        except Exception as e:
            report("pkg", {"error": repr(e)})
        """
        p = ctx.probe(code).probe
        el = p.get("elements", {})
        if el.get("error"):
            ctx.ko("import alchemy.elements impossible", got=el["error"])
        else:
            for f, want in (("create_earth", "Earth element created"),
                            ("create_air", "Air element created")):
                if el.get(f) != want:
                    ctx.ko("alchemy/elements.py : %s() incorrecte" % f,
                           "alchemy/elements.py will contain: A function "
                           "%s() that just returns the string “%s”."
                           % (f, want), expected=repr(want),
                           got=repr(el.get(f)))
        pkg = p.get("pkg", {})
        if pkg.get("error"):
            ctx.ko("import alchemy impossible", self.INIT_RULE,
                   got=pkg["error"])
        else:
            if pkg.get("air") != "Air element created":
                ctx.ko("alchemy.create_air() non exposé par __init__.py",
                       self.INIT_RULE, expected="'Air element created'",
                       got=repr(pkg.get("air")))
            if pkg.get("earth"):
                ctx.ko("alchemy.create_earth est exposé", self.INIT_RULE,
                       detail="import alchemy ne doit pas donner accès à "
                              "create_earth.")
        t0 = ctx.tree("ft_alembic_0.py")
        if not any(i.kind == "import" and i.module == "elements"
                   for i in A.imports(t0)):
            ctx.ko("ft_alembic_0.py n'utilise pas « import elements »",
                   "ft_alembic_0.py will use the import ... structure to "
                   "access elements.py at the root, and then create fire.",
                   got="\n".join(A.ast.unparse(n) for n in A.ast.walk(t0)
                                 if isinstance(n, (A.ast.Import,
                                                   A.ast.ImportFrom))))
        t1 = ctx.tree("ft_alembic_1.py")
        if not any(i.kind == "import" and i.module == "alchemy"
                   for i in A.imports(t1)):
            ctx.ko("ft_alembic_1.py n'utilise pas « import alchemy »",
                   "ft_alembic_1.py will use import alchemy to go through "
                   "the package interface, and then create air.")
        check_script(
            ctx, "ft_alembic_0.py", lines("""
            === Alembic 0 ===
            Using: 'import ...' structure to access elements.py
            Testing create_fire: Fire element created"""),
            "Example: $> python3 ft_alembic_0.py", cwd="")
        res = ctx.run("ft_alembic_1.py", cwd="")
        text = res.stdout + res.stderr
        if res.timeout:
            ctx.ko("ft_alembic_1.py : délai dépassé")
        elif "create_earth" not in text or (
                "AttributeError" not in text and "has no attribute" not in
                text):
            ctx.ko("ft_alembic_1.py ne montre pas l'échec de create_earth",
                   "It will then try to call create_earth() through that "
                   "same interface: this must fail, even though "
                   "alchemy/elements.py defines that very function.",
                   expected="AttributeError: module 'alchemy' has no "
                            "attribute 'create_earth'", got=text)
        else:
            ctx.ok("ft_alembic_1.py : create_earth inaccessible")
        if "Air element created" not in res.stdout:
            ctx.ko("ft_alembic_1.py ne crée pas l'air", "ft_alembic_1.py "
                   "will use import alchemy to go through the package "
                   "interface, and then create air.", got=res.stdout)


# ====================================================================
HEAL = ("Healing potion brewed with 'Earth element created' and 'Air "
        "element created'")
STRENGTH = ("Strength potion brewed with 'Fire element created' and 'Water "
            "element created'")
GOLD = ("Recipe transmuting Lead to Gold: brew 'Air element created' and '"
        + STRENGTH + "' mixed with 'Fire element created'")


class Ex3(M05Exercise):
    ex_id, title, directory = "ex3", "Distillation and Transmutation", ""
    files = ["alchemy/potions.py", "alchemy/transmutation/__init__.py",
             "alchemy/transmutation/recipes.py", "ft_distillation_0.py",
             "ft_transmutation_0.py"]
    imports: set[str] | None = set()
    local_imports = True
    authorized_line = OWN_IMPORTS

    def run_checks(self, ctx: Ctx) -> None:
        pot = ctx.tree("alchemy/potions.py")
        used = {A.call_name(c) for c in A.calls(pot)}
        need = {"create_fire", "create_water", "create_earth", "create_air"}
        if not need <= used:
            ctx.ko("potions.py n'appelle pas les quatre create_*()",
                   "Whatever else is needed to reach the four fundamental "
                   "elements. Note that two of them live outside the "
                   "package.", got="manquant : " + ", ".join(
                       sorted(need - used)),
                   detail="Les chaînes doivent venir des fonctions, pas "
                          "être recopiées.")
        ctx.expect_calls("alchemy/potions.py", [
            {"call": "healing_potion", "returns": HEAL,
             "rule": "A function healing_potion() that returns the string "
                     "“Healing potion brewed with ’[created earth element]’ "
                     "and ’[created air element]”’."},
            {"call": "strength_potion", "returns": STRENGTH,
             "rule": "A function strength_potion() that returns the string "
                     "“Strength potion brewed with ’[created fire element]’ "
                     "and ’[created water element]”’."}])
        code = """
        import importlib
        r = importlib.import_module("alchemy.transmutation.recipes")
        report("gold", capture(r.lead_to_gold).as_dict()
               if hasattr(r, "lead_to_gold") else None)
        """
        res = ctx.probe(code)
        gold = res.probe.get("gold")
        rule = ("A function lead_to_gold() that returns the string “Recipe "
                "transmuting Lead to Gold: brew ’[created air]’ and "
                "’[created strength potion]’ mixed with ’[created fire]”’.")
        if gold is None:
            ctx.ko("lead_to_gold() introuvable dans "
                   "alchemy/transmutation/recipes.py", rule,
                   got=res.meta.get("probe_error"))
        elif gold["exc"] or gold["value"] != GOLD:
            ctx.ko("lead_to_gold() incorrecte", rule, expected=GOLD,
                   got=gold["exc"] or repr(gold["value"]))
        rec = A.imports(ctx.tree("alchemy/transmutation/recipes.py"))
        if not any(i.level == 0 for i in rec):
            ctx.ko("recipes.py : aucun import absolu", "At least one "
                   "absolute import and one relative import.")
        if not any(i.level > 0 for i in rec):
            ctx.ko("recipes.py : aucun import relatif", "At least one "
                   "absolute import and one relative import.")
        td = ctx.tree("ft_distillation_0.py")
        if not any(i.kind == "from" and (i.module == "alchemy.potions" or (
                i.module == "alchemy" and "potions" in i.names))
                for i in A.imports(td)):
            ctx.ko("ft_distillation_0.py n'utilise pas « from "
                   "alchemy.potions import ... »", "ft_distillation_0.py "
                   "will use the from ... import ... structure to access "
                   "alchemy/potions.py directly")
        tt = ctx.tree("ft_transmutation_0.py")
        if not any(i.kind == "import" and i.module ==
                   "alchemy.transmutation.recipes" for i in A.imports(tt)):
            ctx.ko("ft_transmutation_0.py n'utilise pas « import "
                   "alchemy.transmutation.recipes »", "ft_transmutation_0.py"
                   " will use the import ... structure to access "
                   "alchemy/transmutation/recipes.py directly")
        check_script(ctx, "ft_distillation_0.py", [
            "=== Distillation 0 ===", "Direct access to alchemy/potions.py",
            "Testing strength_potion: " + STRENGTH,
            "Testing healing_potion: " + HEAL],
            "Example: $> python3 ft_distillation_0.py", cwd="")
        check_script(ctx, "ft_transmutation_0.py", [
            "=== Transmutation 0 ===",
            "Using file alchemy/transmutation/recipes.py directly",
            "Testing lead to gold: " + GOLD],
            "Example: $> python3 ft_transmutation_0.py", cwd="")


# ====================================================================
LIGHT_RULE = ("alchemy/grimoire/light_spellbook.py will contain: A function "
              "light_spell_allowed_ingredients() that returns the list of "
              "ingredients allowed for light magic: “earth”, “air”, “fire”, "
              "“water”. A function light_spell_record(spell_name: str, "
              "ingredients: str) that returns a string stating whether the "
              "spell was recorded or rejected.")
VALID_RULE = ("A function validate_ingredients(ingredients: str) that "
              "returns a string containing the ingredients and the “VALID” "
              "or “INVALID” keyword. The ingredients are valid if they "
              "include at least one of the ingredients allowed by the "
              "spellbook, case insensitive.")
DARK_RULE = ("This time, write the mutual dependency the naive way, at the "
             "top of both files, and leave it broken. This pair is a "
             "demonstration of the failure, so it must genuinely fail.")


class Ex4(M05Exercise):
    ex_id, title, directory = "ex4", "Avoid the Explosion", ""
    G = "alchemy/grimoire/"
    files = [G + "__init__.py", G + "light_spellbook.py",
             G + "light_validator.py", G + "dark_spellbook.py",
             G + "dark_validator.py", "ft_kaboom_0.py", "ft_kaboom_1.py"]
    imports: set[str] | None = set()
    local_imports = True
    authorized_line = OWN_IMPORTS

    def run_checks(self, ctx: Ctx) -> None:
        g = self.G
        for first in ("light_spellbook", "light_validator"):
            code = """
            import importlib
            try:
                importlib.import_module("alchemy.grimoire.%s")
                report("ok", True)
            except Exception as e:
                report("ok", False)
                report("err", "%%s: %%s" %% (type(e).__name__, e))
            """ % first
            p = ctx.probe(code).probe
            if not p.get("ok"):
                ctx.ko("Import de alchemy.grimoire.%s impossible" % first,
                       "There are several ways to keep that from exploding; "
                       "pick one", got=p.get("err"),
                       detail="Le grimoire « light » ne doit pas exploser, "
                              "quel que soit le fichier importé en premier.")
        code = """
        import importlib
        sb = importlib.import_module("alchemy.grimoire.light_spellbook")
        va = importlib.import_module("alchemy.grimoire.light_validator")
        out = {}
        out["allowed"] = capture(sb.light_spell_allowed_ingredients).value \\
            if hasattr(sb, "light_spell_allowed_ingredients") else "absent"
        for k, arg in (("v1", "Earth, wind and fire"), ("v2", "FIRE"),
                       ("v3", "bats and frogs"), ("v4", "")):
            out[k] = capture(va.validate_ingredients, arg).value \\
                if hasattr(va, "validate_ingredients") else "absent"
        if hasattr(sb, "light_spell_record"):
            out["r1"] = capture(sb.light_spell_record, "Fantasy",
                                "Earth, wind and fire").value
            out["r2"] = capture(sb.light_spell_record, "Doom",
                                "bats and frogs").value
        report("light", out)
        """
        p = ctx.probe(code).probe.get("light")
        if p:
            allowed = p.get("allowed")
            want = ["earth", "air", "fire", "water"]
            if allowed == "absent":
                ctx.ko("light_spell_allowed_ingredients() absente",
                       LIGHT_RULE)
            elif not isinstance(allowed, list) or sorted(
                    str(x).lower() for x in allowed) != sorted(want):
                ctx.ko("light_spell_allowed_ingredients() incorrecte",
                       LIGHT_RULE, expected=repr(want), got=repr(allowed))
            for k, ok, arg in (("v1", True, "Earth, wind and fire"),
                               ("v2", True, "FIRE"),
                               ("v3", False, "bats and frogs")):
                v = p.get(k)
                if v == "absent":
                    ctx.ko("validate_ingredients() absente de "
                           "light_validator.py", VALID_RULE)
                    break
                good = isinstance(v, str) and arg in v and (
                    ("VALID" in v and "INVALID" not in v) if ok
                    else "INVALID" in v)
                if not good:
                    ctx.ko("validate_ingredients(%r) incorrect" % arg,
                           VALID_RULE, expected="'%s - %s'" % (
                               arg, "VALID" if ok else "INVALID"),
                           got=repr(v))
            r1, r2 = p.get("r1"), p.get("r2")
            if r1 is None:
                ctx.ko("light_spell_record() absente", LIGHT_RULE)
            elif not isinstance(r1, str) or not isinstance(r2, str) or \
                    r1.replace("Fantasy", "X").replace(
                        "Earth, wind and fire", "Y").replace("VALID", "Z") \
                    == r2.replace("Doom", "X").replace(
                        "bats and frogs", "Y").replace("INVALID", "Z"):
                ctx.ko("light_spell_record() ne distingue pas sort "
                       "enregistré / rejeté", LIGHT_RULE,
                       got="valide : %r\ninvalide : %r" % (r1, r2))
            elif "Fantasy" not in r1:
                ctx.ko("light_spell_record() n'indique pas le nom du sort",
                       LIGHT_RULE, got=repr(r1))
        # Le grimoire sombre doit exploser
        code = """
        import importlib
        try:
            importlib.import_module("alchemy.grimoire.dark_spellbook")
            report("ok", True)
        except ImportError as e:
            report("ok", False)
            report("err", str(e))
        except Exception as e:
            report("ok", False)
            report("other", "%s: %s" % (type(e).__name__, e))
        """
        p = ctx.probe(code).probe
        if p.get("ok"):
            ctx.ko("Le grimoire sombre n'explose pas", DARK_RULE,
                   detail="import alchemy.grimoire.dark_spellbook "
                          "fonctionne : l'import circulaire doit échouer.")
        elif p.get("other"):
            ctx.ko("Le grimoire sombre échoue pour une autre raison qu'un "
                   "import circulaire", DARK_RULE, got=p["other"])
        elif "circular" not in str(p.get("err", "")):
            ctx.warn("Erreur d'import sans mention d'import circulaire",
                     DARK_RULE, got=p.get("err"))
        else:
            ctx.ok("dark_spellbook : ImportError (import circulaire)")
        sb = ctx.tree(g + "dark_spellbook.py")
        va = ctx.tree(g + "dark_validator.py")
        top_sb = [i for i in A.imports(sb) if i.toplevel and
                  "dark_validator" in i.module + ".".join(i.names)]
        top_va = [i for i in A.imports(va) if i.toplevel and
                  "dark_spellbook" in i.module + ".".join(i.names)]
        if not top_sb or not top_va:
            ctx.ko("Dépendance mutuelle non écrite en haut des deux "
                   "fichiers sombres", DARK_RULE)
        if "dark_spell_allowed_ingredients" not in A.functions(sb) or \
                "dark_spell_record" not in A.functions(sb):
            ctx.ko("Fonctions dark_ absentes de dark_spellbook.py",
                   "Now write dark_spellbook.py and dark_validator.py as the "
                   "dark counterparts, with dark_-prefixed function names",
                   got=", ".join(A.functions(sb)))
        consts = " ".join(t for t, _ in A.string_constants(sb)).lower()
        miss = [w for w in ("bats", "frogs", "arsenic", "eyeball")
                if w not in consts]
        if miss:
            ctx.ko("Ingrédients sombres manquants", "dark ingredients: "
                   "“bats”, “frogs”, “arsenic”, “eyeball”.",
                   got="manquant : " + ", ".join(miss))
        res = check_script(
            ctx, "ft_kaboom_0.py", lines("""
            === Kaboom 0 ===
            Using grimoire module directly
            Testing record light spell: Spell recorded: Fantasy (Earth, wind and fire - VALID)"""),  # noqa: E501
            "ft_kaboom_0.py will access the grimoire package and record a "
            "light spell, flawlessly.", strict=False, cwd="")
        if not res.crashed and "VALID" not in res.stdout:
            ctx.ko("ft_kaboom_0.py n'enregistre pas de sort", "ft_kaboom_0."
                   "py will access the grimoire package and record a light "
                   "spell, flawlessly.", got=res.stdout)
        res = ctx.run("ft_kaboom_1.py", cwd="")
        text = res.stdout + res.stderr
        if res.timeout:
            ctx.ko("ft_kaboom_1.py : délai dépassé")
        elif "ImportError" not in text and "circular" not in text:
            ctx.ko("ft_kaboom_1.py n'explose pas", "ft_kaboom_1.py will "
                   "reach dark_spellbook.py directly and try to record a "
                   "dark spell. This must fail and raise an exception, "
                   "indicating that your laboratory has just exploded.",
                   got=text)
        else:
            ctx.ok("ft_kaboom_1.py : ImportError circulaire")


class Module05bis(Module):
    id = "05bis"
    title = "The Codex"
    pdf = "python_module_05bis.pdf"
    signature = ["ex0/construct.py", "ex0/loading.py", "ex1/oracle.py",
                 "alchemy/__init__.py", "alchemy/elements.py",
                 "ft_alembic_0.py", "ft_distillation_0.py",
                 "ft_kaboom_0.py", "alchemy/grimoire/dark_spellbook.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4()]
    flake8_rule = "Your project must adhere to the flake8 coding standard."
    hints_rule = ("All code must include comprehensive type annotations. "
                  "Check this using mypy.")
    only_requested_rule = NO_SUBMIT


MODULE = Module05bis()
