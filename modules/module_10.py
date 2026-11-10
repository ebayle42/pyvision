"""Module 10 : FuncMage (Master the Ancient Arts of Functional
Programming)."""
from __future__ import annotations

import sys
from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines, rx

OUTPUT_RULE = ("Each exercise provides terminal examples showing the "
               "suggested output format. While the core structure must be "
               "maintained, you may customize messages ... as long as the "
               "essential information is preserved.")
CALLABLE_RULE = "When using Callable as a type hint, use collections.abc"
GLOBAL_RULE = ("Forbidden: Global variables (embrace functional purity when "
               "possible)")
NO_IO = "Forbidden: File I/O operations (focus on in-memory processing)"
EXTERNAL = "Forbidden: External libraries (no pip install)"
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {
    "typing", "collections", "itertools", "functools", "operator", "time",
    "random", "abc"}


class M10Exercise(Exercise):
    type_hints = "required"
    forbidden = {"eval", "exec", "open"}
    authorized_line = ("All built-in functions are authorized, but eval() "
                       "and exec(). " + NO_IO)
    file = ""
    functions: list[str] = []
    allowed_extra: set[str] = set()     # functools / operator
    example = ""

    def check(self, ctx: Ctx) -> None:
        f = ctx.rel(self.file)
        tree = ctx.tree(self.file)
        for imp in A.imports(tree):
            mod = imp.module
            if imp.root in ("functools", "operator") and \
                    imp.root not in self.allowed_extra:
                ok = mod == "functools" and imp.names == ["wraps"] and \
                    "functools.wraps" in self.allowed_extra
                if not ok:
                    ctx.ko("Import de %s non autorisé ici" % imp.root,
                           "Essential modules for this project functools and"
                           " operator will be specified if allowed in each "
                           "exercise.", got="ligne %d" % imp.lineno, file=f)
            elif imp.root not in STDLIB and imp.level == 0:
                ctx.ko("Bibliothèque externe importée", EXTERNAL,
                       got=mod, file=f)
            if imp.root == "typing" and "Callable" in imp.names:
                ctx.ko("Callable importé depuis typing", CALLABLE_RULE,
                       expected="from collections.abc import Callable",
                       got="from typing import Callable", file=f)
        if A.has_global(tree):
            ctx.ko("Mot-clé global utilisé", GLOBAL_RULE,
                   got="lignes : %s" % A.has_global(tree), file=f)
        defined = A.functions(tree)
        for fn in self.functions:
            if fn not in defined:
                ctx.ko("Fonction %s() absente" % fn, "Function Signatures:",
                       file=f, got="fonctions : " + ", ".join(defined))
        self.static(ctx, tree)
        expected: list[Any] = lines(self.example)
        if self.example.startswith("\n\n"):
            expected.insert(0, "")      # le sujet commence par une ligne vide
        expected = [rx(r"Spell completed in \d+\.\d{3} seconds")
                    if isinstance(e, str) and e.startswith("Spell completed")
                    else e for e in expected]
        check_script(ctx, self.file, expected, OUTPUT_RULE,
                     strict=False, crash_rule="Exception handling should "
                     "protect the data streams from corruption.",
                     timeout=20)
        self.behaviour(ctx)

    def static(self, ctx: Ctx, tree: Any) -> None:
        pass

    def behaviour(self, ctx: Ctx) -> None:
        pass

    def results(self, ctx: Ctx, code: str) -> dict[str, Any]:
        """Sonde : le code remplit R[clé] = [ok, attendu, obtenu, règle]."""
        head = ("m = load(os.path.join(EX, %r))\nR = {}\n"
                "def chk(key, ok, expected, got):\n"
                "    R[key] = [bool(ok), repr(expected), repr(got)]\n"
                % self.file)
        tail = "\nreport('R', R)\n"
        res = ctx.probe(head + code + tail, timeout=30)
        return res.probe.get("R") or {}

    def report(self, ctx: Ctx, R: dict[str, Any], rules: dict[str, str]
               ) -> None:
        for key, (ok, exp, got) in R.items():
            if ok:
                ctx.ok(key)
                continue
            rule = next((r for k, r in rules.items() if key.startswith(k)),
                        None)
            ctx.ko(key, rule, expected=exp, got=got,
                   file=ctx.rel(self.file))


