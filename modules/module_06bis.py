"""Module 06bis : Code Nexus (Abstract Architecture, from Data Streams to
Battle Strategies)."""
from __future__ import annotations

import json
import re
from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines

IMPORTS_RULE = ("Authorized imports: abc and typing . External libraries are "
                "forbidden.")
ABC_RULE = ("An abstract class DataProcessor that inherits from ABC and "
            "defines the common processing interface. Two abstract methods "
            "in DataProcessor: validate ... and ingest ... One standard "
            "method in DataProcessor: output, which will output ingested "
            "data.")
VALIDATE_RULE = ("The validate method will be defined as validate(self, "
                 "data: Any) -> bool in the DataProcessor class. The "
                 "overriding methods in the specialized classes will share "
                 "the same signature")
INGEST_RULE = ("The ingest method will be defined as ingest(self, data: Any)"
               " -> None in the DataProcessor class. The overriding methods "
               "in the specialized classes will have their own specific "
               "signatures to match the types they expect. In case the user "
               "does not validate the data before calling ingest, and "
               "provides invalid data, an exception must be raised.")
OUTPUT_RULE = ("The output method will be defined as output(self) -> "
               "tuple[int, str] in the DataProcessor class. The output method"
               " will extract the oldest piece of data stored internally in "
               "the data processor, along with the associated processing "
               "rank within the data processor. The piece of data is then "
               "removed from the data processor.")
SPECIALIZED = ["NumericProcessor", "TextProcessor", "LogProcessor"]


def _norm(s: str) -> str:
    s = s.replace(" ", "").replace("typing.", "")
    return s.replace("Tuple[", "tuple[").replace("List[", "list[")


def signature(fn: A.ast.FunctionDef) -> str:
    return "def %s(%s) -> %s" % (fn.name, A.ast.unparse(fn.args),
                                 A.ast.unparse(fn.returns)
                                 if fn.returns else "?")


def is_abstract(fn: A.ast.FunctionDef) -> bool:
    return "abstractmethod" in A.decorator_names(fn)


