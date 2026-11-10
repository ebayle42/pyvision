"""Module 03 : Data Quest (Mastering Python Collections)."""
from __future__ import annotations

import ast
import re
from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines

TYPES = {"str", "int", "float"}
TYPES_LINE = ("The following standard types are allowed, along with all "
              "their associated methods and constructors: str, int, float.")
NO_IO = ("No file I/O operations are allowed. All data must be processed "
         "in-memory or via command-line arguments.")
CRASH = "Your functions should handle exceptions gracefully to avoid crashes."


def _find(out: str, pattern: str) -> re.Match[str] | None:
    return re.search(pattern, out, re.M)


def _literal(text: str) -> Any:
    text = text.strip()
    if text == "set()":
        return set()
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return None


class M03Exercise(Exercise):
    type_hints = "required"
    file = ""
    forbidden = {"open"}
    # Types qui ne sont introduits que dans un exercice suivant.
    later_types: dict[str, str] = {}

    def check(self, ctx: Ctx) -> None:
        tree = ctx.tree(self.file)
        if A.calls_named(tree, "open"):
            ctx.ko("Opération sur fichier", NO_IO, file=ctx.rel(self.file))
        self.later(ctx, tree)
        self.run_checks(ctx, tree)

    def later(self, ctx: Ctx, tree: Any) -> None:
        found = []
        for n in A.ast.walk(tree):
            kind = None
            if isinstance(n, (A.ast.Dict, A.ast.DictComp)):
                kind = "dict"
            elif isinstance(n, (A.ast.Set, A.ast.SetComp)):
                kind = "set"
            if kind in self.later_types:
                found.append("ligne %d : %s" % (n.lineno, kind))
        if found:
            ctx.warn("Structure de données pas encore introduite",
                     "Starting with this project, and when properly "
                     "introduced by an exercise, you will be able to use "
                     "each new Python data structure and all its associated "
                     "class methods.", got="\n".join(found),
                     file=ctx.rel(self.file))

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        pass


class Ex0(M03Exercise):
    ex_id, title, directory = "ex0", "Command Quest", "ex0"
    files = ["ft_command_quest.py"]
    file = files[0]
    authorized = {"len", "print"} | TYPES
    authorized_line = ("Authorized: import sys, sys.argv, len(), print()\n"
                       + TYPES_LINE)
    imports = {"sys"}
    later_types = {"dict": "ex4", "set": "ex3"}
    RULE = "Build a simple script that shows the data received as " \
           "command-line parameters. Mimic the example below."

    @staticmethod
    def expected(args: list[str]) -> list[str]:
        out = ["=== Command Quest ===", "Program name: ft_command_quest.py"]
        if not args:
            out.append("No arguments provided!")
        else:
            out.append("Arguments received: %d" % len(args))
            out += ["Argument %d: %s" % (i + 1, a)
                    for i, a in enumerate(args)]
        out.append("Total arguments: %d" % (len(args) + 1))
        return out

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        for args in ([], ["hello", "world", "42"], ["Data Quest"],
                     ["un", "deux", "trois", "quatre", "cinq"]):
            check_script(ctx, self.file, self.expected(args), self.RULE,
                         argv=args, crash_rule=CRASH)