def uses_lambda_in(fn: Any, call: str) -> bool:
    for c in A.calls_named(fn, call):
        if any(isinstance(a, A.ast.Lambda) for a in c.args) or any(
                isinstance(k.value, A.ast.Lambda) for k in c.keywords):
            return True
    return False


# =================================================================== ex0
LAMBDA_RULE = ("For this exercise, you must use lambda expressions for all "
               "transformations. Do not use the ’def’ keyword to create named "
               "functions for simple operations")


class Ex0(M10Exercise):
    ex_id, title, directory = "ex0", "Lambda Sanctum", "ex0"
    files = ["lambda_spells.py"]
    file = files[0]
    functions = ["artifact_sorter", "power_filter", "spell_transformer",
                 "mage_stats"]
    example = """

        Testing artifact sorter...
        Fire Staff (92 power) comes before Crystal Orb (85 power)

        Testing spell transformer...
        * fireball * * heal * * shield *"""
    USES = {"artifact_sorter": ("sorted", "Use sorted() with a lambda to sort"
                                " by ’power’ level (descending)"),
            "power_filter": ("filter", "Use filter() with a lambda to find "
                             "mages with power >= min_power"),
            "spell_transformer": ("map", "Use map() with a lambda to add "
                                  "\"* \" prefix and \" *\" suffix"),
            "mage_stats": ("max", "Use lambdas with max(), min() to find")}

    def static(self, ctx: Ctx, tree: Any) -> None:
        funcs = A.functions(tree)
        for name, (call, rule) in self.USES.items():
            fn = funcs.get(name)
            if fn is None:
                continue
            if not uses_lambda_in(fn, call):
                ctx.ko("%s() n'utilise pas %s() avec une lambda" % (
                    name, call), rule, file=ctx.rel(self.file))
            nested = [n.name for n in A.ast.walk(fn)
                      if isinstance(n, A.ast.FunctionDef) and n is not fn]
            if nested:
                ctx.ko("Fonction nommée (def) dans %s()" % name, LAMBDA_RULE,
                       got=", ".join(nested), file=ctx.rel(self.file))
        fn = funcs.get("mage_stats")
        if fn is not None and not uses_lambda_in(fn, "min"):
            ctx.ko("mage_stats() n'utilise pas min() avec une lambda",
                   self.USES["mage_stats"][1], file=ctx.rel(self.file))

    def behaviour(self, ctx: Ctx) -> None:
        arts = [{"name": "Crystal Orb", "power": 85, "type": "orb"},
                {"name": "Fire Staff", "power": 92, "type": "staff"},
                {"name": "Old Ring", "power": 12, "type": "ring"},
                {"name": "Wind Cloak", "power": 60, "type": "cloak"}]
        mages = [{"name": "Ana", "power": 40, "element": "fire"},
                 {"name": "Bo", "power": 75, "element": "ice"},
                 {"name": "Cy", "power": 75, "element": "air"},
                 {"name": "Di", "power": 12, "element": "earth"}]
        sorted_arts = sorted(arts, key=lambda a: a["power"], reverse=True)
        ctx.expect_calls(self.file, [
            {"call": "artifact_sorter", "args": [arts],
             "returns": sorted_arts, "rule": self.USES["artifact_sorter"][1]
             + " ... Return the sorted list"},
            {"call": "power_filter", "args": [mages, 40],
             "returns": [m for m in mages if m["power"] >= 40],
             "rule": self.USES["power_filter"][1] + " ... Return a list of "
             "filtered mages"},
            {"call": "power_filter", "args": [mages, 100], "returns": [],
             "rule": self.USES["power_filter"][1]},
            {"call": "spell_transformer", "args": [["fireball", "heal"]],
             "returns": ["* fireball *", "* heal *"],
             "rule": self.USES["spell_transformer"][1] + " ... Return a list"
             " of transformed spell names"},
            {"call": "mage_stats", "args": [mages],
             "returns": {"max_power": 75, "min_power": 12,
                         "avg_power": 50.5},
             "rule": "Return dict: {’max_power’: int, ’min_power’: int, "
                     "’avg_power’: float} (average rounded to 2 decimals)"},
            {"call": "mage_stats", "args": [mages[:3]],
             "returns": {"max_power": 75, "min_power": 40,
                         "avg_power": 63.33},
             "rule": "Average power level (rounded to 2 decimals)"},
        ])