class M06Exercise(Exercise):
    directory = ""
    type_hints = "required"
    imports = {"abc", "typing"}
    local_imports = True
    forbidden = {"eval", "exec"}
    authorized_line = ("Authorized: builtins, standard types, import typing, "
                       "import abc\n" + IMPORTS_RULE)
    file = ""

    def check(self, ctx: Ctx) -> None:
        self.run_checks(ctx, ctx.tree(self.file) if self.file else None)

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        pass

    # ----------------------------------------------------- data processors
    def processors_static(self, ctx: Ctx, tree: Any) -> None:
        f = ctx.rel(self.file)
        cls = A.classes(tree)
        dp = cls.get("DataProcessor")
        if dp is None:
            ctx.ko("Classe DataProcessor absente", ABC_RULE, file=f)
            return
        if "ABC" not in A.base_names(dp):
            ctx.ko("DataProcessor n'hérite pas de ABC", ABC_RULE, file=f,
                   got="class DataProcessor(%s)" % ", ".join(
                       A.base_names(dp)))
        meths = A.methods(dp)
        want = {"validate": "def validate(self, data: Any) -> bool",
                "ingest": "def ingest(self, data: Any) -> None",
                "output": "def output(self) -> tuple[int, str]"}
        rules = {"validate": VALIDATE_RULE, "ingest": INGEST_RULE,
                 "output": OUTPUT_RULE}
        for name, sig in want.items():
            m = meths.get(name)
            if m is None:
                ctx.ko("DataProcessor.%s() absente" % name, rules[name],
                       file=f)
                continue
            if _norm(signature(m)) != _norm(sig):
                ctx.ko("Signature de DataProcessor.%s() différente du sujet"
                       % name, rules[name], expected=sig,
                       got=signature(m), file=f)
            if name in ("validate", "ingest") and not is_abstract(m):
                ctx.ko("DataProcessor.%s() n'est pas abstraite" % name,
                       ABC_RULE, file=f, expected="@abstractmethod")
            if name == "output" and is_abstract(m):
                ctx.ko("DataProcessor.output() ne doit pas être abstraite",
                       "One standard method in DataProcessor: output",
                       file=f)
        for name in SPECIALIZED:
            c = cls.get(name)
            if c is None:
                ctx.ko("Classe %s absente" % name, "Three specialized "
                       "classes NumericProcessor, TextProcessor, and "
                       "LogProcessor that inherit from the DataProcessor "
                       "class", file=f)
                continue
            if "DataProcessor" not in A.base_names(c):
                ctx.ko("%s n'hérite pas de DataProcessor" % name, ABC_RULE,
                       file=f)
            cm = A.methods(c)
            v = cm.get("validate")
            if v is None:
                ctx.ko("%s ne redéfinit pas validate()" % name,
                       "Each specialized class will need to override these "
                       "methods.", file=f)
            elif _norm(signature(v)) != _norm(want["validate"]):
                ctx.ko("Signature de %s.validate() différente" % name,
                       VALIDATE_RULE, expected=want["validate"],
                       got=signature(v), file=f)
            i = cm.get("ingest")
            if i is None:
                ctx.ko("%s ne redéfinit pas ingest()" % name,
                       "Each specialized class will need to override these "
                       "methods.", file=f)
            else:
                args = i.args.args
                ann = A.ast.unparse(args[1].annotation) if len(args) > 1 \
                    and args[1].annotation is not None else None
                if ann is None or _norm(ann) == "Any":
                    ctx.ko("%s.ingest() : le type du paramètre ne reflète "
                           "pas les types acceptés" % name,
                           "The overriding ingest method signature must "
                           "reflect the accepted types.", got=signature(i),
                           file=f)

    def processors_probe(self, ctx: Ctx) -> None:
        code = """
        m = load(os.path.join(EX, %r))
        R = {}

        def go(cls_name, steps):
            cls = getattr(m, cls_name, None)
            if cls is None:
                return
            c = capture(cls)
            if c.exc:
                R[cls_name] = {"ctor": c.exc}
                return
            p = c.value
            out = {}
            for i, (kind, arg) in enumerate(steps):
                if kind == "validate":
                    r = capture(p.validate, arg)
                    out[i] = ["validate", repr(arg), r.value, r.exc]
                elif kind == "ingest":
                    r = capture(p.ingest, arg)
                    out[i] = ["ingest", repr(arg), None, r.exc]
                else:
                    r = capture(p.output)
                    out[i] = ["output", "", r.value, r.exc]
            R[cls_name] = out

        LOG1 = {"log_level": "NOTICE", "log_message": "Connection to server"}
        LOG2 = {"log_level": "ERROR", "log_message": "Unauthorized access!!"}
        go("NumericProcessor", [
            ("validate", 42), ("validate", 3.14), ("validate", [1, 2.5, -3]),
            ("validate", "Hello"), ("validate", ["a"]),
            ("validate", [1, "a"]), ("ingest", "foo"),
            ("ingest", [1, 2, 3]), ("ingest", 4.5), ("output", None),
            ("output", None), ("output", None), ("output", None)])
        go("TextProcessor", [
            ("validate", "Hello"), ("validate", ["a", "b"]),
            ("validate", 42), ("validate", ["a", 1]), ("ingest", 42),
            ("ingest", ["Hello", "Nexus"]), ("ingest", "World"),
            ("output", None), ("output", None), ("output", None)])
        go("LogProcessor", [
            ("validate", LOG1), ("validate", [LOG1, LOG2]),
            ("validate", "Hello"), ("validate", {"a": 1}), ("ingest", "x"),
            ("ingest", [LOG1, LOG2]), ("output", None), ("output", None)])
        dp = getattr(m, "DataProcessor", None)
        if dp is not None:
            R["abstract"] = capture(dp).exc
        report("R", R)
        """ % self.file
        res = ctx.probe(code)
        R = res.probe.get("R")
        if not R:
            return
        f = ctx.rel(self.file)
        if "abstract" in R and not R["abstract"]:
            ctx.ko("DataProcessor peut être instanciée", ABC_RULE, file=f,
                   detail="Une classe abstraite (méthodes @abstractmethod) "
                          "ne doit pas pouvoir être instanciée.")
        expect = {
            "NumericProcessor": {0: True, 1: True, 2: True, 3: False,
                                 4: False, 5: False},
            "TextProcessor": {0: True, 1: True, 2: False, 3: False},
            "LogProcessor": {0: True, 1: True, 2: False, 3: False}}
        raises = {"NumericProcessor": 6, "TextProcessor": 4,
                  "LogProcessor": 4}
        outputs = {"NumericProcessor": ([9, 10, 11, 12],
                                        ["1", "2", "3", "4.5"]),
                   "TextProcessor": ([7, 8, 9], ["Hello", "Nexus", "World"]),
                   "LogProcessor": ([6, 7], None)}
        for name in SPECIALIZED:
            d = R.get(name)
            if d is None:
                continue
            if "ctor" in d:
                ctx.warn("%s() sans argument impossible : tests directs non "
                         "réalisés" % name, got=d["ctor"], file=f)
                continue
            d = {int(k): v for k, v in d.items()}
            for i, want in expect[name].items():
                kind, arg, val, exc = d[i]
                if exc or val is not want:
                    ctx.ko("%s.validate(%s) incorrect" % (name, arg),
                           VALIDATE_RULE + " This method returns a bool "
                           "that indicates if the provided data can be "
                           "ingested by this data processor.",
                           expected=repr(want), got=exc or repr(val), file=f)
            kind, arg, val, exc = d[raises[name]]
            if not exc:
                ctx.ko("%s.ingest(%s) sans validation ne lève pas "
                       "d'exception" % (name, arg), INGEST_RULE, file=f)
            idx, values = outputs[name]
            got = [d[i][2] for i in idx]
            errs = [d[i][3] for i in idx if d[i][3]]
            if errs:
                ctx.ko("%s.output() lève une exception" % name, OUTPUT_RULE,
                       got=errs[0], file=f)
                continue
            shape_ok = all(isinstance(g, list) and len(g) == 2
                           and isinstance(g[0], int)
                           and isinstance(g[1], str) for g in got)
            if not shape_ok:
                ctx.ko("%s.output() ne renvoie pas un tuple (int, str)"
                       % name, OUTPUT_RULE, got=repr(got), file=f)
                continue
            ranks = [g[0] for g in got]
            if ranks != list(range(ranks[0], ranks[0] + len(ranks))):
                ctx.ko("%s.output() : rangs de traitement incorrects" % name,
                       OUTPUT_RULE, expected="rangs consécutifs (0, 1, 2, "
                       "...)", got=repr(ranks), file=f)
            vals = [g[1] for g in got]
            if values is not None and vals != values:
                ctx.ko("%s : données stockées/extraites incorrectes" % name,
                       "keeping each item separated, waiting to be extracted"
                       " piece by piece using the output method (oldest "
                       "first)", expected=repr(values), got=repr(vals),
                       file=f)
            if name == "LogProcessor" and not (
                    "NOTICE" in vals[0] and "Connection to server" in vals[0]
                    and "ERROR" in vals[1]):
                ctx.ko("LogProcessor : entrées de log mal converties", "The "
                       "LogProcessor ingests a dict of string key-value "
                       "pairs, and lists of that type. It then converts the "
                       "data into strings", expected="'NOTICE: Connection to"
                       " server', 'ERROR: Unauthorized access!!'",
                       got=repr(vals), file=f)


