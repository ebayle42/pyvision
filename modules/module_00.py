"""Module 00 : Growing Code (Python Fundamentals Through Garden Data)."""
from __future__ import annotations

from typing import Any

from core.base import A, Ctx, Exercise, Module, lines

ONLY_FUNC = ("IMPORTANT: For each exercise, you must write ONLY a function "
             "(not a main program). Each file should contain only the "
             "requested function that handles input and output directly.")
NAME_RULE = "Function names must match exactly what is requested."


class M00Exercise(Exercise):
    main_guard = "forbidden"
    type_hints = "recommended"
    imports: set[str] | None = set()
    func: str = ""
    helpers_allowed = False

    def check_only_function(self, ctx: Ctx, file: str,
                            funcs: list[str]) -> bool:
        tree = ctx.tree(file)
        defined = A.functions(tree)
        ok = True
        for f in funcs:
            if f not in defined:
                ctx.ko("Fonction %s() absente de %s" % (f, file), NAME_RULE,
                       expected="def %s(...)" % f,
                       got="\n".join("def %s(...)" % n for n in defined)
                       or "(aucune fonction)", file=ctx.rel(file))
                ok = False
        extra = [n for n in defined if n not in funcs]
        if extra and not self.helpers_allowed:
            ctx.ko("Fonctions en plus dans %s" % file,
                   "Each file should contain only the requested function.",
                   got=", ".join(extra), file=ctx.rel(file))
        classes = [n for n in tree.body if isinstance(n, A.ast.ClassDef)]
        if classes:
            ctx.ko("Classe définie dans %s" % file,
                   "Each file should contain only the requested function.",
                   got=", ".join(c.name for c in classes),
                   file=ctx.rel(file))
        return ok

    def scenario_checks(self, ctx: Ctx, file: str, func: str,
                        scenarios: list[dict[str, Any]], rule: str) -> None:
        """Chaque scénario : inputs, prompts attendus, sortie attendue."""
        results = ctx.call(file, func, scenarios)
        if results is None:
            return
        prompts_checked = False
        for sc, r in zip(scenarios, results):
            label = sc["label"]
            expected = list(sc["expected"])
            if r["timeout"]:
                ctx.ko(label + " : délai dépassé (boucle infinie ?)", rule,
                       got=r["out"][-1000:], file=ctx.rel(file),
                       kind="crash")
                continue
            got = r["out"].splitlines()
            if "prompts" in sc:
                if not prompts_checked:
                    ctx.check_prompts(func + "()", sc["prompts"],
                                      r["prompts"], rule, file=ctx.rel(file))
                    prompts_checked = True
                # Prompt déjà signalé : on compare le reste de la sortie
                # avec le prompt de l'élève pour ne pas répéter l'erreur.
                for want, have in zip(sc["prompts"], r["prompts"]):
                    if want != have:
                        expected = [have + e[len(want):]
                                    if e.startswith(want) else e
                                    for e in expected]
            elif r["input_calls"]:
                ctx.ko(label + " : input() appelé alors que l'exercice ne "
                       "lit aucune saisie", rule, got=repr(r["prompts"]),
                       file=ctx.rel(file))
            if r["exc"] and not r["exhausted"]:
                ctx.ko(label + " : la fonction plante", rule,
                       got=r["exc"], file=ctx.rel(file), kind="crash")
                continue
            if r["exhausted"]:
                ctx.ko(label + " : input() appelé trop de fois", rule,
                       expected="%d saisie(s)" % len(sc.get("inputs", [])),
                       got=repr(r["prompts"]), file=ctx.rel(file),
                       kind="crash")
                continue
            ctx.compare(label, expected, got, rule,
                        file=ctx.rel(file), detail=sc.get("detail"))
            if r["value"] is not None and sc.get("returns_none", True):
                ctx.warn(label + " : la fonction renvoie une valeur",
                         "The function should handle output directly.",
                         kind="output",
                         got=repr(r["value"]), file=ctx.rel(file))

    def check(self, ctx: Ctx) -> None:
        file = self.files[0]
        if self.check_only_function(ctx, file, [self.func]):
            self.behaviour(ctx)

    def behaviour(self, ctx: Ctx) -> None:
        pass


