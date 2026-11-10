"""Harness exécuté dans un sous-processus isolé (python -I -B).

Il n'est jamais importé par le testeur lui-même : il est lancé avec un
fichier de configuration JSON et écrit ses résultats dans un fichier JSON
séparé, pour ne jamais se mélanger à la sortie de l'élève.

Modes :
  - script : exécute un fichier élève comme `python3 fichier.py args...`
  - probe  : exécute du code de test (écrit par pyvision) qui importe les
             fonctions / classes de l'élève et les teste directement.
"""
import builtins
import importlib.util
import io
import json
import os
import runpy
import signal
import sys
import traceback

META = {"prompts": [], "input_calls": 0, "input_exhausted": False,
        "exception": None, "exit_code": None, "probe": {},
        "probe_error": None, "finished": False}
_REAL_STDOUT = sys.stdout


class InputExhausted(BaseException):
    """Levée quand l'élève appelle input() plus souvent que prévu."""


class CallTimeout(BaseException):
    """Levée quand un appel testé dépasse son délai."""


class OutputOverflow(BaseException):
    """Levée quand un appel testé écrit beaucoup trop (boucle infinie)."""


class BoundedIO(io.StringIO):
    LIMIT = 2_000_000

    def write(self, s):
        if self.tell() > self.LIMIT:
            raise OutputOverflow()
        return super().write(s)


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        if isinstance(value, (list, tuple)):
            return [_jsonable(v) for v in value]
        if isinstance(value, dict):
            return {str(k): _jsonable(v) for k, v in value.items()}
        return repr(value)


class FakeInput:
    """Remplace input() : enregistre le prompt et rejoue les réponses.

    Le prompt et la réponse sont écrits sur la sortie, comme dans un
    terminal, pour pouvoir comparer avec les exemples du sujet.
    """

    def __init__(self, answers):
        self.answers = list(answers) if answers is not None else None

    def __call__(self, prompt=""):
        prompt = str(prompt)
        META["prompts"].append(prompt)
        META["input_calls"] += 1
        sys.stdout.write(prompt)
        if self.answers is None:
            line = sys.stdin.readline()
            if not line:
                META["input_exhausted"] = True
                raise InputExhausted()
            line = line.rstrip("\n")
            sys.stdout.write(line + "\n")
            return line
        if not self.answers:
            META["input_exhausted"] = True
            sys.stdout.write("\n")
            raise InputExhausted()
        answer = self.answers.pop(0)
        sys.stdout.write(answer + "\n")
        return answer


class EchoStdin(io.TextIOBase):
    """sys.stdin qui recopie chaque ligne lue sur la sortie (comme l'écho
    du terminal), pour que la transcription ressemble au sujet."""

    def __init__(self, data):
        self._buf = io.StringIO(data)
        META["stdin_reads"] = 0

    def readable(self):
        return True

    def _echo(self, text):
        META["stdin_reads"] += 1
        if text:
            sys.stdout.write(text if text.endswith("\n") else text + "\n")
        return text

    def readline(self, size=-1):
        return self._echo(self._buf.readline(size))

    def read(self, size=-1):
        return self._echo(self._buf.read(size))

    def __iter__(self):
        while True:
            line = self.readline()
            if not line:
                return
            yield line

    def fileno(self):
        raise io.UnsupportedOperation("fileno")


def _on_alarm(signum, frame):
    raise CallTimeout()


class Captured:
    """Résultat d'un appel capturé dans une sonde."""

    def __init__(self):
        self.value = None
        self.out = ""
        self.err = ""
        self.prompts = []
        self.exc = None
        self.exc_type = None
        self.exc_obj = None
        self.exhausted = False
        self.timeout = False
        self.input_calls = 0

    def lines(self):
        return self.out.splitlines()

    def as_dict(self):
        return {"out": self.out, "err": self.err, "prompts": self.prompts,
                "exc": self.exc, "exc_type": self.exc_type,
                "exhausted": self.exhausted, "timeout": self.timeout,
                "input_calls": self.input_calls,
                "value": _jsonable(self.value)}