class Ex0(M06Exercise):
    ex_id, title = "ex0", "Data Processor"
    files = ["data_processor.py"]
    file = files[0]
    mypy_expected = r'Argument 1 to "ingest"|\[arg-type\]'
    mypy_note = ("Test at least one invalid data item with the ingest method "
                 "without prior validation ... This will leave you with a "
                 "mypy warning, on purpose.")
    EXAMPLE = """
        === Code Nexus - Data Processor ===

        Testing Numeric Processor...
         Trying to validate input '42': True
         Trying to validate input 'Hello': False
         Test invalid ingestion of string 'foo' without prior validation:
         Got exception: Improper numeric data
         Processing data: [1, 2, 3, 4, 5]
         Extracting 3 values...
         Numeric value 0: 1
         Numeric value 1: 2
         Numeric value 2: 3

        Testing Text Processor...
         Trying to validate input '42': False
         Processing data: ['Hello', 'Nexus', 'World']
         Extracting 1 value...
         Text value 0: Hello

        Testing Log Processor...
         Trying to validate input 'Hello': False
         Processing data: [{'log_level': 'NOTICE', 'log_message': 'Connection to server'}, {'log_level': 'ERROR', 'log_message': 'Unauthorized access!!'}]
         Extracting 2 values...
         Log entry 0: NOTICE: Connection to server
         Log entry 1: ERROR: Unauthorized access!!"""  # noqa: E501

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        self.processors_static(ctx, tree)
        check_script(ctx, self.file, lines(self.EXAMPLE), "Example: $> "
                     "python3 data_processor.py", strict=False, cwd="")
        self.processors_probe(ctx)


BATCH = ['Hello world', [3.14, -1, 2.71],
         [{'log_level': 'WARNING', 'log_message':
           'Telnet access! Use ssh instead'},
          {'log_level': 'INFO', 'log_message': 'User wil is connected'}],
         42, ['Hi', 'five']]
STREAM_RULE = ("Create a DataStream class that will receive a stream of data "
               "containing different types and then will route each element "
               "to the appropriate data processor using polymorphic "
               "behavior.")