def _io(label: str, inputs: list[str], prompts: list[str], expected: str,
        detail: str | None = None) -> dict[str, Any]:
    return {"label": label, "inputs": inputs, "prompts": prompts,
            "expected": lines(expected), "detail": detail}


class Ex0(M00Exercise):
    ex_id, title, directory = "ex0", "Hello Garden", "ex0"
    files = ["ft_hello_garden.py"]
    func = "ft_hello_garden"
    authorized = {"print"}
    authorized_line = "Authorized: print()"

    def behaviour(self, ctx: Ctx) -> None:
        self.scenario_checks(ctx, self.files[0], self.func, [
            {"label": "ft_hello_garden()", "inputs": [],
             "expected": ["Hello, Garden Community!"]}],
            ">>> ft_hello_garden()\nHello, Garden Community!")


class Ex1(M00Exercise):
    ex_id, title, directory = "ex1", "Garden Name", "ex1"
    files = ["ft_garden_name.py"]
    func = "ft_garden_name"
    authorized = {"input", "print"}
    authorized_line = "Authorized: input(), print()"
    RULE = (">>> ft_garden_name()\nEnter garden name: Community Garden\n"
            "Garden: Community Garden\nStatus: Growing well!")

    def behaviour(self, ctx: Ctx) -> None:
        p = ["Enter garden name: "]
        self.scenario_checks(ctx, self.files[0], self.func, [
            _io("exemple du sujet", ["Community Garden"], p, """
                Enter garden name: Community Garden
                Garden: Community Garden
                Status: Growing well!"""),
            _io("autre nom (détection de sortie en dur)", ["Rose Corner"], p,
                """
                Enter garden name: Rose Corner
                Garden: Rose Corner
                Status: Growing well!"""),
        ], self.RULE)


class Ex2(M00Exercise):
    ex_id, title, directory = "ex2", "Garden Plot Area", "ex2"
    files = ["ft_plot_area.py"]
    func = "ft_plot_area"
    authorized = {"input", "int", "print"}
    authorized_line = "Authorized: input(), int(), print()"
    RULE = (">>> ft_plot_area()\nEnter length: 5\nEnter width: 3\n"
            "Plot area: 15")

    def behaviour(self, ctx: Ctx) -> None:
        p = ["Enter length: ", "Enter width: "]
        self.scenario_checks(ctx, self.files[0], self.func, [
            _io("exemple du sujet (5 x 3)", ["5", "3"], p, """
                Enter length: 5
                Enter width: 3
                Plot area: 15"""),
            _io("autres valeurs (7 x 12)", ["7", "12"], p, """
                Enter length: 7
                Enter width: 12
                Plot area: 84"""),
        ], self.RULE)


class Ex3(M00Exercise):
    ex_id, title, directory = "ex3", "Harvest Total", "ex3"
    files = ["ft_harvest_total.py"]
    func = "ft_harvest_total"
    authorized = {"input", "int", "print"}
    authorized_line = "Authorized: input(), int(), print()"
    RULE = (">>> ft_harvest_total()\nDay 1 harvest: 5\nDay 2 harvest: 8\n"
            "Day 3 harvest: 3\nTotal harvest: 16")

    def behaviour(self, ctx: Ctx) -> None:
        p = ["Day 1 harvest: ", "Day 2 harvest: ", "Day 3 harvest: "]
        self.scenario_checks(ctx, self.files[0], self.func, [
            _io("exemple du sujet", ["5", "8", "3"], p, """
                Day 1 harvest: 5
                Day 2 harvest: 8
                Day 3 harvest: 3
                Total harvest: 16"""),
            _io("autres valeurs", ["10", "0", "32"], p, """
                Day 1 harvest: 10
                Day 2 harvest: 0
                Day 3 harvest: 32
                Total harvest: 42"""),
        ], self.RULE)


