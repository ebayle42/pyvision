"""Module 04 : Data Archivist (Digital Preservation in the Cyber Archives)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines, rx

TYPES = {"str", "int", "float", "list", "dict", "set", "tuple"}
TYPES_LINE = ("The following standard types and collections are allowed, "
              "along with all their associated methods and constructors: "
              "str, int, float, list, dict, set, tuple.")
NO_WITH = ("Note for advanced learners: the use of the with statement will "
           "be introduced in exercise 3. You must not use it before then.")
OUTPUT_RULE = ("Each exercise provides terminal examples showing the "
               "suggested output format. While the core structure must be "
               "maintained, you may customize messages to reflect your "
               "understanding of the file operations, as long as the "
               "essential information is preserved.")
CRASH = "Your functions should handle exceptions gracefully to avoid crashes."
FAIL_RULE = ("You need to handle the various failure cases (nonexistent "
             "files, inaccessible files, etc.).")

FRAGMENT = ("[FRAGMENT 001] Digital preservation protocols established 2087\n"
            "[FRAGMENT 002] Knowledge must survive the entropy wars\n"
            "[FRAGMENT 003] Every byte saved is a victory against oblivion\n")
OTHER = ("Line alpha of the pyvision test\n"
         "Second line, with: punctuation!\n"
         "3rd line 42\n")
IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


def _locked(name: str):  # type: ignore[no-untyped-def]
    def setup(workdir: Path) -> None:
        p = workdir / name
        p.write_text("secret\n", encoding="utf-8")
        p.chmod(0)
    return setup


def _locked_dir(name: str):  # type: ignore[no-untyped-def]
    def setup(workdir: Path) -> None:
        p = workdir / name
        p.mkdir()
        p.chmod(0o555)
    return setup


class M04Exercise(Exercise):
    type_hints = "required"
    file = ""
    allow_with = False

    def check(self, ctx: Ctx) -> None:
        tree = ctx.tree(self.file)
        if not self.allow_with and A.has_with(tree):
            ctx.ko("Instruction with utilisée avant l'exercice 3", NO_WITH,
                   file=ctx.rel(self.file))
        self.run_checks(ctx, tree)

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        pass

    # --- tests communs aux exercices 0 à 2 -------------------------------
    def common_reading(self, ctx: Ctx, header: str, stdin_mode: bool = False,
                       ) -> None:
        kw: dict[str, Any] = {}
        if stdin_mode:
            kw = {"inputs": None, "stdin": "\n", "stdin_echo": True}
        else:
            kw = {"inputs": [""]}
        f = ctx.rel(self.file)
        # Sans argument
        res = ctx.run(self.file, argv=[], **kw)
        if self.crashed(ctx, res, "sans argument"):
            pass
        elif "usage" not in (res.stdout + res.stderr).lower():
            ctx.ko("Pas de message d'usage sans argument", "$> python3 "
                   "%s\nUsage: %s <file>" % (self.file, self.file),
                   got=res.stdout + res.stderr, file=f)
        # Fichier inexistant
        res = ctx.run(self.file, argv=["foo"], **kw)
        if not self.crashed(ctx, res, "fichier inexistant"):
            text = res.stdout + res.stderr
            if "No such file" not in text and "Errno 2" not in text:
                ctx.ko("Erreur de fichier inexistant non affichée", FAIL_RULE,
                       expected="Error opening file 'foo': [Errno 2] No such "
                                "file or directory: 'foo'", got=text, file=f)
        # Fichier inaccessible
        if not IS_ROOT:
            res = ctx.run(self.file, argv=["locked.txt"],
                          setup=_locked("locked.txt"), **kw)
            if not self.crashed(ctx, res, "fichier inaccessible"):
                text = res.stdout + res.stderr
                if "Permission denied" not in text and "Errno 13" not in text:
                    ctx.ko("Erreur de permission non affichée", FAIL_RULE,
                           expected="Error opening file 'locked.txt': [Errno "
                                    "13] Permission denied: 'locked.txt'",
                           got=text, file=f)
        # Dossier à la place d'un fichier
        res = ctx.run(self.file, argv=["."], **kw)
        self.crashed(ctx, res, "dossier passé en argument")
        # Contenu affiché
        for name, content in (("ancient_fragment.txt", FRAGMENT),
                              ("pyvision_other.txt", OTHER)):
            res = ctx.run(self.file, argv=[name], files={name: content},
                          **kw)
            if self.crashed(ctx, res, name):
                continue
            out = res.lines()
            want = content.splitlines()
            idx = [out.index(w) if w in out else -1 for w in want]
            if -1 in idx or idx != sorted(idx):
                ctx.ko("Contenu du fichier non affiché tel quel (%s)" % name,
                       "read the file's contents and display them as the cat"
                       " command would.", expected="\n".join(want),
                       got=res.stdout, file=f)

    def crashed(self, ctx: Ctx, res: Any, label: str) -> bool:
        if res.timeout or res.killed or res.exception:
            ctx.ko("Plantage : %s" % label, CRASH, got=(
                res.stdout[-600:] + "\n" + res.crash_text()).strip(),
                file=ctx.rel(self.file), kind="crash")
            return True
        return False

    def check_saved(self, ctx: Ctx, res: Any, name: str, source: str,
                    rule: str) -> None:
        want = "".join(line + "#\n" for line in source.splitlines())
        target = Path(res.meta.get("workdir", "")) / name
        if not target.exists():
            ctx.ko("Fichier %s non créé" % name, rule,
                   expected=want, got=res.stdout, file=ctx.rel(self.file))
            return
        got = target.read_text(encoding="utf-8", errors="replace")
        if got.rstrip("\n") != want.rstrip("\n"):
            ctx.ko("Contenu sauvegardé incorrect", rule, expected=want,
                   got=got, file=ctx.rel(self.file),
                   detail="Chaque ligne doit se terminer par '#'.")
        else:
            ctx.ok("fichier sauvegardé avec '#' en fin de ligne")


class Ex0(M04Exercise):
    ex_id, title, directory = "ex0", "Ancient Text Recovery", "ex0"
    files = ["ft_ancient_text.py"]
    file = files[0]
    authorized = {"len", "open", "print"} | TYPES
    authorized_line = ("Authorized: import sys, sys.argv, len(), open(), "
                       "import typing, typing.IO, io.read(), io.close(), "
                       "print()\n" + TYPES_LINE)
    imports = {"sys", "typing"}
    EXAMPLE = """
        === Cyber Archives Recovery ===
        Accessing file 'ancient_fragment.txt'
        ---

        [FRAGMENT 001] Digital preservation protocols established 2087
        [FRAGMENT 002] Knowledge must survive the entropy wars
        [FRAGMENT 003] Every byte saved is a victory against oblivion

        ---
        File 'ancient_fragment.txt' closed."""

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        if not [c for c in A.calls(tree) if A.call_name(c) == "close"]:
            ctx.warn("Le fichier n'est jamais fermé (close())",
                     "File 'ancient_fragment.txt' closed.",
                     file=ctx.rel(self.file))
        check_script(ctx, self.file, lines(self.EXAMPLE), OUTPUT_RULE,
                     strict=False, argv=["ancient_fragment.txt"],
                     files={"ancient_fragment.txt": FRAGMENT},
                     crash_rule=CRASH)
        self.common_reading(ctx, "=== Cyber Archives Recovery ===")


SAVE_RULE = ("Ask the user for the name of the file to save to, or leave it "
             "empty to avoid saving anything. Save the new content if a file "
             "name is provided and display a new ending message. Create the "
             "file or replace it if it already exists.")


class Ex1(M04Exercise):
    ex_id, title, directory = "ex1", "Archive Creation", "ex1"
    files = ["ft_archive_creation.py"]
    file = files[0]
    authorized = {"len", "open", "print", "input"} | TYPES
    authorized_line = ("Authorized: import sys, sys.argv, len(), open(), "
                       "import typing, typing.IO, io.read(), io.write(), "
                       "io.close(), print(), input()\n" + TYPES_LINE)
    imports = {"sys", "typing"}
    PROMPT = "Enter new file name (or empty): "
    EXAMPLE = """
        === Cyber Archives Recovery & Preservation ===
        Accessing file 'ancient_fragment.txt'
        ---

        [FRAGMENT 001] Digital preservation protocols established 2087
        [FRAGMENT 002] Knowledge must survive the entropy wars
        [FRAGMENT 003] Every byte saved is a victory against oblivion

        ---
        File 'ancient_fragment.txt' closed.

        Transform data:
        ---

        [FRAGMENT 001] Digital preservation protocols established 2087#
        [FRAGMENT 002] Knowledge must survive the entropy wars#
        [FRAGMENT 003] Every byte saved is a victory against oblivion#

        ---
        Enter new file name (or empty): new_fragment.txt
        Saving data to 'new_fragment.txt'
        Data saved in file 'new_fragment.txt'."""

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        self.save_checks(ctx, stdin_mode=False)
        self.common_reading(ctx, "", stdin_mode=False)

    def save_checks(self, ctx: Ctx, stdin_mode: bool) -> None:
        f = ctx.rel(self.file)

        def kw(answer: str) -> dict[str, Any]:
            if stdin_mode:
                return {"inputs": None, "stdin": answer + "\n",
                        "stdin_echo": True}
            return {"inputs": [answer]}

        res = check_script(ctx, self.file, lines(self.EXAMPLE), OUTPUT_RULE,
                           strict=False, argv=["ancient_fragment.txt"],
                           files={"ancient_fragment.txt": FRAGMENT},
                           crash_rule=CRASH, **kw("new_fragment.txt"))
        if not res.crashed:
            if not stdin_mode:
                if not res.prompts:
                    ctx.ko("input() n'est jamais appelé", SAVE_RULE, file=f)
                elif res.prompts[0] != self.PROMPT:
                    ctx.warn("Prompt différent de l'exemple", OUTPUT_RULE,
                             expected=repr(self.PROMPT),
                             got=repr(res.prompts[0]), file=f)
            elif stdin_mode and res.meta.get("stdin_reads", 0) == 0:
                ctx.ko("La saisie n'est pas lue sur sys.stdin", "Get user "
                       "input without using the input() built-in function.",
                       file=f)
            for want in ("[FRAGMENT 001] Digital preservation protocols "
                         "established 2087#",):
                if want not in res.lines():
                    ctx.ko("Données transformées non affichées",
                           "Add a special archive character (the # "
                           "character) at the end of each line; Display the "
                           "new content", expected=want, got=res.stdout,
                           file=f)
            self.check_saved(ctx, res, "new_fragment.txt", FRAGMENT,
                             SAVE_RULE)
        # Remplacement d'un fichier existant + autre contenu
        res = ctx.run(self.file, argv=["pyvision_other.txt"],
                      files={"pyvision_other.txt": OTHER,
                             "out.txt": "OLD CONTENT TO REPLACE\n" * 5},
                      **kw("out.txt"))
        if not self.crashed(ctx, res, "sauvegarde dans un fichier existant"):
            self.check_saved(ctx, res, "out.txt", OTHER, SAVE_RULE)
        # Réponse vide : rien n'est sauvegardé
        res = ctx.run(self.file, argv=["ancient_fragment.txt"],
                      files={"ancient_fragment.txt": FRAGMENT}, **kw(""))
        if not self.crashed(ctx, res, "réponse vide"):
            work = Path(res.meta.get("workdir", ""))
            new = sorted(p.name for p in work.iterdir() if p.name not in (
                self.file, "ancient_fragment.txt"))
            if new:
                ctx.ko("Un fichier est créé alors que la réponse est vide",
                       SAVE_RULE, got=", ".join(new), file=f)
        # Écriture impossible
        if not IS_ROOT:
            res = ctx.run(self.file, argv=["ancient_fragment.txt"],
                          files={"ancient_fragment.txt": FRAGMENT},
                          setup=_locked_dir("locked"),
                          **kw("locked/out.txt"))
            if not self.crashed(ctx, res, "écriture dans un dossier "
                                          "protégé"):
                text = res.stdout + res.stderr
                if "Permission denied" not in text and "Errno 13" not in text:
                    ctx.ko("Erreur d'écriture non affichée", CRASH,
                           expected="[Errno 13] Permission denied: "
                                    "'locked/out.txt'", got=text, file=f)


class Ex2(Ex1):
    ex_id, title, directory = "ex2", "Stream Management", "ex2"
    files = ["ft_stream_management.py"]
    file = files[0]
    authorized = {"len", "open", "print"} | TYPES
    authorized_line = ("Authorized: import sys, sys.argv, sys.stdin, "
                       "sys.stdout, sys.stderr, len(), open(), import typing,"
                       " typing.IO, io.read(), io.readline(), io.write(), "
                       "io.flush(), io.close(), print()\n" + TYPES_LINE)
    imports = {"sys", "typing"}
    STDERR_RULE = ("Print error messages resulting from exceptions to the "
                   "error output stream instead of to the standard output, "
                   "with a clear prefix (see example)")

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        f = ctx.rel(self.file)
        if A.calls_named(tree, "input"):
            ctx.ko("input() utilisé", "Get user input without using the "
                   "input() built-in function.", file=f)
        self.save_checks(ctx, stdin_mode=True)
        self.common_reading(ctx, "", stdin_mode=True)
        res = ctx.run(self.file, argv=["foo"], inputs=None, stdin="\n",
                      stdin_echo=True)
        if not self.crashed(ctx, res, "fichier inexistant"):
            if "No such file" in res.stdout or "Errno 2" in res.stdout:
                ctx.ko("Message d'erreur écrit sur la sortie standard",
                       self.STDERR_RULE, expected="(stderr) [STDERR] Error "
                       "opening file 'foo': [Errno 2] ...",
                       got="(stdout) " + res.stdout, file=f)
            elif "Errno 2" not in res.stderr and \
                    "No such file" not in res.stderr:
                ctx.ko("Aucune erreur sur la sortie d'erreur",
                       self.STDERR_RULE, got="stderr : " + repr(res.stderr),
                       file=f)
            elif "[STDERR]" not in res.stderr:
                ctx.warn("Préfixe d'erreur absent", self.STDERR_RULE,
                         expected="[STDERR] Error opening file 'foo': ...",
                         got=res.stderr, file=f)
            else:
                ctx.ok("erreurs sur stderr avec préfixe")


VAULT_RULE = ("Create a function secure_archive() that provides safe access "
              "to any file for reading or writing. It returns a tuple "
              "(True|False, str) that indicates whether the operation "
              "succeeded (the boolean) and provides the associated content "
              "(either the file’s contents or an error message). The "
              "function takes the following parameters: a mandatory file "
              "name, an optional int or str (your choice) that indicates the "
              "action to perform (read or write), and another optional "
              "string that contains the content to write to the file.")


class Ex3(M04Exercise):
    ex_id, title, directory = "ex3", "Vault Security", "ex3"
    files = ["ft_vault_security.py"]
    file = files[0]
    allow_with = True
    authorized = {"open", "print"} | TYPES
    authorized_line = "Authorized: open(), read(), write(), print()\n" + \
        TYPES_LINE
    imports = set()
    EXAMPLE = """
        === Cyber Archives Security ===

        Using 'secure_archive' to read from a nonexistent file:
        (False, "[Errno 2] No such file or directory: '/not/existing/file'")

        Using 'secure_archive' to read from an inaccessible file:
        (False, "[Errno 13] Permission denied: '/etc/master.passwd'")

        Using 'secure_archive' to read from a regular file:
        (True, '[FRAGMENT 001] Digital preservation protocols established 2087\\n[FRAGMENT 002] Knowledge must survive the entropy wars\\n[FRAGMENT 003] Every byte saved is a victory against oblivion\\n')

        Using 'secure_archive' to write previous content to a new file:
        (True, 'Content successfully written to file')"""  # noqa: E501

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        f = ctx.rel(self.file)
        fn = A.functions(tree).get("secure_archive")
        if fn is None:
            ctx.ko("Fonction secure_archive() absente", VAULT_RULE, file=f)
            return
        if not A.has_with(fn):
            ctx.ko("secure_archive() n'utilise pas with", "This exercise "
                   "requires the use of the with statement (context manager)"
                   " to ensure proper file handling.", file=f)
        args = fn.args
        n_args = len(args.args)
        n_def = len(args.defaults)
        if n_args < 3 or n_def < 2 or n_args - n_def != 1:
            ctx.ko("Paramètres de secure_archive() incorrects", VAULT_RULE,
                   expected="secure_archive(file, action=<défaut>, "
                            "content=<défaut>)",
                   got="def secure_archive(%s)" % A.ast.unparse(args),
                   file=f)
        # /etc/master.passwd n'existe que sous macOS : Errno 2 accepté.
        expected: list[Any] = lines(self.EXAMPLE)
        expected[6] = rx(r"""\(False, "\[Errno (13\] Permission denied|2\] """
                         r"""No such file or directory): '/etc/master\."""
                         r"""passwd'"\)""")
        check_script(ctx, self.file, expected, OUTPUT_RULE, strict=False,
                     files={"ancient_fragment.txt": FRAGMENT},
                     crash_rule=CRASH)
        code = """
        import os
        m = load(os.path.join(EX, %r))
        sa = m.secure_archive
        out = {}
        with open("vault_read.txt", "w") as fh:
            fh.write(%r)
        out["read"] = capture(sa, "vault_read.txt").as_dict()
        out["missing"] = capture(sa, "/not/existing/file").as_dict()
        out["dir"] = capture(sa, ".").as_dict()
        with open("locked.txt", "w") as fh:
            fh.write("x")
        os.chmod("locked.txt", 0)
        out["locked"] = capture(sa, "locked.txt").as_dict()
        found = None
        for action in ("w", "write", 1, "W", "Write", "WRITE", 2, True):
            name = "vault_w_%%s.txt" %% str(action)
            c = capture(sa, name, action, "pyvision content\\n")
            if os.path.exists(name):
                with open(name) as fh:
                    data = fh.read()
                if data == "pyvision content\\n":
                    found = {"action": repr(action), "res": c.as_dict()}
                    break
        out["write"] = found
        report("calls", out)
        """ % (self.file, OTHER)
        p = ctx.probe(code).probe.get("calls")
        if not p:
            return

        def shape(d: dict[str, Any]) -> bool:
            v = d.get("value")
            return isinstance(v, list) and len(v) == 2 and \
                isinstance(v[0], bool) and isinstance(v[1], str)

        cases = [("read", "lecture d'un fichier", True, OTHER),
                 ("missing", "fichier inexistant", False, "No such file"),
                 ("dir", "dossier", False, None)]
        if not IS_ROOT:
            cases.append(("locked", "fichier inaccessible", False,
                          "Permission denied"))
        for key, label, ok, text in cases:
            d = p[key]
            if d["exc"]:
                ctx.ko("secure_archive : %s lève une exception" % label,
                       VAULT_RULE, got=d["exc"], file=f)
            elif not shape(d):
                ctx.ko("secure_archive : %s ne renvoie pas (bool, str)"
                       % label, VAULT_RULE, got=repr(d["value"]), file=f)
            elif d["value"][0] is not ok:
                ctx.ko("secure_archive : %s renvoie %s" % (
                    label, d["value"][0]), VAULT_RULE, expected=str(ok),
                    got=repr(d["value"]), file=f)
            elif ok and d["value"][1] != text:
                ctx.ko("secure_archive : contenu lu incorrect", VAULT_RULE,
                       expected=repr(text), got=repr(d["value"][1]), file=f)
            elif not ok and text and text not in d["value"][1]:
                ctx.ko("secure_archive : message d'erreur incomplet (%s)"
                       % label, VAULT_RULE, expected="... %s ..." % text,
                       got=d["value"][1], file=f)
            else:
                ctx.ok("secure_archive : " + label)
        w = p.get("write")
        if w is None:
            ctx.warn("Écriture avec secure_archive() non détectée",
                     VAULT_RULE, detail="Aucune des valeurs d'action "
                     "essayées ('w', 'write', 1, 'W'...) n'a écrit le "
                     "fichier.", manual="appelez secure_archive('test.txt',"
                     " <votre action d'écriture>, 'abc') et vérifiez le "
                     "contenu de test.txt.", file=f)
        elif not shape(w["res"]) or w["res"]["value"][0] is not True:
            ctx.ko("secure_archive en écriture ne renvoie pas (True, str)",
                   VAULT_RULE, got=repr(w["res"]["value"]), file=f)
        else:
            ctx.ok("secure_archive : écriture (action %s)" % w["action"])


class Module04(Module):
    id = "04"
    title = "Data Archivist"
    pdf = "python_module_04.pdf"
    signature = ["ex0/ft_ancient_text.py", "ex1/ft_archive_creation.py",
                 "ex2/ft_stream_management.py", "ex3/ft_vault_security.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3()]
    flake8_rule = "Your code must comply with the flake8 linter standards."
    hints_rule = ("All functions and methods must include type hints. Check "
                  "this using mypy.")
    only_requested_rule = ("You need to submit only the files requested by "
                           "the project specification.")


MODULE = Module04()