class Ex1(M06Exercise):
    ex_id, title = "ex1", "Polymorphic Data Stream"
    files = ["data_stream.py"]
    file = files[0]
    mypy_expected = Ex0.mypy_expected
    SIGS = {"register_processor": "def register_processor(self, proc: "
                                  "DataProcessor) -> None",
            "process_stream": "def process_stream(self, stream: "
                              "list[typing.Any]) -> None",
            "print_processors_stats": "def print_processors_stats(self) -> "
                                      "None"}
    EXAMPLE = """
        === Code Nexus - Data Stream ===

        Initialize Data Stream...
        == DataStream statistics ==
        No processor found, no data

        Registering Numeric Processor

        Send first batch of data on stream: ['Hello world', [3.14, -1, 2.71], [{'log_level': 'WARNING', 'log_message': 'Telnet access! Use ssh instead'}, {'log_level': 'INFO', 'log_message': 'User wil is connected'}], 42, ['Hi', 'five']]
        DataStream error - Can't process element in stream: Hello world
        DataStream error - Can't process element in stream: [{'log_level': 'WARNING', 'log_message': 'Telnet access! Use ssh instead'}, {'log_level': 'INFO', 'log_message': 'User wil is connected'}]
        DataStream error - Can't process element in stream: ['Hi', 'five']
        == DataStream statistics ==
        Numeric Processor: total 4 items processed, remaining 4 on processor

        Registering other data processors
        Send the same batch again
        == DataStream statistics ==
        Numeric Processor: total 8 items processed, remaining 8 on processor
        Text Processor: total 3 items processed, remaining 3 on processor
        Log Processor: total 2 items processed, remaining 2 on processor

        Consume some elements from the data processors: Numeric 3, Text 2, Log 1
        == DataStream statistics ==
        Numeric Processor: total 8 items processed, remaining 5 on processor
        Text Processor: total 3 items processed, remaining 1 on processor
        Log Processor: total 2 items processed, remaining 1 on processor"""  # noqa: E501

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        self.processors_static(ctx, tree)
        self.stream_static(ctx, tree, self.SIGS)
        check_script(ctx, self.file, lines(self.EXAMPLE), "Example: $> "
                     "python3 data_stream.py", strict=False, cwd="")
        self.processors_probe(ctx)
        self.stream_probe(ctx)

    def stream_static(self, ctx: Ctx, tree: Any, sigs: dict[str, str]
                      ) -> None:
        f = ctx.rel(self.file)
        ds = A.classes(tree).get("DataStream")
        if ds is None:
            ctx.ko("Classe DataStream absente", STREAM_RULE, file=f)
            return
        meths = A.methods(ds)
        for name, sig in sigs.items():
            m = meths.get(name)
            if m is None:
                ctx.ko("DataStream.%s() absente" % name,
                       "This class will implement the " + sig, file=f)
            elif _norm(signature(m)) != _norm(sig):
                ctx.ko("Signature de DataStream.%s() différente" % name,
                       "This class will implement the " + sig,
                       expected=sig, got=signature(m), file=f)
        bad = []
        for c in A.calls_named(ds, "isinstance"):
            names = {n.id for n in A.ast.walk(c) if isinstance(n, A.ast.Name)}
            hit = names & set(SPECIALIZED)
            if hit:
                bad.append("ligne %d : %s" % (c.lineno, A.ast.unparse(c)))
        if bad:
            ctx.ko("DataStream teste le type concret des processeurs",
                   STREAM_RULE, got="\n".join(bad), file=f,
                   detail="Le routage doit passer par proc.validate() "
                          "(polymorphisme), pas par isinstance(..., "
                          "NumericProcessor).")

    def stream_probe(self, ctx: Ctx) -> None:
        code = """
        import json
        m = load(os.path.join(EX, %r))
        BATCH = json.loads(%r)
        R = {}
        ds = m.DataStream()
        num = m.NumericProcessor()
        R["empty_stats"] = capture(ds.print_processors_stats).out
        capture(ds.register_processor, num)
        c = capture(ds.process_stream, BATCH)
        R["first"] = {"out": c.out, "exc": c.exc}
        R["stats1"] = capture(ds.print_processors_stats).out
        txt, log = m.TextProcessor(), m.LogProcessor()
        capture(ds.register_processor, txt)
        capture(ds.register_processor, log)
        c = capture(ds.process_stream, BATCH)
        R["second_exc"] = c.exc
        R["stats2"] = capture(ds.print_processors_stats).out
        def drain(p):
            out = []
            for _ in range(20):
                r = capture(p.output)
                if r.exc or r.value is None:
                    break
                out.append(r.value[1])
            return out
        R["num"] = drain(num)
        R["txt"] = drain(txt)
        R["log"] = drain(log)
        report("R", R)
        """ % (self.file, json.dumps(BATCH))
        R = ctx.probe(code).probe.get("R")
        if not R:
            return
        f = ctx.rel(self.file)
        if R["first"]["exc"] or R["second_exc"]:
            ctx.ko("process_stream() plante", STREAM_RULE,
                   got=R["first"]["exc"] or R["second_exc"], file=f)
            return
        errs = [ln for ln in R["first"]["out"].splitlines() if ln.strip()]
        if len(errs) < 3:
            ctx.ko("Pas de message d'erreur pour les éléments non traités",
                   "Error messages will be printed if no data processor can "
                   "handle an element.", expected="3 messages (Hello world, "
                   "logs, ['Hi', 'five'])", got=R["first"]["out"] or
                   "(rien)", file=f)
        want = {"num": ["3.14", "-1", "2.71", "42"] * 2,
                "txt": ["Hello world", "Hi", "five"]}
        for k, label in (("num", "NumericProcessor"),
                         ("txt", "TextProcessor")):
            if R[k] != want[k]:
                ctx.ko("Routage incorrect vers %s" % label, STREAM_RULE,
                       expected=repr(want[k]), got=repr(R[k]), file=f,
                       detail="Batch envoyé deux fois (Numeric enregistré "
                              "seul la première fois).")
        if len(R["log"]) != 2:
            ctx.ko("Routage incorrect vers LogProcessor", STREAM_RULE,
                   expected="2 entrées", got=repr(R["log"]), file=f)
        if not re.search(r"\b8\b", R["stats2"]) or not re.search(
                r"\b3\b", R["stats2"]):
            ctx.ko("print_processors_stats() n'affiche pas les bons "
                   "compteurs", "Finally, the class will implement the def "
                   "print_processors_stats(self) -> None: method in order "
                   "to print stream statistics.", expected="Numeric : 8 "
                   "traités, Text : 3, Log : 2", got=R["stats2"], file=f)
        if not R["empty_stats"].strip():
            ctx.warn("Statistiques vides sans processeur", "== DataStream "
                     "statistics ==\nNo processor found, no data", file=f)


PLUGIN_RULE = ("A new ExportPlugin class that inherits from the special "
               "Protocol class. This class will define the following method,"
               " which will act as a constraint for each export plugin: def "
               "process_output(self, data: list[tuple[int, str]]) -> None:")