class Ex1(M03Exercise):
    ex_id, title, directory = "ex1", "Score Cruncher", "ex1"
    files = ["ft_score_analytics.py"]
    file = files[0]
    authorized = {"len", "sum", "max", "min", "print"} | TYPES
    authorized_line = ("Authorized: import sys, sys.argv, len(), sum(), "
                       "max(), min(), print()\n" + TYPES_LINE)
    imports = {"sys"}
    later_types = {"dict": "ex4", "set": "ex3"}
    STYLE = ("Make the output look cool enough to impress your gaming "
             "buddies (you can mimic the example again)")
    EXAMPLE = """
        === Player Score Analytics ===
        Scores processed: [1500, 2300, 1800, 2100, 1950]
        Total players: 5
        Total score: 9650
        Average score: 1930.0
        High score: 2300
        Low score: 1500
        Score range: 800"""
    USAGE = ("No scores provided. Usage: python3 ft_score_analytics.py "
             "<score1> <score2> ...")

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        if not A.has_try(tree):
            ctx.ko("Aucun try/except", "This exercise requires you to use "
                   "lists to store scores and try/except blocks to handle "
                   "invalid input gracefully", file=ctx.rel(self.file))
        if not [n for n in A.ast.walk(tree)
                if isinstance(n, (A.ast.List, A.ast.ListComp))]:
            ctx.ko("Aucune liste créée", "Create a new list to store and "
                   "organize the scores", file=ctx.rel(self.file))
        check_script(ctx, self.file, lines(self.EXAMPLE), self.STYLE,
                     strict=False, argv="1500 2300 1800 2100 1950".split(),
                     crash_rule=CRASH)
        check_script(ctx, self.file, ["=== Player Score Analytics ===",
                                      self.USAGE], self.STYLE, strict=False,
                     argv=[], crash_rule=CRASH)
        res = check_script(ctx, self.file, [
            "=== Player Score Analytics ===", "Invalid parameter: 'ab'",
            "Invalid parameter: 'ac'", self.USAGE], self.STYLE,
            strict=False, argv=["ab", "ac"], crash_rule=CRASH)
        # Valeurs mélangées : les stats doivent ignorer les invalides.
        res = ctx.run(self.file, argv=["10", "abc", "40", "25", "x1"])
        if res.crashed or res.returncode:
            ctx.ko("Plantage avec des arguments valides et invalides "
                   "mélangés", CRASH, got=res.stdout + res.crash_text(),
                   file=ctx.rel(self.file), kind="crash")
            return
        out = res.stdout
        rule = ("If both valid and invalid inputs are provided via the "
                "command line, discard the invalid ones and proceed with the "
                "remaining valid inputs unless none remain. Calculate some "
                "basic stats (number, total, average, max, min, and range)")
        want = {"nombre": "3", "total": "75", "moyenne": "25.0",
                "max": "40", "min": "10", "écart": "30"}
        missing = [k + "=" + v for k, v in want.items()
                   if not re.search(r"(?<![\d.])%s(?![\d])" % re.escape(v),
                                    out)]
        for bad in ("abc", "x1"):
            if bad not in out:
                missing.append("message pour %r" % bad)
        if missing:
            ctx.ko("Statistiques fausses avec « 10 abc 40 25 x1 »", rule,
                   expected="scores [10, 40, 25] : " + ", ".join(
                       k + "=" + v for k, v in want.items()),
                   got=out, detail="Introuvable dans la sortie : "
                                   + ", ".join(missing),
                   file=ctx.rel(self.file))
        else:
            ctx.ok("statistiques correctes en ignorant les invalides")


COORD_RULE = ("First, write a function get_player_pos() that: Asks the user "
              "for the new player coordinates in the format x,y,z; Handles "
              "improper inputs; Retries until a valid set of coordinates is "
              "provided; Returns a tuple containing the player’s current 3D "
              "coordinates")


