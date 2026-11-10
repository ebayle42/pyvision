"""Exécution sécurisée du code élève dans un sous-processus isolé."""
from __future__ import annotations

import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HARNESS = Path(__file__).with_name("harness.py")

# Dossiers jamais recopiés dans le bac à sable.
IGNORED_DIRS = {".git", "__pycache__", ".mypy_cache", ".pytest_cache",
                ".ruff_cache", "node_modules", ".idea", ".vscode",
                ".tox", ".eggs"}

MAX_OUTPUT = 20 * 1024 * 1024      # 20 Mo de sortie maximum
MAX_MEMORY = 2 * 1024 * 1024 * 1024  # 2 Go de mémoire virtuelle


def is_venv_dir(path: Path) -> bool:
    return (path / "pyvenv.cfg").is_file()


def _ignore(directory: str, names: list[str]) -> list[str]:
    out = []
    for n in names:
        full = Path(directory) / n
        if n in IGNORED_DIRS or (full.is_dir() and is_venv_dir(full)):
            out.append(n)
    return out


@dataclass
class RunResult:
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    timeout: bool = False
    killed: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)
    command: str = ""

    @property
    def prompts(self) -> list[str]:
        return list(self.meta.get("prompts", []))

    @property
    def input_calls(self) -> int:
        return int(self.meta.get("input_calls", 0))

    @property
    def exception(self) -> dict[str, Any] | None:
        exc = self.meta.get("exception")
        return exc if isinstance(exc, dict) else None

    @property
    def probe(self) -> dict[str, Any]:
        return dict(self.meta.get("probe", {}))

    @property
    def crashed(self) -> bool:
        return self.timeout or self.killed is not None or (
            self.exception is not None)

    def lines(self) -> list[str]:
        return self.stdout.splitlines()

    def crash_text(self) -> str:
        if self.timeout:
            return "Délai dépassé : le programme ne s'est pas terminé " \
                   "(boucle infinie ou attente d'une saisie ?)"
        if self.killed:
            return self.killed
        exc = self.exception
        if exc:
            tb = exc.get("tb") or ""
            tail = "\n".join(_clean_tb(tb).splitlines()[-8:])
            return tail or "%s: %s" % (exc.get("type"), exc.get("msg"))
        return ""


def _clean_tb(tb: str) -> str:
    """Retire les lignes de traceback qui concernent le harness."""
    out: list[str] = []
    skip = False
    for line in tb.splitlines():
        if line.startswith('  File "'):
            skip = ("harness.py" in line or "<frozen runpy>" in line
                    or "runpy.py" in line)
        if not skip:
            out.append(line)
    return "\n".join(out)


class Sandbox:
    """Copie de travail du rendu élève : rien n'est jamais exécuté dans le
    dossier de l'élève, qui reste intact."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.base = Path(tempfile.mkdtemp(prefix="pyvision-"))
        self.work = self.base / "work"
        shutil.copytree(root, self.work, ignore=_ignore, symlinks=True)
        # Cache mypy persistant (hors du dossier de l'élève) : sans lui,
        # chaque lancement de mypy reprend typeshed de zéro (lent).
        self.mypy_cache = Path(os.environ.get(
            "XDG_CACHE_HOME", Path.home() / ".cache")) / "pyvision" / "mypy"
        self.mypy_cache.mkdir(parents=True, exist_ok=True)
        self._counter = 0

    def fresh_copy(self) -> Path:
        """Nouvelle copie propre (pour les exercices qui créent des
        fichiers)."""
        self._counter += 1
        dest = self.base / ("run%d" % self._counter)
        shutil.copytree(self.work, dest, symlinks=True)
        return dest

    def tmpdir(self) -> Path:
        self._counter += 1
        dest = self.base / ("tmp%d" % self._counter)
        dest.mkdir()
        return dest

    def cleanup(self) -> None:
        # Rendre les droits (fichiers de test en chmod 000) avant suppression.
        for dirpath, dirnames, filenames in os.walk(self.base):
            for n in dirnames + filenames:
                try:
                    os.chmod(os.path.join(dirpath, n), 0o700,
                             follow_symlinks=False)
                except (OSError, NotImplementedError):
                    pass
        shutil.rmtree(self.base, ignore_errors=True)


def _limits() -> None:
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT, MAX_OUTPUT))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))
    except (ValueError, OSError):
        pass
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ValueError, OSError):
        pass


def run_harness(cfg: dict[str, Any], cwd: Path, workdir: Path,
                timeout: float = 5.0, python: str | None = None,
                env_extra: dict[str, str] | None = None,
                isolated: bool = True,
                stdin_data: str | None = None) -> RunResult:
    """Lance le harness dans un sous-processus avec timeout et limites."""
    python = python or sys.executable
    workdir.mkdir(parents=True, exist_ok=True)
    fd, cfg_path = tempfile.mkstemp(suffix=".json", dir=workdir)
    os.close(fd)
    meta_path = cfg_path[:-5] + ".meta.json"
    out_path = cfg_path[:-5] + ".out"
    err_path = cfg_path[:-5] + ".err"
    in_path = cfg_path[:-5] + ".in"
    cfg = dict(cfg, meta_path=meta_path)
    Path(cfg_path).write_text(json.dumps(cfg), encoding="utf-8")
    Path(in_path).write_text(stdin_data or "", encoding="utf-8")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("PYTHON", "VIRTUAL_ENV"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONHASHSEED"] = "0"
    env["NO_COLOR"] = "1"
    for k, v in (env_extra or {}).items():
        if v is None:
            env.pop(k, None)
        else:
            env[k] = v
    flags = ["-I", "-B"] if isolated else ["-B"]
    cmd = [python, *flags, str(HARNESS), cfg_path]
    res = RunResult(command=" ".join(cmd))
    with open(out_path, "wb") as out, open(err_path, "wb") as err, \
            open(in_path, "rb") as stdin:
        try:
            proc = subprocess.Popen(cmd, cwd=cwd, stdout=out, stderr=err,
                                    stdin=stdin, env=env,
                                    preexec_fn=_limits,
                                    start_new_session=True)
        except OSError as e:
            res.killed = "Impossible de lancer Python : %s" % e
            return res
        try:
            res.returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            res.timeout = True
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait()
    res.stdout = _read(out_path)
    res.stderr = _clean_tb(_read(err_path))
    if not res.timeout and res.returncode is not None \
            and res.returncode < 0:
        sig = -res.returncode
        names = {signal.SIGXFSZ: "sortie trop volumineuse (> 20 Mo)",
                 signal.SIGSEGV: "erreur de segmentation (récursion "
                                 "infinie ?)",
                 signal.SIGKILL: "processus tué (mémoire ?)"}
        res.killed = "Processus arrêté : %s" % names.get(
            sig, "signal %d" % sig)
    try:
        res.meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        res.meta = {}
    if res.meta.get("exception") and res.meta["exception"].get("tb"):
        res.meta["exception"]["tb"] = _clean_tb(res.meta["exception"]["tb"])
    for p in (cfg_path, meta_path, out_path, err_path, in_path):
        try:
            os.unlink(p)
        except OSError:
            pass
    return res


def _read(path: str) -> str:
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def run_tool(cmd: list[str], cwd: Path, timeout: float = 120.0
             ) -> tuple[int, str]:
    """Lance un outil (flake8, mypy...) et renvoie (code, sortie)."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTHONPATH", None)
    env.pop("MYPYPATH", None)
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return -1, "délai dépassé"
    except OSError as e:
        return -2, str(e)
    return proc.returncode, (proc.stdout + proc.stderr).strip()