class Ex2(Ex1):
    ex_id, title = "ex2", "Data Pipeline"
    files = ["data_pipeline.py"]
    file = files[0]
    SIGS = dict(Ex1.SIGS, output_pipeline="def output_pipeline(self, nb: "
                "int, plugin: ExportPlugin) -> None")
    EXAMPLE = ""

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        f = ctx.rel(self.file)
        self.processors_static(ctx, tree)
        self.stream_static(ctx, tree, self.SIGS)
        cls = A.classes(tree)
        ep = cls.get("ExportPlugin")
        if ep is None:
            ctx.ko("Classe ExportPlugin absente", PLUGIN_RULE, file=f)
        else:
            if "Protocol" not in A.base_names(ep):
                ctx.ko("ExportPlugin n'hérite pas de Protocol", PLUGIN_RULE,
                       got="class ExportPlugin(%s)" % ", ".join(
                           A.base_names(ep)), file=f)
            m = A.methods(ep).get("process_output")
            sig = ("def process_output(self, data: list[tuple[int, str]]) "
                   "-> None")
            if m is None:
                ctx.ko("ExportPlugin.process_output() absente", PLUGIN_RULE,
                       file=f)
            elif _norm(signature(m)) != _norm(sig):
                ctx.ko("Signature de process_output() différente",
                       PLUGIN_RULE, expected=sig, got=signature(m), file=f)
        plugins = [n for n, c in cls.items() if n != "ExportPlugin"
                   and "process_output" in A.methods(c)]
        csv = [p for p in plugins if "csv" in p.lower()]
        js = [p for p in plugins if "json" in p.lower()]
        if not csv or not js:
            ctx.ko("Plugins CSV et JSON absents", "Create at least a CSV "
                   "export plugin and a JSON export plugin.",
                   got="plugins trouvés : " + (", ".join(plugins) or
                                               "aucun"), file=f)
        inherit = [p for p in plugins if "ExportPlugin" in
                   A.base_names(cls[p])]
        if inherit:
            ctx.warn("Les plugins héritent de ExportPlugin", "This will be "
                     "achieved by using a plugin system for export classes, "
                     "made export-compatible through duck typing.",
                     got=", ".join(inherit), file=f,
                     detail="Avec un Protocol, les plugins n'ont pas besoin "
                            "d'en hériter : c'est tout l'intérêt du duck "
                            "typing.")
        res = check_script(ctx, self.file, None, None, cwd="")
        if not res.crashed:
            out = res.lines()
            for want in ("3.14,-1,2.71", "Hello world,Hi,five"):
                if want not in out:
                    ctx.warn("Ligne CSV de l'exemple absente : %s" % want,
                             "Send 3 processed data from each processor to "
                             "a CSV plugin", got=res.stdout[-1500:], file=f)
        self.processors_probe(ctx)
        self.stream_probe(ctx)
        if csv and js:
            self.plugin_probe(ctx, csv[0], js[0])

    def plugin_probe(self, ctx: Ctx, csv: str, js: str) -> None:
        code = """
        import json
        m = load(os.path.join(EX, %r))
        BATCH = json.loads(%r)
        ds = m.DataStream()
        for name in ("NumericProcessor", "TextProcessor", "LogProcessor"):
            capture(ds.register_processor, getattr(m, name)())
        capture(ds.process_stream, BATCH)
        c1 = capture(ds.output_pipeline, 3, getattr(m, %r)())
        c2 = capture(ds.output_pipeline, 5, getattr(m, %r)())
        report("csv", c1.as_dict())
        report("json", c2.as_dict())
        """ % (self.file, json.dumps(BATCH), csv, js)
        p = ctx.probe(code).probe
        f = ctx.rel(self.file)
        rule = ("The DataStream class will now implement the def "
                "output_pipeline(self, nb: int, plugin: ExportPlugin) -> "
                "None: method, to be used after calling process_stream, that "
                "will consume nb elements from all registered data "
                "processors and export them using the provided compatible "
                "plugin. ... manually create valid CSV and JSON strings.")
        c = p.get("csv")
        if c:
            if c["exc"]:
                ctx.ko("output_pipeline(3, CSV) plante", rule, got=c["exc"],
                       file=f)
            else:
                out = c["out"].splitlines()
                for want in ("3.14,-1,2.71", "Hello world,Hi,five",
                             "WARNING: Telnet access! Use ssh instead,INFO: "
                             "User wil is connected"):
                    if want not in out:
                        ctx.ko("Export CSV incorrect", rule, expected=want,
                               got=c["out"], file=f)
                        break
        j = p.get("json")
        if j:
            if j["exc"]:
                ctx.ko("output_pipeline(5, JSON) plante", rule, got=j["exc"],
                       file=f)
            else:
                objs = []
                for ln in j["out"].splitlines():
                    s = ln.strip()
                    if s.startswith(("{", "[")):
                        try:
                            objs.append(json.loads(s))
                        except ValueError:
                            ctx.ko("Export JSON invalide", rule, got=s,
                                   file=f, detail="json.loads() échoue sur "
                                                  "cette ligne.")
                            return
                flat = json.dumps(objs)
                if not objs or "42" not in flat:
                    ctx.ko("Export JSON incorrect", rule,
                           expected='{"item_3": "42"} (élément restant du '
                                    'Numeric Processor)', got=j["out"],
                           file=f)
                else:
                    ctx.ok("export JSON valide")


# =================================================================== ex3
FACTORY_RULE = ("Your ex3 package must only expose the factories, never the "
                "concrete entities.")
CAPA_RULE = ("A TransformCapability abstract class (inheriting from ABC) "
             "defining the transform and revert abstract methods. It must not"
             " inherit from Creature: an ability should not be forced onto "
             "every entity. An attribute keeps the transformed state and "
             "changes what attack returns.")


def package_classes(ctx: Ctx, pkg: str) -> dict[str, tuple[str, Any]]:
    out: dict[str, tuple[str, Any]] = {}
    base = ctx.path(pkg)
    if not base.is_dir():
        return out
    for p in sorted(base.glob("*.py")):
        rel = str(p.relative_to(ctx.path("")))
        for name, c in A.classes(ctx.tree(rel)).items():
            out[name] = (rel, c)
    return out


def abstract_names(c: Any) -> set[str]:
    return {n for n, m in A.methods(c).items() if is_abstract(m)}