def capture(fn, *args, inputs=None, timeout=3.0, **kwargs):
    """Appelle fn(*args, **kwargs) en capturant sortie, prompts, erreurs."""
    res = Captured()
    old_out, old_err, old_input = sys.stdout, sys.stderr, builtins.input
    before_prompts = len(META["prompts"])
    before_calls = META["input_calls"]
    sys.stdout, sys.stderr = BoundedIO(), BoundedIO()
    builtins.input = FakeInput(inputs if inputs is not None else [])
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        res.value = fn(*args, **kwargs)
    except InputExhausted:
        res.exhausted = True
        res.exc = "input() appelé plus de fois que prévu"
        res.exc_type = "InputExhausted"
    except OutputOverflow:
        res.timeout = True
        res.exc = "sortie infinie (plus de 2 Mo écrits)"
        res.exc_type = "Timeout"
    except CallTimeout:
        res.timeout = True
        res.exc = "délai dépassé (boucle infinie ?)"
        res.exc_type = "Timeout"
    except RecursionError as e:
        res.exc = "RecursionError: " + str(e)
        res.exc_type = "RecursionError"
        res.exc_obj = e
    except SystemExit as e:
        res.exc = "SystemExit(%r)" % (e.code,)
        res.exc_type = "SystemExit"
    except BaseException as e:  # noqa: B902 - on veut tout attraper
        res.exc = "%s: %s" % (type(e).__name__, e)
        res.exc_type = type(e).__name__
        res.exc_obj = e
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        res.out = sys.stdout.getvalue()
        res.err = sys.stderr.getvalue()
        sys.stdout, sys.stderr, builtins.input = old_out, old_err, old_input
    res.prompts = META["prompts"][before_prompts:]
    res.input_calls = META["input_calls"] - before_calls
    del META["prompts"][before_prompts:]
    META["input_calls"] = before_calls
    return res


_LOADED = {}


def load(path, name=None, fresh=False):
    """Importe un fichier élève comme module (sans exécuter __main__)."""
    path = os.path.abspath(path)
    if name is None:
        name = os.path.splitext(os.path.basename(path))[0]
    if not fresh and path in _LOADED:
        return _LOADED[path]
    folder = os.path.dirname(path)
    if os.path.exists(os.path.join(folder, "__init__.py")):
        # Fichier dans un package : import par nom pointé depuis la racine
        # du package, comme le ferait Python lancé depuis cette racine.
        parts = [os.path.splitext(os.path.basename(path))[0]]
        top = folder
        while os.path.exists(os.path.join(top, "__init__.py")):
            parts.insert(0, os.path.basename(top))
            top = os.path.dirname(top)
        if top not in sys.path:
            sys.path.insert(0, top)
        dotted = ".".join(parts)
        box = {}

        def imp():
            box["m"] = importlib.import_module(dotted)

        res = capture(imp, timeout=5.0)
        if res.exc is not None:
            raise ImportError("import de %s impossible : %s"
                              % (dotted, res.exc))
        module = box["m"]
        module.__pyvision_import_output__ = res.out
        _LOADED[path] = module
        return module
    if folder not in sys.path:
        sys.path.insert(0, folder)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    res = capture(spec.loader.exec_module, module, timeout=5.0)
    if res.exc is not None:
        raise ImportError("import de %s impossible : %s"
                          % (os.path.basename(path), res.exc))
    module.__pyvision_import_output__ = res.out
    _LOADED[path] = module
    return module


# Instances créées pendant run_main(record=True) : nom de classe ->
# liste de (instance, copie de vars() juste après __init__).
INSTANCES = {}
CLASSES = {}


def _snapshot(obj):
    try:
        return {k: v for k, v in vars(obj).items()}
    except TypeError:
        return {}


def _wrap_class(cls):
    orig = cls.__dict__.get("__init__")
    if orig is None:
        def orig(self, *a, **k):  # noqa: E306
            return super(cls, self).__init__(*a, **k)

    def __init__(self, *args, **kwargs):
        orig(self, *args, **kwargs)
        if type(self) is cls:
            INSTANCES.setdefault(cls.__name__, []).append(
                (self, _snapshot(self)))

    __init__.__wrapped_by_pyvision__ = True
    try:
        __init__.__name__ = "__init__"
        __init__.__qualname__ = getattr(orig, "__qualname__", "__init__")
        __init__.__doc__ = getattr(orig, "__doc__", None)
        __init__.__wrapped__ = orig
        cls.__init__ = __init__
    except (TypeError, AttributeError):
        pass
    CLASSES[cls.__name__] = cls
    return cls