# =================================================================== ex1
HIGHER = {
    "spell_combiner": "spell_combiner(spell1, spell2) - Return a new function"
                      " that calls both spells with the same arguments; The "
                      "combined spell should return a tuple of both results",
    "power_amplifier": "power_amplifier(base_spell, multiplier) - Returns a "
                       "new spell where the power is multiplied before "
                       "casting.",
    "conditional_caster": "conditional_caster(condition, spell) - Returns a "
                          "new spell that only casts if a condition is True."
                          " If condition fails, return \"Spell fizzled\"",
    "spell_sequence": "spell_sequence(spells) - Return a function that casts"
                      " all spells in order; Returns a list of all spell "
                      "results"}


class Ex1(M10Exercise):
    ex_id, title, directory = "ex1", "Higher Realm", "ex1"
    files = ["higher_magic.py"]
    file = files[0]
    functions = list(HIGHER)
    example = """

        Testing spell combiner...
        Combined spell result: Fireball hits Dragon, Heals Dragon

        Testing power amplifier...
        Original: 10, Amplified: 30"""

    def behaviour(self, ctx: Ctx) -> None:
        R = self.results(ctx, '''
fire = lambda t, p: "Fireball hits %s for %d" % (t, p)
heal = lambda t, p: "Heal restores %s for %d HP" % (t, p)
def call(fn, *a):
    c = capture(fn, *a)
    return c.exc if c.exc else c.value
if hasattr(m, "spell_combiner"):
    comb = call(m.spell_combiner, fire, heal)
    got = call(comb, "Dragon", 10) if callable(comb) else comb
    chk("spell_combiner(fire, heal)('Dragon', 10)",
        got == (fire("Dragon", 10), heal("Dragon", 10)),
        (fire("Dragon", 10), heal("Dragon", 10)), got)
if hasattr(m, "power_amplifier"):
    amp = call(m.power_amplifier, fire, 3)
    got = call(amp, "Orc", 10) if callable(amp) else amp
    chk("power_amplifier(fire, 3)('Orc', 10)", got == fire("Orc", 30),
        fire("Orc", 30), got)
if hasattr(m, "conditional_caster"):
    cc = call(m.conditional_caster, lambda t, p: p > 5, fire)
    if callable(cc):
        a, b = call(cc, "Troll", 10), call(cc, "Troll", 3)
        chk("conditional_caster : condition vraie", a == fire("Troll", 10),
            fire("Troll", 10), a)
        chk("conditional_caster : condition fausse", b == "Spell fizzled",
            "Spell fizzled", b)
    else:
        chk("conditional_caster renvoie une fonction", False, "callable", cc)
if hasattr(m, "spell_sequence"):
    seq = call(m.spell_sequence, [fire, heal, fire])
    got = call(seq, "Imp", 7) if callable(seq) else seq
    want = [fire("Imp", 7), heal("Imp", 7), fire("Imp", 7)]
    chk("spell_sequence([fire, heal, fire])('Imp', 7)", got == want, want,
        got)
''')
        self.report(ctx, R, HIGHER)


# =================================================================== ex2
SCOPE = {
    "mage_counter": "mage_counter() - Return a function that counts how many"
                    " times it’s been called; Each call should return the "
                    "current count (starting from 1); Creating two separate "
                    "counters must yield independent state.",
    "spell_accumulator": "spell_accumulator(initial_power) - Each call adds "
                         "the given amount to the total power; Return the new"
                         " total power after each addition",
    "enchantment_factory": "enchantment_factory(enchantment_type) - Format: "
                           "\"enchantment_type item_name\" (e.g., \"Flaming "
                           "Sword\")",
    "memory_vault": "memory_vault() - Return a dict with ’store’ and ’recall’"
                    " functions; ’recall’ function: takes (key) and returns "
                    "stored value or \"Memory not found\"; Use closure to "
                    "maintain private memory storage"}