class Ex2(M03Exercise):
    ex_id, title, directory = "ex2", "Position Tracker", "ex2"
    files = ["ft_coordinate_system.py"]
    file = files[0]
    authorized = {"input", "round", "print"} | TYPES
    authorized_line = ("Authorized: import math, math.sqrt(), input(), "
                       "round(), print()\n" + TYPES_LINE)
    imports = {"math"}
    later_types = {"dict": "ex4", "set": "ex3"}
    PROMPT = "Enter new coordinates as floats in format 'x,y,z': "
    EXAMPLE = """
        === Game Coordinate System ===

        Get a first set of coordinates
        Enter new coordinates as floats in format 'x,y,z': hello world
        Invalid syntax
        Enter new coordinates as floats in format 'x,y,z': 1.0 , 2.5, 3.0
        Got a first tuple: (1.0, 2.5, 3.0)
        It includes: X=1.0, Y=2.5, Z=3.0
        Distance to center: 4.0311

        Get a second set of coordinates
        Enter new coordinates as floats in format 'x,y,z': 4,abc,5
        Error on parameter 'abc': could not convert string to float: 'abc'
        Enter new coordinates as floats in format 'x,y,z': 4,5,6
        Distance between the 2 sets of coordinates: 4.9244"""

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        if "get_player_pos" not in A.functions(tree):
            ctx.ko("Fonction get_player_pos() absente", COORD_RULE,
                   file=ctx.rel(self.file))
            return
        if not A.calls_named(tree, "sqrt"):
            ctx.warn("math.sqrt() non utilisé", "Just use 'import math' at "
                     "the top of your script in order to use math.sqrt().",
                     file=ctx.rel(self.file))
        res = check_script(
            ctx, self.file, lines(self.EXAMPLE), "Example: $> python3 "
            "ft_coordinate_system.py", inputs=["hello world",
                                               "1.0 , 2.5, 3.0", "4,abc,5",
                                               "4,5,6"], crash_rule=CRASH)
        if res.prompts:
            bad = [p for p in res.prompts if p != self.PROMPT]
            if bad:
                ctx.ko("Prompt différent du sujet", "Enter new coordinates "
                       "as floats in format 'x,y,z': ", expected=repr(
                           self.PROMPT), got=repr(bad[0]),
                       file=ctx.rel(self.file))
        elif not res.crashed:
            ctx.ko("input() n'est jamais appelé", COORD_RULE,
                   file=ctx.rel(self.file))
        res = ctx.run(self.file, inputs=["3,4,0", "1,2", "0,0,0"])
        if not res.crashed:
            out = res.stdout
            if not re.search(r"\(3\.0, 4\.0, 0\.0\)", out) or not re.search(
                    r"(?<![\d.])5\.0(?!\d)", out):
                ctx.ko("Résultat faux avec d'autres coordonnées", COORD_RULE,
                       expected="tuple (3.0, 4.0, 0.0), distance au centre "
                                "5.0, distance entre les points 5.0",
                       got=out, file=ctx.rel(self.file))
        ctx.expect_calls(self.file, [
            {"call": "get_player_pos", "inputs": ["7,8,9"],
             "returns": [7.0, 8.0, 9.0], "rule": COORD_RULE,
             "label": "get_player_pos() avec '7,8,9'"},
            {"call": "get_player_pos", "inputs": ["a,b,c", "1,2,3,4",
                                                  "1.5,-2,0"],
             "returns": [1.5, -2.0, 0.0], "rule": COORD_RULE,
             "label": "get_player_pos() réessaie après 'a,b,c' et "
                      "'1,2,3,4'"},
        ])
        code = """
        m = load(os.path.join(EX, %r))
        c = capture(m.get_player_pos, inputs=["7,8,9"])
        report("type", type(c.value).__name__)
        """ % self.file
        p = ctx.probe(code).probe
        if p.get("type") and p["type"] != "tuple":
            ctx.ko("get_player_pos() ne renvoie pas un tuple", COORD_RULE,
                   expected="tuple", got=p["type"], file=ctx.rel(self.file))


ACH_RULE = ("Create a function gen_player_achievements() that will use a "
            "large fixed list of achievements to randomly assign a set to a "
            "player. Choose a random number of achievements, then pick this "
            "number of achievements from the list to build and return the "
            "set.")