def _recording_build_class(real):
    def build(func, name, *bases, **kw):
        cls = real(func, name, *bases, **kw)
        try:
            if isinstance(cls, type) and not issubclass(cls, BaseException):
                _wrap_class(cls)
        except Exception:
            pass
        return cls
    return build


def instances(name):
    """Instances (objets) de la classe `name` créées par le programme."""
    return [o for o, _ in INSTANCES.get(name, [])]


def initial_state(obj):
    for lst in INSTANCES.values():
        for o, snap in lst:
            if o is obj:
                return snap
    return {}


def run_main(path, argv=None, inputs=None, timeout=5.0, record=False):
    """Exécute un fichier élève comme __main__ et renvoie (Captured, globals).
    record=True : enregistre les instances créées (voir instances())."""
    path = os.path.abspath(path)
    folder = os.path.dirname(path)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    old_argv = sys.argv
    sys.argv = [os.path.basename(path)] + list(argv or [])
    box = {}

    def go():
        box["g"] = runpy.run_path(path, run_name="__main__")

    real_build = builtins.__build_class__
    if record:
        builtins.__build_class__ = _recording_build_class(real_build)
    try:
        res = capture(go, inputs=inputs, timeout=timeout)
    finally:
        sys.argv = old_argv
        builtins.__build_class__ = real_build
    return res, box.get("g", {})


def report(key, value):
    META["probe"][key] = _jsonable(value)


def _write_meta(path):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_jsonable(META), f)
    except OSError:
        pass


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        cfg = json.load(f)
    meta_path = cfg["meta_path"]
    for p in reversed(cfg.get("sys_path", [])):
        sys.path.insert(0, p)
    if cfg.get("stdin_echo") is not None:
        sys.stdin = EchoStdin(cfg["stdin_echo"])
    if cfg.get("patch_input", True):
        builtins.input = FakeInput(cfg.get("inputs"))
    sys.setrecursionlimit(3000)
    code = 0
    try:
        if cfg["mode"] == "script":
            script = cfg["script"]
            sys.argv = [cfg.get("argv0", os.path.basename(script))]
            sys.argv += cfg.get("argv", [])
            sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
            # runpy remplace sys.argv[0] par le chemin donné : on lui passe
            # le chemin tel que l'élève l'aurait tapé (relatif au cwd).
            target = sys.argv[0] if os.path.exists(sys.argv[0]) else script
            runpy.run_path(target, run_name="__main__")
        else:
            env = {"load": load, "capture": capture, "report": report,
                   "run_main": run_main, "META": META,
                   "instances": instances, "initial_state": initial_state,
                   "CLASSES": CLASSES, "INSTANCES": INSTANCES,
                   "InputExhausted": InputExhausted}
            try:
                exec(compile(cfg["probe"], "<pyvision-probe>", "exec"), env)
            except BaseException:  # noqa: B902
                META["probe_error"] = traceback.format_exc(limit=6)
    except InputExhausted:
        code = 1
        META["exception"] = {"type": "InputExhausted", "msg":
                             "input() appelé plus de fois que prévu",
                             "tb": ""}
    except SystemExit as e:
        if e.code is None or isinstance(e.code, int):
            code = e.code or 0
        else:
            sys.stderr.write(str(e.code) + "\n")
            code = 1
    except BaseException as e:  # noqa: B902
        code = 1
        tb = traceback.format_exc()
        sys.stderr.write(tb)
        META["exception"] = {"type": type(e).__name__, "msg": str(e),
                             "tb": tb}
    finally:
        for stream in (sys.stdout, sys.stderr, sys.__stdout__,
                       sys.__stderr__):
            try:
                stream.flush()
            except Exception:
                pass
        META["exit_code"] = code
        META["finished"] = True
        _write_meta(meta_path)
    os._exit(code)


if __name__ == "__main__":
    main()