class Ex4(M00Exercise):
    ex_id, title, directory = "ex4", "Plant Age Check", "ex4"
    files = ["ft_plant_age.py"]
    func = "ft_plant_age"
    authorized = {"input", "int", "print"}
    authorized_line = "Authorized: input(), int(), print()"
    RULE = ("Write a function named ft_plant_age that asks for a plant's "
            "age in days and tells you whether it's ready to harvest "
            "(strictly more than 60 days) or not.")

    def behaviour(self, ctx: Ctx) -> None:
        p = ["Enter plant age in days: "]
        ready, wait = "Plant is ready to harvest!", \
            "Plant needs more time to grow."
        sc = [_io("exemple du sujet (75)", ["75"], p,
                  "Enter plant age in days: 75\n" + ready),
              _io("exemple du sujet (45)", ["45"], p,
                  "Enter plant age in days: 45\n" + wait),
              _io("limite : 60 jours (pas « strictement plus »)", ["60"], p,
                  "Enter plant age in days: 60\n" + wait),
              _io("limite : 61 jours", ["61"], p,
                  "Enter plant age in days: 61\n" + ready)]
        self.scenario_checks(ctx, self.files[0], self.func, sc, self.RULE)


class Ex5(M00Exercise):
    ex_id, title, directory = "ex5", "Water Reminder", "ex5"
    files = ["ft_water_reminder.py"]
    func = "ft_water_reminder"
    authorized = {"input", "int", "print"}
    authorized_line = "Authorized: input(), int(), print()"
    RULE = ('If it has been more than 2 days, print "Water the plants!"; '
            'otherwise print "Plants are fine".')

    def behaviour(self, ctx: Ctx) -> None:
        p = ["Days since last watering: "]
        water, fine = "Water the plants!", "Plants are fine"
        sc = [_io("exemple du sujet (4)", ["4"], p,
                  "Days since last watering: 4\n" + water),
              _io("exemple du sujet (1)", ["1"], p,
                  "Days since last watering: 1\n" + fine),
              _io("limite : 2 jours (pas « plus de 2 »)", ["2"], p,
                  "Days since last watering: 2\n" + fine),
              _io("limite : 3 jours", ["3"], p,
                  "Days since last watering: 3\n" + water)]
        self.scenario_checks(ctx, self.files[0], self.func, sc, self.RULE)


class Ex6(M00Exercise):
    ex_id, title, directory = "ex6", "Count to Harvest", "ex6"
    files = ["ft_count_harvest_iterative.py",
             "ft_count_harvest_recursive.py"]
    authorized = {"input", "int", "print", "range"}
    authorized_line = ("Authorized: input(), int(), print(), range(), "
                       "defining helper functions for recursion")

    @staticmethod
    def rule(func: str) -> str:
        """Exemple du sujet correspondant à la fonction testée."""
        return (">>> %s()\nDays until harvest: 5\n"
                "Day 1\nDay 2\nDay 3\nDay 4\nDay 5\nHarvest time!" % func)

    @staticmethod
    def expected(n: int) -> str:
        return "\n".join(["Days until harvest: %d" % n]
                         + ["Day %d" % i for i in range(1, n + 1)]
                         + ["Harvest time!"])

    def check(self, ctx: Ctx) -> None:
        it_file, rec_file = self.files
        p = ["Days until harvest: "]
        # Fichier itératif : uniquement la fonction demandée.
        self.helpers_allowed = False
        ok_it = self.check_only_function(ctx, it_file,
                                         ["ft_count_harvest_iterative"])
        # Fichier récursif : fonctions auxiliaires autorisées.
        self.helpers_allowed = True
        ok_rec = self.check_only_function(ctx, rec_file,
                                          ["ft_count_harvest_recursive"])
        if ok_it:
            fn = A.functions(ctx.tree(it_file))["ft_count_harvest_iterative"]
            if not (A.contains_node(fn, A.ast.For)
                    or A.contains_node(fn, A.ast.While)):
                ctx.ko("Version itérative sans boucle",
                       "Write two functions named ft_count_harvest_iterative"
                       " and ft_count_harvest_recursive.",
                       file=ctx.rel(it_file),
                       detail="ft_count_harvest_iterative doit utiliser une "
                              "boucle (for / while).")
        if ok_rec:
            tree = ctx.tree(rec_file)
            fn = A.functions(tree)["ft_count_harvest_recursive"]
            if not A.is_recursive(fn, tree):
                ctx.ko("Version récursive sans récursion",
                       "Write two functions named ft_count_harvest_iterative"
                       " and ft_count_harvest_recursive.",
                       file=ctx.rel(rec_file),
                       detail="Aucune fonction ne s'appelle elle-même "
                              "(directement ou via une fonction "
                              "auxiliaire).")
            loops = [n for n in A.ast.walk(fn)
                     if isinstance(n, (A.ast.For, A.ast.While))]
            if loops:
                ctx.warn("Boucle dans la version récursive",
                         "For the recursive version, various approaches are"
                         " acceptable", file=ctx.rel(rec_file),
                         detail="Une boucle for/while dans la version "
                                "récursive : vérifiez que la répétition "
                                "vient bien de la récursion.")
        for file, func, ok in ((it_file, "ft_count_harvest_iterative",
                                ok_it),
                               (rec_file, "ft_count_harvest_recursive",
                                ok_rec)):
            if not ok:
                continue
            sc = [_io("%s() exemple (5)" % func, ["5"], p, self.expected(5)),
                  _io("%s() autre valeur (3)" % func, ["3"], p,
                      self.expected(3),
                      "Avec 3, la sortie doit s'arrêter à Day 3 : une "
                      "sortie identique à l'exemple est écrite en dur."),
                  _io("%s() autre valeur (12)" % func, ["12"], p,
                      self.expected(12))]
            self.scenario_checks(ctx, file, func, sc, self.rule(func))