class Ex3(M03Exercise):
    ex_id, title, directory = "ex3", "Achievement Hunter", "ex3"
    files = ["ft_achievement_tracker.py"]
    file = files[0]
    authorized = {"len", "print", "set"} | TYPES
    authorized_line = ("Authorized: len(), print(), import random, random.*, "
                       "set(), set.union(), set.intersection(), "
                       "set.difference()\n" + TYPES_LINE)
    imports = {"random"}
    later_types = {"dict": "ex4"}

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        if "gen_player_achievements" not in A.functions(tree):
            ctx.ko("Fonction gen_player_achievements() absente", ACH_RULE,
                   file=ctx.rel(self.file))
        else:
            code = """
            m = load(os.path.join(EX, %r))
            sizes, types, items = set(), set(), set()
            for _ in range(40):
                c = capture(m.gen_player_achievements)
                if c.exc:
                    report("exc", c.exc)
                    break
                types.add(type(c.value).__name__)
                try:
                    sizes.add(len(c.value))
                    items |= set(c.value)
                except TypeError:
                    pass
            report("sizes", sorted(sizes))
            report("types", sorted(types))
            report("items", len(items))
            """ % self.file
            p = ctx.probe(code).probe
            if p.get("exc"):
                ctx.ko("gen_player_achievements() plante", ACH_RULE,
                       got=p["exc"], file=ctx.rel(self.file))
            elif p.get("types") and p["types"] != ["set"]:
                ctx.ko("gen_player_achievements() ne renvoie pas un set",
                       ACH_RULE, expected="set", got=", ".join(p["types"]),
                       file=ctx.rel(self.file))
            elif len(p.get("sizes", [])) < 2:
                ctx.ko("Le nombre de succès n'est jamais aléatoire",
                       ACH_RULE, got="tailles obtenues sur 40 appels : %s"
                       % p.get("sizes"), file=ctx.rel(self.file))
            else:
                ctx.ok("gen_player_achievements() : set de taille aléatoire")
        res = check_script(ctx, self.file, None, None, crash_rule=CRASH)
        if res.crashed or res.returncode:
            return
        self.semantic(ctx, res.stdout)

    def semantic(self, ctx: Ctx, out: str) -> None:
        players = {m.group(1): _literal(m.group(2)) for m in re.finditer(
            r"^Player (\w+): (.*)$", out, re.M)}
        rule = ("Generate achievement sets for a minimum of four different "
                "players; Track unique achievements among all the players; "
                "Find achievements shared by all players; For each player, "
                "spot the achievements no one else has; For each player, "
                "list the missing achievements to have them all")
        if len(players) < 4 or any(not isinstance(v, set)
                                   for v in players.values()):
            ctx.warn("Format inattendu : impossible de vérifier les "
                     "ensembles", rule, got=out[-1500:],
                     detail="Lignes « Player <nom>: {...} » attendues pour "
                            "au moins 4 joueurs.", file=ctx.rel(self.file))
            if len(re.findall(r"(?im)^player", out)) < 4:
                ctx.ko("Moins de 4 joueurs", rule, file=ctx.rel(self.file),
                       got=out[-800:])
            return
        sets: dict[str, set[str]] = players
        union: set[str] = set().union(*sets.values())
        common = set.intersection(*sets.values())
        checks = [("All distinct achievements", r"^All distinct "
                   r"achievements: (.*)$", union),
                  ("Common achievements", r"^Common achievements: (.*)$",
                   common)]
        for name, s in sets.items():
            others: set[str] = set().union(*[v for k, v in sets.items()
                                             if k != name])
            checks.append(("Only %s has" % name, r"^Only %s has: (.*)$"
                           % name, s - others))
            checks.append(("%s is missing" % name, r"^%s is missing: (.*)$"
                           % name, union - s))
        errors = []
        for label, rx_, want in checks:
            m = re.search(rx_, out, re.M)
            if m is None:
                errors.append("%s : ligne introuvable" % label)
                continue
            got = _literal(m.group(1))
            if got != want:
                errors.append("%s : attendu %s, obtenu %s" % (
                    label, sorted(want) or "set()", m.group(1)))
        if errors:
            missing_only = all("introuvable" in e for e in errors)
            ctx.issue(not missing_only, "Ensembles calculés incorrects"
                      if not missing_only else "Lignes de résultat "
                      "introuvables (format différent de l'exemple)", rule,
                      got="\n".join(errors), file=ctx.rel(self.file))
        else:
            ctx.ok("union / intersection / différences correctes")