class Ex3(M06Exercise):
    ex_id, title = "ex3", "Entity Factories"
    files = ["battle.py", "capacitor.py", "ex3/__init__.py"]
    glob_files = ["ex3/*.py"]

    def roles(self, ctx: Ctx) -> dict[str, Any]:
        cls = package_classes(ctx, "ex3")
        creature = [n for n, (_, c) in cls.items()
                    if "attack" in abstract_names(c)
                    and "describe" in A.methods(c)]
        capa = [n for n, (_, c) in cls.items()
                if {"transform", "revert"} <= abstract_names(c)]
        factory = [n for n, (_, c) in cls.items()
                   if {"create_base", "create_evolved"} <= abstract_names(c)]

        def subclasses(parents: list[str]) -> list[str]:
            out, todo = [], list(parents)
            while todo:
                cur = todo.pop()
                for n, (_, c) in cls.items():
                    if cur in A.base_names(c) and n not in out:
                        out.append(n)
                        todo.append(n)
            return out

        return {"cls": cls, "creature": creature, "capa": capa,
                "factory": factory,
                "entities": [n for n in subclasses(creature)
                             if not abstract_names(cls[n][1])],
                "factories": [n for n in subclasses(factory)
                              if not abstract_names(cls[n][1])],
                "subclasses": subclasses}

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        r = self.roles(ctx)
        cls = r["cls"]
        if not r["creature"]:
            ctx.ko("Classe abstraite Creature introuvable", "A Creature "
                   "abstract class (inheriting from ABC) that holds "
                   "attributes for the name and the type of the entity, an "
                   "abstract method attack, and a concrete method describe")
        for n in r["creature"] + r["capa"] + r["factory"]:
            if "ABC" not in A.base_names(cls[n][1]):
                ctx.ko("%s n'hérite pas de ABC" % n, "(inheriting from ABC)",
                       file=cls[n][0])
        if not r["capa"]:
            ctx.ko("Capacité TransformCapability introuvable", CAPA_RULE)
        for n in r["capa"]:
            inherited = set(A.base_names(cls[n][1])) & set(
                r["creature"] + r["entities"])
            if inherited:
                ctx.ko("%s hérite de Creature" % n, CAPA_RULE,
                       file=cls[n][0])
        if not r["factory"]:
            ctx.ko("Fabrique abstraite CreatureFactory introuvable", "A "
                   "CreatureFactory abstract class (inheriting from ABC) with"
                   " the create_base and create_evolved abstract methods.")
        if len(r["factories"]) < 2:
            ctx.ko("Moins de 2 fabriques concrètes", "Two concrete factories"
                   " inheriting from CreatureFactory: FlameFactory (base "
                   "Flameling, evolved Pyrodon) and TransformCreatureFactory "
                   "(base Shiftling, evolved Morphagon).",
                   got=", ".join(r["factories"]) or "aucune")
        both = [n for n in r["entities"] if any(
            b in r["capa"] for b in A.base_names(cls[n][1]))
            or any(c in r["subclasses"](r["capa"]) for c in [n])]
        if len(both) < 2:
            ctx.ko("Moins de 2 entités avec la capacité de transformation",
                   "Two concrete entities that inherit from both Creature "
                   "and TransformCapability: Shiftling and Morphagon.",
                   got=", ".join(both) or "aucune")
        entity_names = set(r["entities"])
        exported = set()
        for imp in A.imports(ctx.tree("ex3/__init__.py")):
            exported |= set(imp.names)
        if exported & entity_names:
            ctx.ko("Le package ex3 expose des entités concrètes",
                   FACTORY_RULE, got=", ".join(sorted(exported &
                                                      entity_names)),
                   file="ex3/__init__.py")
        for script in ("battle.py", "capacitor.py"):
            imported = set()
            for imp in A.imports(ctx.tree(script)):
                imported |= set(imp.names) | {imp.module.split(".")[-1]}
            bad = imported & entity_names
            if bad:
                ctx.ko("%s importe des entités concrètes" % script,
                       "battle.py (at the root of the repository) tests the "
                       "factory interface", got=", ".join(sorted(bad)),
                       file=script)
        funcs = [f for f in A.functions(ctx.tree("battle.py"))
                 if f != "main"]
        if len(funcs) < 2:
            ctx.ko("battle.py : il faut deux fonctions (une fabrique, deux "
                   "fabriques)", "A single function that receives a factory,"
                   " creates the base then the evolved entity, and describes"
                   " and attacks with each. Another function that receives "
                   "two factories and makes their base entities fight.",
                   got=", ".join(funcs) or "aucune", file="battle.py")
        self.probe_package(ctx, r)
        check_script(
            ctx, "battle.py", lines("""
            Testing factory
            Flameling is a Fire type Creature
            Flameling uses Ember!
            Pyrodon is a Fire/Flying type Creature
            Pyrodon uses Flamethrower!

            Testing factory
            Shiftling is a Normal type Creature
            Shiftling attacks normally.
            Morphagon is a Normal/Dragon type Creature
            Morphagon attacks normally.

            Testing battle
            Flameling is a Fire type Creature
             vs.
            Shiftling is a Normal type Creature
             fight!
            Flameling uses Ember!
            Shiftling attacks normally."""),
            "You may use different entity and factory names, as long as the "
            "design patterns are correctly implemented.", strict=False,
            cwd="")
        check_script(
            ctx, "capacitor.py", lines("""
            Testing Creature with transform capability
             base:
            Shiftling is a Normal type Creature
            Shiftling attacks normally.
            Shiftling shifts into a sharper form!
            Shiftling performs a boosted strike!
            Shiftling returns to normal.
             evolved:
            Morphagon is a Normal/Dragon type Creature
            Morphagon attacks normally.
            Morphagon morphs into a dragonic battle form!
            Morphagon unleashes a devastating morph strike!
            Morphagon stabilizes its form."""),
            "You may use different entity and factory names, as long as the "
            "design patterns are correctly implemented.", strict=False,
            cwd="")

    def probe_package(self, ctx: Ctx, r: dict[str, Any]) -> None:
        code = """
        import importlib, inspect, abc
        R = {}
        pkg = importlib.import_module("ex3")
        exposed = [n for n in dir(pkg) if not n.startswith("_")]
        R["exposed"] = {n: [k.__name__ for k in getattr(pkg, n).__mro__]
                        if inspect.isclass(getattr(pkg, n)) else "obj"
                        for n in exposed}
        facts = [getattr(pkg, n) for n in exposed
                 if inspect.isclass(getattr(pkg, n))
                 and hasattr(getattr(pkg, n), "create_base")
                 and not inspect.isabstract(getattr(pkg, n))]
        R["factories"] = []
        for F in facts:
            d = {"name": F.__name__}
            c = capture(F)
            if c.exc:
                d["exc"] = c.exc
                R["factories"].append(d)
                continue
            f = c.value
            for kind in ("create_base", "create_evolved"):
                e = capture(getattr(f, kind))
                if e.exc:
                    d[kind] = {"exc": e.exc}
                    continue
                ent = e.value
                info = {"cls": type(ent).__name__}
                info["describe"] = capture(ent.describe).value \\
                    if hasattr(ent, "describe") else None
                a1 = capture(ent.attack)
                info["attack"] = [a1.value, a1.out, a1.exc]
                if hasattr(ent, "transform"):
                    t = capture(ent.transform)
                    a2 = capture(ent.attack)
                    rv = capture(ent.revert)
                    a3 = capture(ent.attack)
                    info["transformed"] = [t.exc, [a2.value, a2.out],
                                           rv.exc, [a3.value, a3.out]]
                d[kind] = info
            R["factories"].append(d)
        report("R", R)
        """
        R = ctx.probe(code).probe.get("R")
        if not R:
            return
        entities = set(r["entities"])
        bad = []
        for n, mro in R["exposed"].items():
            if mro == "obj":
                continue
            if n in entities or (set(mro[1:]) & set(r["creature"])):
                bad.append(n)
        if bad and not any(i.title.startswith("Le package ex3 expose des")
                           for i in ctx.result.issues):
            ctx.ko("Le package ex3 expose des entités concrètes",
                   FACTORY_RULE, got=", ".join(sorted(bad)),
                   file="ex3/__init__.py")
        if len(R["factories"]) < 2:
            ctx.ko("Le package ex3 n'expose pas les deux fabriques",
                   FACTORY_RULE, got="exposé : " + ", ".join(R["exposed"]),
                   file="ex3/__init__.py")
        for fac in R["factories"]:
            if "exc" in fac:
                ctx.ko("%s() impossible à instancier" % fac["name"],
                       got=fac["exc"])
                continue
            for kind in ("create_base", "create_evolved"):
                info = fac.get(kind, {})
                label = "%s.%s()" % (fac["name"], kind)
                if "exc" in info:
                    ctx.ko(label + " plante", got=info["exc"])
                    continue
                if not isinstance(info.get("describe"), str):
                    ctx.ko(label + " : describe() ne renvoie pas une chaîne",
                           "a concrete method describe that returns a "
                           "standard message built from the name and the "
                           "type.", got=repr(info.get("describe")))
                val, out, exc = info["attack"]
                if exc:
                    ctx.ko(label + " : attack() plante", got=exc)
                elif not isinstance(val, str):
                    ctx.ko(label + " : attack() ne renvoie pas un message",
                           "their attack returns an appropriate message",
                           got="renvoie %r, affiche %r" % (val, out))
                tr = info.get("transformed")
                if tr:
                    texc, after, rexc, back = tr
                    if texc or rexc:
                        ctx.ko(label + " : transform()/revert() plante",
                               CAPA_RULE, got=texc or rexc)
                    elif after == [val, out]:
                        ctx.ko(label + " : attack() identique après "
                               "transform()", CAPA_RULE,
                               got="avant : %r\naprès : %r" % (val,
                                                               after[0]))
                    elif back != [val, out]:
                        ctx.ko(label + " : revert() ne rétablit pas "
                               "l'attaque normale", CAPA_RULE,
                               expected=repr(val), got=repr(back[0]))