class Ex7(M00Exercise):
    ex_id, title, directory = "ex7", "Seed Inventory", "ex7"
    files = ["ft_seed_inventory.py"]
    func = "ft_seed_inventory"
    authorized = {"print"}
    authorized_line = "Authorized: print(), string methods"
    type_hints = "required"
    SIG = ("def ft_seed_inventory(seed_type: str, quantity: int, unit: str)"
           " -> None:")

    def behaviour(self, ctx: Ctx) -> None:
        fn = A.functions(ctx.tree(self.files[0]))[self.func]
        got_sig = "def %s(%s) -> %s:" % (
            fn.name, A.ast.unparse(fn.args),
            A.ast.unparse(fn.returns) if fn.returns else "?")
        if got_sig.replace(" ", "") != self.SIG.replace(" ", ""):
            ctx.ko("Signature différente du sujet",
                   "Your function signature must look like this:\n"
                   + self.SIG, expected=self.SIG, got=got_sig,
                   file=ctx.rel(self.files[0]))
        else:
            ctx.ok("signature exacte")
        rule = ('Support these units: "packets" (packets available), '
                '"grams" (grams total), "area" (covers X square meters). '
                'For any other unit, print only "Unknown unit type" with no '
                'other information on the line.')

        def sc(label: str, args: list[Any], exp: str) -> dict[str, Any]:
            return {"label": label, "args": args, "inputs": [],
                    "expected": [exp]}

        self.scenario_checks(ctx, self.files[0], self.func, [
            sc('("tomato", 15, "packets")', ["tomato", 15, "packets"],
               "Tomato seeds: 15 packets available"),
            sc('("carrot", 8, "grams")', ["carrot", 8, "grams"],
               "Carrot seeds: 8 grams total"),
            sc('("lettuce", 12, "area")', ["lettuce", 12, "area"],
               "Lettuce seeds: covers 12 square meters"),
            sc('("basil", 3, "packets")', ["basil", 3, "packets"],
               "Basil seeds: 3 packets available"),
            sc('("pumpkin", 250, "grams")', ["pumpkin", 250, "grams"],
               "Pumpkin seeds: 250 grams total"),
            sc('("mint", 7, "area")', ["mint", 7, "area"],
               "Mint seeds: covers 7 square meters"),
            sc('("onion", 5, "boxes") (unité inconnue)',
               ["onion", 5, "boxes"], "Unknown unit type"),
        ], rule)


class Module00(Module):
    id = "00"
    title = "Growing Code"
    pdf = "python_module_00.pdf"
    signature = ["ex0/ft_hello_garden.py", "ex1/ft_garden_name.py",
                 "ex2/ft_plot_area.py", "ex3/ft_harvest_total.py",
                 "ex4/ft_plant_age.py", "ex5/ft_water_reminder.py",
                 "ex6/ft_count_harvest_iterative.py",
                 "ex6/ft_count_harvest_recursive.py",
                 "ex7/ft_seed_inventory.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4(), Ex5(), Ex6(), Ex7()]
    hints_rule = ("Type hints are optional but recommended for learning "
                  "purposes in exercises 0 to 6. They are required for "
                  "exercise 7.")
    only_requested_rule = ("You need to submit only the files requested by "
                           "each exercise for this project.")


MODULE = Module00()