INV_RULE = ("Each parameter must follow this format: <item_name>:<quantity>."
            " Discard invalid parameters (invalid syntax, redundant "
            "parameters, etc.) with an error message, and place valid ones in"
            " a dictionary.")


class Ex4(M03Exercise):
    ex_id, title, directory = "ex4", "Inventory Master", "ex4"
    files = ["ft_inventory_system.py"]
    file = files[0]
    authorized = {"len", "print", "sum", "list", "round"} | TYPES
    authorized_line = ("Authorized: import sys, sys.argv, len(), print(), "
                       "sum(), list(), round(), dict.keys(), dict.values(), "
                       "dict.update()\n" + TYPES_LINE)
    imports = {"sys"}
    EXAMPLE = """
        === Inventory System Analysis ===
        Redundant item 'sword' - discarding
        Error - invalid parameter 'hello'
        Quantity error for 'key': invalid literal for int() with base 10: 'value'
        Got inventory: {'sword': 1, 'potion': 5, 'shield': 2, 'armor': 3, 'helmet': 1}
        Item list: ['sword', 'potion', 'shield', 'armor', 'helmet']
        Total quantity of the 5 items: 12
        Item sword represents 8.3%
        Item potion represents 41.7%
        Item shield represents 16.7%
        Item armor represents 25.0%
        Item helmet represents 8.3%
        Item most abundant: potion with quantity 5
        Item least abundant: sword with quantity 1
        Updated inventory: {'sword': 1, 'potion': 5, 'shield': 2, 'armor': 3, 'helmet': 1, 'magic_item': 1}"""  # noqa: E501

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        check_script(ctx, self.file, lines(self.EXAMPLE),
                     "Example: $> python3 ft_inventory_system.py sword:1 "
                     "potion:5 shield:2 armor:3 helmet:1 sword:2 hello "
                     "key:value", argv="sword:1 potion:5 shield:2 armor:3 "
                     "helmet:1 sword:2 hello key:value".split(),
                     crash_rule=CRASH)
        argv = ["gem:4", "rope:2", "gem:9", "torch:4", "map", "bow:x",
                "arrow:10"]
        res = ctx.run(self.file, argv=argv)
        if res.crashed or res.returncode:
            ctx.ko("Plantage avec d'autres paramètres", CRASH,
                   got=res.stdout + res.crash_text(), file=ctx.rel(self.file),
                   kind="crash")
            return
        out = res.stdout
        inv = {"gem": 4, "rope": 2, "torch": 4, "arrow": 10}
        total = 20
        errors = []
        m = _find(out, r"^Got inventory: (.*)$")
        if m is None or _literal(m.group(1)) != inv:
            errors.append("inventaire attendu %s, obtenu %s" % (
                inv, m.group(1) if m else "(ligne introuvable)"))
        m = _find(out, r"^Item list: (.*)$")
        if m is None or _literal(m.group(1)) != list(inv):
            errors.append("liste attendue %s" % list(inv))
        if not _find(out, r"(?<!\d)%d(?!\d)" % total):
            errors.append("total %d introuvable" % total)
        for k, v in inv.items():
            pct = "%.1f" % round(v / total * 100, 1)
            if not _find(out, r"\b%s\b.*%s%%" % (k, re.escape(pct))):
                errors.append("pourcentage de %s (%s%%) introuvable"
                              % (k, pct))
        if not _find(out, r"most abundant: arrow\b"):
            errors.append("plus abondant : arrow")
        if not _find(out, r"least abundant: rope\b"):
            errors.append("moins abondant : rope")
        for bad in ("gem", "map", "bow"):
            if not _find(out, r"'%s'|\b%s\b.*(?:error|discard|invalid|"
                         r"Redundant)|(?:error|discard|invalid|Redundant)"
                         r".*\b%s\b" % (bad, bad, bad)):
                errors.append("pas de message d'erreur pour %r" % bad)
        m = _find(out, r"^Updated inventory: (.*)$")
        upd = _literal(m.group(1)) if m else None
        if not isinstance(upd, dict) or len(upd) != len(inv) + 1 or any(
                upd.get(k) != v for k, v in inv.items()):
            errors.append("inventaire mis à jour : les 4 objets + 1 nouveau")
        if errors:
            ctx.ko("Résultats faux avec « %s »" % " ".join(argv),
                   INV_RULE + " Report the most and least abundant items "
                   "(choosing the first from the command line in case of a "
                   "tie)", got=out, detail="\n".join(errors),
                   file=ctx.rel(self.file))
        else:
            ctx.ok("inventaire correct avec d'autres paramètres")
        res = ctx.run(self.file, argv=[])
        if res.crashed or res.returncode:
            ctx.ko("Plantage sans argument", "At the beginning of the game, "
                   "your inventory is usually empty ;)",
                   got=res.stdout + res.crash_text(), file=ctx.rel(self.file),
                   kind="crash")