# =================================================================== ex4
STRAT_RULE = ("A BattleStrategy abstract class (inheriting from ABC) "
              "defining the act and is_valid abstract methods. is_valid "
              "returns a bool telling whether an entity is suitable for the "
              "strategy; act is called by the tournament.")
ISINST_RULE = ("A strategy checks capabilities with isinstance, never the "
               "concrete family.")


class Ex4(Ex3):
    ex_id, title = "ex4", "Abstract Strategy"
    files = ["tournament.py", "ex4/__init__.py"]
    glob_files = ["ex4/*.py"]

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        cls = package_classes(ctx, "ex4")
        r3 = self.roles(ctx)
        bs = cls.get("BattleStrategy")
        if bs is None:
            ctx.ko("Classe BattleStrategy absente", STRAT_RULE)
        else:
            if "ABC" not in A.base_names(bs[1]):
                ctx.ko("BattleStrategy n'hérite pas de ABC", STRAT_RULE,
                       file=bs[0])
            if not {"act", "is_valid"} <= abstract_names(bs[1]):
                ctx.ko("act / is_valid ne sont pas abstraites", STRAT_RULE,
                       got=", ".join(abstract_names(bs[1])) or "aucune",
                       file=bs[0])
        for name in ("NormalStrategy", "AggressiveStrategy"):
            c = cls.get(name)
            if c is None:
                ctx.ko("Classe %s absente" % name, "Two concrete strategies "
                       "inheriting from BattleStrategy: NormalStrategy ... "
                       "AggressiveStrategy")
            elif "BattleStrategy" not in A.base_names(c[1]):
                ctx.ko("%s n'hérite pas de BattleStrategy" % name,
                       STRAT_RULE, file=c[0])
        entities = set(r3["entities"])
        agg = cls.get("AggressiveStrategy")
        if agg is not None:
            iv = A.methods(agg[1]).get("is_valid")
            calls = A.calls_named(iv, "isinstance") if iv else []
            used = {n.id for c in calls for n in A.ast.walk(c)
                    if isinstance(n, A.ast.Name)}
            if not calls:
                ctx.ko("AggressiveStrategy.is_valid() n'utilise pas "
                       "isinstance", ISINST_RULE, file=agg[0])
            elif used & entities:
                ctx.ko("is_valid() teste la famille concrète", ISINST_RULE,
                       got=", ".join(sorted(used & entities)), file=agg[0])
        exc = [n for n, (_, c) in cls.items()
               if any(b.endswith(("Error", "Exception"))
                      for b in A.base_names(c))]
        if not exc:
            ctx.ko("Pas d'exception dédiée dans ex4", "If act is called with"
                   " an entity the strategy is not valid for, raise a "
                   "dedicated exception with a clear message.")
        if not [f for f in A.functions(ctx.tree("tournament.py"))
                if f != "main"]:
            ctx.ko("tournament.py : pas de fonction de combat", "Defines a "
                   "single battle function that takes a list of opponents, "
                   "each a tuple of a CreatureFactory and a BattleStrategy",
                   file="tournament.py")
        code = """
        import importlib, inspect
        ex3 = importlib.import_module("ex3")
        ex4 = importlib.import_module("ex4")
        mods = [ex4] + [importlib.import_module("ex4." + n[:-3])
                        for n in os.listdir(os.path.join(ROOT, "ex4"))
                        if n.endswith(".py") and n != "__init__.py"]
        def find(name):
            for m in mods:
                if hasattr(m, name):
                    return getattr(m, name)
        Normal, Aggr = find("NormalStrategy"), find("AggressiveStrategy")
        facts = [getattr(ex3, n) for n in dir(ex3)
                 if inspect.isclass(getattr(ex3, n))
                 and hasattr(getattr(ex3, n), "create_base")
                 and not inspect.isabstract(getattr(ex3, n))]
        R = {"plain": [], "capable": []}
        for F in facts:
            for kind in ("create_base", "create_evolved"):
                e = getattr(F(), kind)()
                key = "capable" if hasattr(e, "transform") else "plain"
                R[key].append(e)
        out = {}
        if Normal and Aggr and R["plain"] and R["capable"]:
            n, a = Normal(), Aggr()
            p, c = R["plain"][0], R["capable"][0]
            out["n_plain"] = capture(n.is_valid, p).value
            out["n_cap"] = capture(n.is_valid, c).value
            out["a_plain"] = capture(a.is_valid, p).value
            out["a_cap"] = capture(a.is_valid, c).value
            r = capture(a.act, p)
            out["bad_act"] = [r.exc_type, r.exc,
                              [k.__module__ for k in type(r.exc_obj).__mro__]
                              if r.exc_obj is not None else []]
            r = capture(a.act, c)
            out["good_act"] = [r.exc, r.out, repr(r.value)]
        report("R", out)
        """
        R = ctx.probe(code).probe.get("R")
        if R:
            for k, want, label in (("n_plain", True, "NormalStrategy / "
                                    "entité simple"),
                                   ("n_cap", True, "NormalStrategy / entité "
                                    "transformable"),
                                   ("a_plain", False, "AggressiveStrategy / "
                                    "entité simple"),
                                   ("a_cap", True, "AggressiveStrategy / "
                                    "entité transformable")):
                if R.get(k) is not want:
                    ctx.ko("is_valid() incorrect : %s" % label, STRAT_RULE
                           + " NormalStrategy, suitable for any entity ... "
                           "AggressiveStrategy, suitable for entities with "
                           "the transform capability", expected=repr(want),
                           got=repr(R.get(k)))
            et, emsg, emods = R["bad_act"]
            if not et:
                ctx.ko("AggressiveStrategy.act() n'échoue pas sur une entité"
                       " simple", "If act is called with an entity the "
                       "strategy is not valid for, raise a dedicated "
                       "exception with a clear message.")
            elif emods and emods[0] == "builtins":
                ctx.ko("Exception non dédiée levée par act()", "raise a "
                       "dedicated exception with a clear message.", got=emsg)
            if R["good_act"][0]:
                ctx.ko("AggressiveStrategy.act() plante sur une entité "
                       "transformable", STRAT_RULE, got=R["good_act"][0])
        check_script(
            ctx, "tournament.py", lines("""
            Tournament 0 (basic)
             [ (Flameling+Normal), (Shiftling+Aggressive) ]
            *** Tournament ***
            2 opponents involved

            * Battle *
            Flameling is a Fire type Creature
             vs.
            Shiftling is a Normal type Creature
             now fight!
            Flameling uses Ember!
            Shiftling shifts into a sharper form!
            Shiftling performs a boosted strike!
            Shiftling returns to normal.

            Tournament 1 (error)
             [ (Shiftling+Aggressive), (Flameling+Aggressive) ]
            *** Tournament ***
            2 opponents involved

            * Battle *
            Shiftling is a Normal type Creature
             vs.
            Flameling is a Fire type Creature
             now fight!
            Shiftling shifts into a sharper form!
            Shiftling performs a boosted strike!
            Shiftling returns to normal.
            Battle error, aborting tournament: Invalid Creature 'Flameling' for this aggressive strategy"""),  # noqa: E501
            "Example: $> python3 tournament.py (names may differ)",
            strict=False, cwd="")


class Module06bis(Module):
    id = "06bis"
    title = "Code Nexus"
    pdf = "python_module_06bis.pdf"
    signature = ["data_processor.py", "data_stream.py", "data_pipeline.py",
                 "ex3/__init__.py", "battle.py", "capacitor.py",
                 "ex4/__init__.py", "tournament.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4()]
    flake8_rule = "Your project must adhere to the flake8 coding standard."
    hints_rule = ("All code must include comprehensive type annotations. "
                  "Check this using mypy.")
    only_requested_rule = ("You only need to submit the files requested by "
                           "the subject of this project.")


MODULE = Module06bis()