class Ex2(M10Exercise):
    ex_id, title, directory = "ex2", "Memory Depths", "ex2"
    files = ["scope_mysteries.py"]
    file = files[0]
    functions = list(SCOPE)
    example = """
        Testing mage counter...
        counter_a call 1: 1
        counter_a call 2: 2
        counter_b call 1: 1

        Testing spell accumulator...
        Base 100, add 20: 120
        Base 100, add 30: 150

        Testing enchantment factory...
        Flaming Sword
        Frozen Shield

        Testing memory vault...
        Store 'secret' = 42
        Recall 'secret': 42
        Recall 'unknown': Memory not found"""

    def behaviour(self, ctx: Ctx) -> None:
        R = self.results(ctx, '''
def run(fn, *a):
    c = capture(fn, *a)
    return c.exc if c.exc else c.value
if hasattr(m, "mage_counter"):
    a, b = m.mage_counter(), m.mage_counter()
    got = [run(a), run(a), run(b), run(a), run(b)]
    chk("mage_counter : deux compteurs indépendants", got == [1, 2, 1, 3, 2],
        [1, 2, 1, 3, 2], got)
if hasattr(m, "spell_accumulator"):
    a, b = m.spell_accumulator(100), m.spell_accumulator(5)
    got = [run(a, 20), run(a, 30), run(b, 1), run(a, 0)]
    chk("spell_accumulator(100) puis (5)", got == [120, 150, 6, 150],
        [120, 150, 6, 150], got)
if hasattr(m, "enchantment_factory"):
    got = [run(run(m.enchantment_factory, "Flaming"), "Sword"),
           run(run(m.enchantment_factory, "Shadow"), "Dagger")]
    chk("enchantment_factory", got == ["Flaming Sword", "Shadow Dagger"],
        ["Flaming Sword", "Shadow Dagger"], got)
if hasattr(m, "memory_vault"):
    v, w = run(m.memory_vault), run(m.memory_vault)
    ok = isinstance(v, dict) and {"store", "recall"} <= set(v)
    chk("memory_vault renvoie {'store', 'recall'}", ok, "{'store': ..., "
        "'recall': ...}", v)
    if ok:
        run(v["store"], "secret", 42)
        got = [run(v["recall"], "secret"), run(v["recall"], "unknown"),
               run(w["recall"], "secret")]
        want = [42, "Memory not found", "Memory not found"]
        chk("memory_vault : store / recall / coffres indépendants",
            got == want, want, got)
''')
        self.report(ctx, R, SCOPE)


# =================================================================== ex3
FT = {
    "spell_reducer": "spell_reducer(spells, operation) - Use functools.reduce"
                     " to combine all spell powers; Support operations: "
                     "\"add\", \"multiply\", \"max\", \"min\"; If spells is "
                     "empty, return 0; If operation is unknown, properly "
                     "handle the error",
    "partial_enchanter": "partial_enchanter(base_enchantment) - Use "
                         "functools.partial to create 3 specialized versions"
                         "; Each version pre-filling power=50 and the element",
    "memoized_fibonacci": "memoized_fibonacci(n) - Use functools.lru_cache "
                          "decorator for memoization; Function should return "
                          "the nth Fibonacci number",
    "spell_dispatcher": "spell_dispatcher() - Use decorator "
                        "functools.singledispatch to create a spell system; "
                        "Handle different types: int (damage spell), str "
                        "(enchantment), list (multi-cast); Return the "
                        "dispatcher function"}