STREAM_RULE = ("Create an endless generator function gen_event() that picks "
               "a random name from a list of players, and a random action "
               "from a list of actions. Each time next() is called on this "
               "generator, it returns a new event as a tuple (name, action).")
CONSUME_RULE = ("Finally, create a new generator function consume_event that "
                "takes the previously created list, randomly pick one of its "
                "elements, remove it from the list, and yields it, until the "
                "list is empty. This generator must be used directly in the "
                "for .. in .. construct.")


class Ex5(M03Exercise):
    ex_id, title, directory = "ex5", "Stream Wizard", "ex5"
    files = ["ft_data_stream.py"]
    file = files[0]
    authorized = {"next", "range", "len", "print"} | TYPES
    authorized_line = ("Authorized: next(), range(), len(), print(), import "
                       "typing, typing.Generator, import random, random.*\n"
                       + TYPES_LINE)
    imports = {"typing", "random"}

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        funcs = A.functions(tree)
        for name, rule in (("gen_event", STREAM_RULE),
                           ("consume_event", CONSUME_RULE)):
            if name not in funcs:
                ctx.ko("Fonction %s() absente" % name, rule,
                       file=ctx.rel(self.file))
            elif not A.has_yield(funcs[name]):
                ctx.ko("%s() n'est pas un générateur (pas de yield)" % name,
                       rule, file=ctx.rel(self.file))
        loops = [n for n in A.ast.walk(tree) if isinstance(n, A.ast.For)
                 and isinstance(n.iter, A.ast.Call)
                 and A.call_name(n.iter) == "consume_event"]
        if "consume_event" in funcs and not loops:
            ctx.ko("consume_event() n'est pas utilisé dans un for .. in ..",
                   CONSUME_RULE, file=ctx.rel(self.file),
                   expected="for event in consume_event(events):")
        if "gen_event" in funcs and "consume_event" in funcs:
            code = """
            import types
            m = load(os.path.join(EX, %r))
            g = capture(m.gen_event)
            report("is_gen", isinstance(g.value, types.GeneratorType))
            if isinstance(g.value, types.GeneratorType):
                def pull():
                    return [next(g.value) for _ in range(3000)]
                c = capture(pull)
                report("pull_exc", c.exc)
                if not c.exc:
                    ev = c.value
                    report("tuples", all(isinstance(e, tuple) and len(e) == 2
                                         and all(isinstance(x, str) for x in e)
                                         for e in ev))
                    report("distinct", len(set(ev)))
            data = [("a", "run"), ("b", "eat"), ("c", "sleep"), ("a", "eat")]
            orig = list(data)
            c = capture(lambda: list(m.consume_event(data)))
            report("consume_exc", c.exc)
            if not c.exc:
                report("consumed_sorted", sorted(c.value) == sorted(orig))
                report("left", len(data))
            """ % self.file
            p = ctx.probe(code).probe
            if p.get("is_gen") is False:
                ctx.ko("gen_event() ne renvoie pas un générateur",
                       STREAM_RULE, file=ctx.rel(self.file))
            elif p.get("pull_exc"):
                ctx.ko("gen_event() n'est pas infini", STREAM_RULE,
                       got="next() x3000 : " + p["pull_exc"],
                       file=ctx.rel(self.file))
            elif p.get("tuples") is False:
                ctx.ko("gen_event() ne produit pas des tuples (name, action)",
                       STREAM_RULE, file=ctx.rel(self.file))
            elif p.get("distinct", 2) < 2:
                ctx.ko("gen_event() ne produit pas d'événements aléatoires",
                       STREAM_RULE, file=ctx.rel(self.file))
            if p.get("consume_exc"):
                ctx.ko("consume_event() plante", CONSUME_RULE,
                       got=p["consume_exc"], file=ctx.rel(self.file))
            elif p.get("consumed_sorted") is False:
                ctx.ko("consume_event() ne renvoie pas tous les éléments",
                       CONSUME_RULE, file=ctx.rel(self.file))
            elif p.get("left", 0) != 0:
                ctx.ko("consume_event() ne retire pas les éléments de la "
                       "liste", CONSUME_RULE, got="%s élément(s) restent"
                       % p.get("left"), file=ctx.rel(self.file))
        res = check_script(ctx, self.file, None, None, crash_rule=CRASH)
        if res.crashed or res.returncode:
            return
        out = res.lines()
        events = [ln for ln in out if re.match(r"^Event \d+: ", ln)]
        nums = [int(re.match(r"^Event (\d+)", e).group(1))  # type: ignore
                for e in events]
        if len(events) != 1000 or nums != list(range(1000)):
            ctx.ko("Les 1000 événements ne sont pas affichés", "From the "
                   "main part of your script, loop a thousand times and "
                   "display all 1000 events you get from your gen_event().",
                   expected="Event 0: ... à Event 999: ...",
                   got="%d ligne(s) « Event N: »" % len(events),
                   file=ctx.rel(self.file))
        m = [ln for ln in out if ln.startswith("Built list of 10 events: ")]
        got_from = [ln for ln in out if ln.startswith("Got event from list")]
        if not m or len(_literal(m[0].split(": ", 1)[1]) or []) != 10:
            ctx.warn("Ligne « Built list of 10 events » introuvable ou "
                     "incorrecte", "Then create a list of ten tuples "
                     "generated by gen_event() again.", got="\n".join(m),
                     file=ctx.rel(self.file))
        if len(got_from) != 10:
            ctx.warn("10 lignes « Got event from list » attendues",
                     CONSUME_RULE, got="%d ligne(s)" % len(got_from),
                     file=ctx.rel(self.file))


ALCH_RULE = ("Create a list of player names, where some are capitalized and "
             "others are not. Build two list comprehensions: the first one "
             "creates a new list with all names capitalized, the second one "
             "creates a new list with only the capitalized names from the "
             "initial list.")


class Ex6(M03Exercise):
    ex_id, title, directory = "ex6", "Data Alchemist", "ex6"
    files = ["ft_data_alchemist.py"]
    file = files[0]
    authorized = {"print", "len", "sum", "round"} | TYPES
    authorized_line = ("Authorized: import random, random.*, print(), len(), "
                       "sum(), round()\n" + TYPES_LINE)
    imports = {"random"}

    def run_checks(self, ctx: Ctx, tree: Any) -> None:
        comps = A.comprehensions(tree)
        if comps["list"] < 2:
            ctx.ko("Moins de 2 list comprehensions", ALCH_RULE,
                   got="%d list comprehension(s)" % comps["list"],
                   file=ctx.rel(self.file))
        if comps["dict"] < 2:
            ctx.ko("Moins de 2 dict comprehensions", "Of course, a "
                   "comprehension will build this dictionary. Then a second "
                   "dict will be created, with scores higher than the "
                   "average, also using a comprehension.",
                   got="%d dict comprehension(s)" % comps["dict"],
                   file=ctx.rel(self.file))
        src = ctx.src(self.file)
        multi = []
        for n in A.ast.walk(tree):
            if isinstance(n, (A.ast.ListComp, A.ast.DictComp, A.ast.SetComp,
                              A.ast.GeneratorExp)) and \
                    n.end_lineno != n.lineno:
                one = " ".join(src.segment(n).split())
                if n.col_offset + len(one) <= 79:
                    multi.append("ligne %d : %s" % (n.lineno, one))
        if multi:
            ctx.warn("Compréhension sur plusieurs lignes", "Each "
                     "comprehension should be on a single line (unless it "
                     "exceeds the line size).", got="\n".join(multi),
                     file=ctx.rel(self.file))
        res = check_script(ctx, self.file, None, None, crash_rule=CRASH)
        if res.crashed or res.returncode:
            return
        out = res.stdout
        rx_ = {
            "init": r"^Initial list of players: (.*)$",
            "cap": r"^New list with all names capitalized: (.*)$",
            "only": r"^New list of capitalized names only: (.*)$",
            "scores": r"^Score dict: (.*)$",
            "avg": r"^Score average is (.*)$",
            "high": r"^High scores: (.*)$"}
        vals = {}
        for k, r in rx_.items():
            m = _find(out, r)
            vals[k] = _literal(m.group(1)) if m else None
        if any(v is None for v in vals.values()):
            ctx.warn("Format différent de l'exemple : vérification des "
                     "valeurs impossible", ALCH_RULE, got=out[-1500:],
                     file=ctx.rel(self.file))
            return
        init = vals["init"]
        errors = []
        if not isinstance(init, list) or not all(isinstance(x, str)
                                                 for x in init):
            errors.append("liste initiale illisible")
        else:
            if init == [x.capitalize() for x in init] or all(
                    x != x.capitalize() for x in init):
                errors.append("la liste initiale doit mélanger noms "
                              "capitalisés et non capitalisés")
            if vals["cap"] != [x.capitalize() for x in init]:
                errors.append("liste capitalisée attendue %s" % [
                    x.capitalize() for x in init])
            if vals["only"] != [x for x in init if x == x.capitalize()]:
                errors.append("noms déjà capitalisés attendus %s" % [
                    x for x in init if x == x.capitalize()])
        sc = vals["scores"]
        if not isinstance(sc, dict) or list(sc) != vals["cap"]:
            errors.append("les clés du dict de scores doivent être la liste "
                          "capitalisée")
        elif sc:
            avg = sum(sc.values()) / len(sc)
            if not isinstance(vals["avg"], (int, float)) or \
                    abs(vals["avg"] - round(avg, 2)) > 0.006:
                errors.append("moyenne attendue %s" % round(avg, 2))
            want = {k: v for k, v in sc.items() if v > avg}
            if vals["high"] != want:
                errors.append("scores au-dessus de la moyenne attendus %s"
                              % want)
        if errors:
            ctx.ko("Résultats des compréhensions incorrects", ALCH_RULE,
                   got=out, detail="\n".join(errors),
                   file=ctx.rel(self.file))
        else:
            ctx.ok("valeurs des compréhensions cohérentes")


class Module03(Module):
    id = "03"
    title = "Data Quest"
    pdf = "python_module_03.pdf"
    signature = ["ex0/ft_command_quest.py", "ex1/ft_score_analytics.py",
                 "ex2/ft_coordinate_system.py",
                 "ex3/ft_achievement_tracker.py",
                 "ex4/ft_inventory_system.py", "ex5/ft_data_stream.py",
                 "ex6/ft_data_alchemist.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4(), Ex5(), Ex6()]
    flake8_rule = "Your project must adhere to the flake8 coding standard."
    hints_rule = ("All functions and methods must include type hints; check "
                  "this using mypy.")
    only_requested_rule = ("You need to return only the files requested by "
                           "the subject of this project.")


MODULE = Module03()