class Ex3(M10Exercise):
    ex_id, title, directory = "ex3", "Ancient Library", "ex3"
    files = ["functools_artifacts.py"]
    file = files[0]
    functions = list(FT)
    allowed_extra = {"functools", "operator"}
    example = """

        Testing spell reducer...
        Sum: 100
        Product: 240000
        Max: 40

        Testing memoized fibonacci...
        Fib(0): 0
        Fib(1): 1
        Fib(10): 55
        Fib(15): 610

        Testing spell dispatcher...
        Damage spell: 42 damage
        Enchantment: fireball
        Multi-cast: 3 spells
        Unknown spell type"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        f = ctx.rel(self.file)
        funcs = A.functions(tree)
        if "spell_reducer" in funcs:
            if not A.calls_named(funcs["spell_reducer"], "reduce"):
                ctx.ko("spell_reducer() n'utilise pas functools.reduce",
                       FT["spell_reducer"], file=f)
            if not any(i.root == "operator" for i in A.imports(tree)):
                ctx.ko("Le module operator n'est pas utilisé",
                       "Use operator module functions (add, mul, etc.)",
                       file=f)
        if "partial_enchanter" in funcs and not A.calls_named(
                funcs["partial_enchanter"], "partial"):
            ctx.ko("partial_enchanter() n'utilise pas functools.partial",
                   FT["partial_enchanter"], file=f)
        if "memoized_fibonacci" in funcs:
            decos = A.decorator_names(funcs["memoized_fibonacci"])
            if not {"lru_cache", "cache"} & set(decos):
                ctx.ko("memoized_fibonacci() sans @lru_cache",
                       FT["memoized_fibonacci"], file=f,
                       got="décorateurs : %s" % (decos or "aucun"))
        if "singledispatch" not in A.ast.unparse(tree):
            ctx.ko("functools.singledispatch non utilisé",
                   FT["spell_dispatcher"], file=f)

    def behaviour(self, ctx: Ctx) -> None:
        R = self.results(ctx, '''
import functools
def run(fn, *a, **k):
    c = capture(fn, *a, **k)
    return c, (c.exc if c.exc else c.value)
if hasattr(m, "spell_reducer"):
    for op, want in (("add", 100), ("multiply", 240000), ("max", 40),
                     ("min", 10)):
        c, got = run(m.spell_reducer, [10, 20, 30, 40], op)
        chk("spell_reducer([10, 20, 30, 40], %r)" % op, got == want, want,
            got)
    c, got = run(m.spell_reducer, [], "add")
    chk("spell_reducer([], 'add')", got == 0, 0, got)
    c, got = run(m.spell_reducer, [3, 4], "power")
    chk("spell_reducer : opération inconnue gérée", c.exc_type not in (
        "KeyError", "TypeError", "AttributeError", "Timeout"),
        "erreur gérée (message ou exception explicite)", got)
if hasattr(m, "partial_enchanter"):
    calls = []
    def base(power, element, target):
        calls.append((power, element, target))
        return "%s %s %d" % (element, target, power)
    c, d = run(m.partial_enchanter, base)
    ok = isinstance(d, dict) and len(d) == 3 and all(
        isinstance(v, functools.partial) for v in d.values())
    chk("partial_enchanter : dict de 3 functools.partial", ok,
        "3 versions functools.partial", d)
    if ok:
        for v in d.values():
            capture(v, target="Dragon")
        ok2 = len(calls) == 3 and all(p == 50 for p, _, _ in calls) and \\
            len({e for _, e, _ in calls}) == 3
        chk("partial_enchanter : power=50 et 3 éléments pré-remplis", ok2,
            "power=50, éléments différents", calls)
if hasattr(m, "memoized_fibonacci"):
    fib = m.memoized_fibonacci
    got = [run(fib, n)[1] for n in (0, 1, 10, 15, 30)]
    chk("memoized_fibonacci(0, 1, 10, 15, 30)", got == [0, 1, 55, 610,
        832040], [0, 1, 55, 610, 832040], got)
    chk("memoized_fibonacci a cache_info() (lru_cache)",
        hasattr(fib, "cache_info"), "cache_info()", "absent")
    c, got = run(fib, 300)
    chk("memoized_fibonacci(300) rapide (cache)", not c.timeout and
        got == 222232244629420445529739893461909967206666939096499764990979600,
        "résultat immédiat", got)
if hasattr(m, "spell_dispatcher"):
    c, d = run(m.spell_dispatcher)
    ok = callable(d) and hasattr(d, "register")
    chk("spell_dispatcher() renvoie une fonction singledispatch", ok,
        "fonction avec .register", d)
    if ok:
        res = {k: run(d, v)[1] for k, v in (("int", 42), ("str", "fireball"),
                                            ("list", ["a", "b", "c"]),
                                            ("float", 3.5))}
        chk("dispatch : int, str, list et type inconnu renvoient des textes "
            "différents", all(isinstance(v, str) for v in res.values())
            and len(set(res.values())) == 4 and "42" in res["int"]
            and "fireball" in res["str"], "4 messages distincts", res)
''')
        self.report(ctx, R, FT)


# =================================================================== ex4
DECO = {
    "spell_timer": "spell_timer(func) - Print \"Casting function_name...\" "
                   "before execution; Print \"Spell completed in X.XXX "
                   "seconds\" after execution (3 decimal places); Use "
                   "functools.wraps to preserve original function metadata;"
                   " Return the original function’s result",
    "power_validator": "power_validator(min_power) - If power is valid (>= "
                       "min_power), execute the function normally; If "
                       "invalid, return \"Insufficient power for this "
                       "spell\"; Use functools.wraps properly",
    "retry_spell": "retry_spell(max_attempts) - If function raises an "
                   "exception, retry up to max_attempts times; Print \"Spell "
                   "failed, retrying... (attempt n/max_attempts)\"; If all "
                   "attempts fail, return \"Spell casting failed after "
                   "max_attempts attempts\"; If one attempt succeeds, return "
                   "its result normally",
    "MageGuild": "validate_mage_name(name) - Static method; Name is valid if "
                 "it’s at least 3 characters and contains only letters/"
                 "spaces; cast_spell(self, spell_name, power) - Should use "
                 "the power_validator decorator with min_power=10; When "
                 "power is valid, return \"Successfully cast spell_name with "
                 "<power> power\""}


class Ex4(M10Exercise):
    ex_id, title, directory = "ex4", "Master's Tower", "ex4"
    files = ["decorator_mastery.py"]
    file = files[0]
    functions = ["spell_timer", "power_validator", "retry_spell"]
    allowed_extra = {"functools.wraps"}
    example = """
        Testing spell timer...
        Casting fireball...
        Spell completed in 0.101 seconds
        Result: Fireball cast!

        Testing retrying spell...
        Spell failed, retrying... (attempt 1/3)
        Spell failed, retrying... (attempt 2/3)
        Spell casting failed after 3 attempts
        Waaaaaaagh spelled !

        Testing MageGuild...
        True
        False
        Successfully cast Lightning with 15 power
        Insufficient power for this spell"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        f = ctx.rel(self.file)
        if "wraps" not in A.ast.unparse(tree):
            ctx.ko("functools.wraps non utilisé", DECO["spell_timer"],
                   file=f)
        guild = A.classes(tree).get("MageGuild")
        if guild is None:
            ctx.ko("Classe MageGuild absente", DECO["MageGuild"], file=f)
            return
        meths = A.methods(guild)
        v = meths.get("validate_mage_name")
        if v is None or "staticmethod" not in A.decorator_names(v):
            ctx.ko("validate_mage_name n'est pas une @staticmethod",
                   DECO["MageGuild"], file=f)
        cs = meths.get("cast_spell")
        ok = False
        if cs is not None:
            for d in cs.decorator_list:
                if isinstance(d, A.ast.Call) and A.call_name(d) == \
                        "power_validator":
                    vals = [a for a in d.args] + [k.value for k in
                                                  d.keywords]
                    ok = any(isinstance(a, A.ast.Constant) and a.value == 10
                             for a in vals)
        if not ok:
            ctx.ko("cast_spell n'est pas décorée par power_validator(10)",
                   DECO["MageGuild"], file=f)

    def behaviour(self, ctx: Ctx) -> None:
        R = self.results(ctx, '''
import re, time
def run(fn, *a, **k):
    c = capture(fn, *a, **k)
    return c, (c.exc if c.exc else c.value)
if hasattr(m, "spell_timer"):
    def fireball():
        time.sleep(0.05)
        return "Fireball cast!"
    c, deco = run(m.spell_timer, fireball)
    if callable(deco):
        c, got = run(deco)
        lines = c.out.splitlines()
        chk("spell_timer : résultat d'origine renvoyé", got ==
            "Fireball cast!", "Fireball cast!", got)
        chk("spell_timer : messages Casting / Spell completed",
            len(lines) >= 2 and lines[0] == "Casting fireball..." and
            re.fullmatch(r"Spell completed in \\d+\\.\\d{3} seconds",
                         lines[-1]) is not None,
            "Casting fireball...\\nSpell completed in 0.050 seconds", c.out)
        chk("spell_timer : functools.wraps conserve le nom",
            getattr(deco, "__name__", "") == "fireball", "fireball",
            getattr(deco, "__name__", None))
if hasattr(m, "power_validator"):
    def zap(power):
        return "zap %d" % power
    c, deco = run(m.power_validator, 20)
    dz = run(deco, zap)[1] if callable(deco) else None
    if callable(dz):
        got = [run(dz, 25)[1], run(dz, 20)[1], run(dz, 5)[1]]
        want = ["zap 25", "zap 20", "Insufficient power for this spell"]
        chk("power_validator(20) sur zap(power)", got == want, want, got)
        chk("power_validator : functools.wraps conserve le nom",
            getattr(dz, "__name__", "") == "zap", "zap",
            getattr(dz, "__name__", None))
if hasattr(m, "retry_spell"):
    count = [0]
    def boom():
        count[0] += 1
        raise ValueError("boom")
    c, deco = run(m.retry_spell, 3)
    db = run(deco, boom)[1] if callable(deco) else None
    if callable(db):
        c, got = run(db)
        chk("retry_spell(3) : échec après 3 tentatives", got ==
            "Spell casting failed after 3 attempts",
            "Spell casting failed after 3 attempts", got)
        chk("retry_spell(3) : la fonction est appelée 3 fois",
            count[0] == 3, 3, count[0])
        msgs = re.findall(r"Spell failed, retrying\\.\\.\\. \\(attempt "
                          r"(\\d+)/3\\)", c.out)
        chk("retry_spell : messages « Spell failed, retrying... (attempt "
            "n/3) »", len(msgs) >= 1, "(attempt 1/3) ...", c.out)
    tries = [0]
    def flaky():
        tries[0] += 1
        if tries[0] < 2:
            raise RuntimeError("fail")
        return "ok after %d" % tries[0]
    dfl = run(deco, flaky)[1] if callable(deco) else None
    if callable(dfl):
        c, got = run(dfl)
        chk("retry_spell : réussite à la 2e tentative", got ==
            "ok after 2", "ok after 2", got)
G = getattr(m, "MageGuild", None)
if G is not None:
    v = getattr(G, "validate_mage_name", None)
    if callable(v):
        names = ["Merlin", "Al", "Gandalf the Grey", "R2D2", "Bob", "Zed!"]
        got = [run(v, n)[1] for n in names]
        want = [True, False, True, False, True, False]
        chk("MageGuild.validate_mage_name(%s)" % ", ".join(names),
            got == want, want, got)
    c, g = run(G)
    if not c.exc and hasattr(g, "cast_spell"):
        got = [run(g.cast_spell, "Lightning", 15)[1],
               run(g.cast_spell, "Ice", 10)[1],
               run(g.cast_spell, "Spark", 5)[1]]
        want = ["Successfully cast Lightning with 15 power",
                "Successfully cast Ice with 10 power",
                "Insufficient power for this spell"]
        chk("MageGuild().cast_spell (15, 10, 5)", got == want, want, got)
''')
        rules = {"spell_timer": DECO["spell_timer"],
                 "power_validator": DECO["power_validator"],
                 "retry_spell": DECO["retry_spell"],
                 "MageGuild": DECO["MageGuild"]}
        for key in list(R):
            if key.startswith("retry_spell : messages") and not R[key][0]:
                ok, exp, got = R.pop(key)
                ctx.warn(key, DECO["retry_spell"], expected=exp, got=got,
                         file=ctx.rel(self.file))
        self.report(ctx, R, rules)


class Module10(Module):
    id = "10"
    title = "FuncMage"
    pdf = "python_module_10.pdf"
    signature = ["ex0/lambda_spells.py", "ex1/higher_magic.py",
                 "ex2/scope_mysteries.py", "ex3/functools_artifacts.py",
                 "ex4/decorator_mastery.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4()]
    flake8_rule = "Your project must adhere to the flake8 coding standard."
    hints_rule = "Use type hints for all function signatures and return types."
    only_requested_rule = ("You need to return only the files requested by "
                           "the subject of this activity.")


MODULE = Module10()
