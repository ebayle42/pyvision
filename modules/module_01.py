"""Module 01 : Code Cultivation (Object-Oriented Garden Systems)."""
from __future__ import annotations

import json
import re
from typing import Any

from core.base import A, Ctx, Exercise, Module, lines

RUN_RULE = "Your programs must always run without errors"
NAMING_RULE = ("Use proper naming conventions: classes in PascalCase, "
               "functions and variables in snake_case")
CLASSES_RULE = ("Object-Oriented Programming: Starting from Exercise 1, all "
                "exercises in this module require the use of classes.")
ANY_PLANT_RULE = ("You must create a Plant class that serves as a model for "
                  "any plant, rather than handling each one individually.")

# Outils disponibles dans toutes les sondes du module 01.
PRELUDE = r'''
import copy, re

FINDINGS = []


def F(level, title, rule=None, **kw):
    FINDINGS.append(dict(level=level, title=title, rule=rule, **kw))


def call_any(fn, *tries):
    """Appelle fn avec le premier jeu d'arguments accepté."""
    c = None
    for args in tries or [()]:
        c = capture(fn, *args)
        if c.exc_type == "TypeError" and re.search(
                r"argument|positional|takes|missing", c.exc or ""):
            continue
        return c
    return c


def show_out(obj):
    m = getattr(obj, "show", None)
    if not callable(m):
        return None
    return capture(m)


def name_attr(obj, shown):
    """Attribut qui contient le nom de la plante (affiché en tête)."""
    try:
        items = list(vars(obj).items())
    except TypeError:
        return None
    first = shown.strip().splitlines()[0] if shown.strip() else ""
    for k, v in items:
        if isinstance(v, str) and v and first.startswith(v):
            return k
    for k, v in items:
        if isinstance(v, str) and v and v in shown:
            return k
    return None


def renamed(obj, new="Zinnia"):
    """Copie de obj avec un autre nom : détecte les noms écrits en dur."""
    c = show_out(obj)
    if c is None or c.exc:
        return None, None
    k = name_attr(obj, c.out)
    if k is None:
        return None, None
    old = getattr(obj, k)
    o = copy.deepcopy(obj)
    setattr(o, k, new)
    return o, old


def restored(obj):
    """Copie de obj remise dans l'état qu'il avait juste après __init__."""
    o = copy.deepcopy(obj)
    snap = initial_state(obj)
    if snap:
        o.__dict__.update(copy.deepcopy(snap))
    return o


def mention(text, word):
    return re.search(r"\b%s\b" % re.escape(word), text, re.I) is not None


def run(path):
    res, g = run_main(path, record=True)
    report("main_out", res.out)
    report("main_exc", res.exc)
    report("main_timeout", res.timeout)
    return res
'''


class M01Exercise(Exercise):
    imports: set[str] | None = set()
    type_hints = "required"
    file: str = ""
    expected_output: str = ""
    output_rule: str | None = None
    output_strict = False
    needs_class = True

    def check(self, ctx: Ctx) -> None:
        tree = ctx.tree(self.file)
        self.naming(ctx, tree)
        if self.needs_class and not A.classes(tree):
            ctx.ko("Aucune classe définie", CLASSES_RULE,
                   file=ctx.rel(self.file))
        self.static(ctx, tree)
        res = ctx.probe(PRELUDE + self.probe_code(ctx), timeout=25)
        p = res.probe
        if p.get("main_timeout"):
            ctx.ko("Le programme ne se termine pas (délai dépassé)",
                   RUN_RULE, got=str(p.get("main_out", ""))[-1500:],
                   file=ctx.rel(self.file), kind="crash")
        elif p.get("main_exc"):
            ctx.ko("Le programme plante", RUN_RULE,
                   got=str(p.get("main_out", ""))[-1500:] + "\n"
                   + str(p["main_exc"]), file=ctx.rel(self.file),
                   kind="crash")
        elif "main_out" in p and self.expected_output:
            got = str(p["main_out"]).splitlines()
            ctx.compare("python3 " + self.file, lines(self.expected_output),
                        got, self.output_rule or
                        "Example (sortie du sujet)",
                        strict=self.output_strict, file=ctx.rel(self.file),
                        detail=None if self.output_strict else
                        "Le format et les données sont libres tant que les "
                        "informations demandées apparaissent : simple "
                        "avertissement.")
        for f in p.get("findings", []) or []:
            (ctx.ko if f.pop("level") == "KO" else ctx.warn)(
                f.pop("title"), f.pop("rule", None),
                file=ctx.rel(self.file), **f)

    def naming(self, ctx: Ctx, tree: Any) -> None:
        bad = []
        for name, cls in A.classes(tree).items():
            if not re.fullmatch(r"_?[A-Z][A-Za-z0-9]*", name):
                bad.append("classe %s (ligne %d)" % (name, cls.lineno))
        for fn in A.all_functions(tree):
            if not re.fullmatch(r"_{0,2}[a-z][a-z0-9_]*_{0,2}", fn.name):
                bad.append("fonction %s (ligne %d)" % (fn.name, fn.lineno))
        if bad:
            ctx.ko("Conventions de nommage non respectées", NAMING_RULE,
                   got="\n".join(bad), file=ctx.rel(self.file))

    def static(self, ctx: Ctx, tree: Any) -> None:
        pass

    def probe_code(self, ctx: Ctx) -> str:
        return 'res = run(os.path.join(EX, %r))\n' % self.file + \
            "report('findings', FINDINGS)\n"

    # -- utilitaires statiques ---------------------------------------
    def need_class(self, ctx: Ctx, tree: Any, name: str, rule: str
                   ) -> A.ast.ClassDef | None:
        cls = A.classes(tree).get(name)
        if cls is None:
            ctx.ko("Classe %s absente" % name, rule,
                   file=ctx.rel(self.file))
        return cls

    def need_methods(self, ctx: Ctx, cls: A.ast.ClassDef,
                     names: list[str], rule: str) -> bool:
        meths = A.methods(cls)
        attrs = A.self_attr_assigns(cls)
        ok = True
        for n in names:
            if n not in meths:
                inherited = [c for c in A.base_names(cls)]
                ctx.ko("Méthode %s.%s() absente" % (cls.name, n), rule,
                       file=ctx.rel(self.file),
                       got="méthodes définies : "
                       + (", ".join(meths) or "aucune"),
                       detail=("Hérite de %s." % ", ".join(inherited)
                               if inherited else None))
                ok = False
            if n in attrs:
                ctx.ko("self.%s écrase la méthode %s()" % (n, n), rule,
                       file=ctx.rel(self.file),
                       detail="L'attribut self.%s (ligne %d) remplace la "
                              "méthode du même nom : plant.%s() devient "
                              "impossible. Ce doit être une vraie méthode."
                              % (n, attrs[n], n))
                ok = False
        return ok

    def hardcoded_growth(self, ctx: Ctx, tree: Any, rule: str) -> None:
        bad = []
        for c in A.calls_named(tree, "print"):
            bad += A.const_arith(c)
        for n in A.ast.walk(tree):
            if isinstance(n, A.ast.JoinedStr):
                bad += A.const_arith(n)
        if bad:
            ctx.ko("Valeur calculée en dur", rule, file=ctx.rel(self.file),
                   got="\n".join("ligne %d : %s" % (ln, e)
                                 for e, ln in sorted(set(bad),
                                                     key=lambda x: x[1])),
                   detail="Le résultat affiché vient d'un calcul entre "
                          "constantes, pas des données de la classe.")

    def hardcoded_strings(self, ctx: Ctx, tree: Any, classes: list[str],
                          words: list[str]) -> None:
        found = []
        for cname in classes:
            cls = A.classes(tree).get(cname)
            if cls is None:
                continue
            for m in A.methods(cls).values():
                for text, ln in A.string_constants(m):
                    if A.is_docstring(m.body[0]) and m.body[0].lineno == ln:
                        continue
                    hit = [w for w in words if re.search(
                        r"\b%s\b" % re.escape(w), text, re.I)]
                    if hit or text.lstrip().startswith(("[asking", "[make")):
                        found.append("%s.%s() ligne %d : %r" % (
                            cname, m.name, ln, text))
        if found:
            ctx.ko("Texte propre à une plante écrit en dur dans une méthode",
                   ANY_PLANT_RULE, got="\n".join(found),
                   file=ctx.rel(self.file),
                   detail="Les méthodes doivent fonctionner pour n'importe "
                          "quelle plante : les noms (Rose, Oak...) et les "
                          "lignes de narration « [asking ...] » appartiennent"
                          " au programme principal, pas aux classes.")


class Ex0(M01Exercise):
    ex_id, title, directory = "ex0", "Planting Your First Seed", "ex0"
    files = ["ft_garden_intro.py"]
    file = files[0]
    authorized = {"print"}
    authorized_line = "Authorized: print()"
    main_guard = "required"
    needs_class = False
    output_rule = ("Mimic the output display below; there will not be a "
                   "strict output check during the evaluation.")
    expected_output = """
        === Welcome to My Garden ===
        Plant: Rose
        Height: 25cm
        Age: 30 days

        === End of Program ==="""

    def static(self, ctx: Ctx, tree: Any) -> None:
        stores = {n.id for n in A.ast.walk(tree)
                  if isinstance(n, A.ast.Name)
                  and isinstance(n.ctx, A.ast.Store)}
        if len(stores) < 3:
            ctx.ko("Moins de 3 variables pour nom, taille et âge",
                   "Store the following plant information in simple "
                   "variables: name, height, and age.",
                   got="variables : " + (", ".join(sorted(stores))
                                         or "aucune"),
                   file=ctx.rel(self.file))
        used = set()
        for c in A.calls_named(tree, "print"):
            used |= {n.id for n in A.ast.walk(c)
                     if isinstance(n, A.ast.Name) and n.id in stores}
        if stores and not used:
            ctx.warn("Les variables ne sont pas utilisées dans print()",
                     "Display the plant information using print()",
                     file=ctx.rel(self.file))


class Ex1(M01Exercise):
    ex_id, title, directory = "ex1", "Garden Data Organizer", "ex1"
    files = ["ft_garden_data.py"]
    file = files[0]
    authorized = {"print"}
    authorized_line = "Authorized: print()"
    expected_output = """
        === Garden Plant Registry ===
        Rose: 25cm, 30 days old
        Sunflower: 80cm, 45 days old
        Cactus: 15cm, 120 days old"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        cls = self.need_class(ctx, tree, "Plant", ANY_PLANT_RULE)
        if cls is not None:
            self.need_methods(ctx, cls, ["show"],
                              "You will create a show() method in the class"
                              " to display the plant information.")

    def probe_code(self, ctx: Ctx) -> str:
        return 'res = run(os.path.join(EX, %r))\n' % self.file + r'''
plants = instances("Plant")
if len(plants) < 3:
    F("KO", "Moins de 3 plantes créées avec la classe Plant",
      "Create a program that manages data for at least 3 different plants",
      got="%d instance(s) de Plant" % len(plants))
for p in plants[:1]:
    o, old = renamed(p)
    if o is None:
        F("WARN", "Impossible de retrouver l'attribut du nom",
          detail="Test des noms écrits en dur non réalisé.")
        continue
    c = show_out(o)
    if c.exc:
        F("KO", "show() plante", got=c.exc)
    elif "Zinnia" not in c.out or mention(c.out, old):
        F("KO", "show() n'utilise pas les attributs de la plante",
          "All plants will be described using the same attributes",
          expected="Zinnia: ...", got=c.out,
          detail="Après avoir renommé la plante %r en 'Zinnia', show() "
                 "doit afficher le nouveau nom." % old)
report("findings", FINDINGS)
'''


GROW_RULE = ("Plants need to be able to grow() and age() on their own "
             "(i.e., these will be methods of the class)")
WEEK_RULE = ("Simulate a week of growth for a plant, then access the data in "
             "the class to get the final height and display the total week "
             "increase.")


class Ex2(M01Exercise):
    ex_id, title, directory = "ex2", "Plant Growth Simulator", "ex2"
    files = ["ft_plant_growth.py"]
    file = files[0]
    authorized = {"print", "range", "round"}
    authorized_line = "Authorized: print(), range(), round()"
    output_rule = ("There are multiple possible approaches to handle this. "
                   "You can implement it the way you want")
    expected_output = """
        === Garden Plant Growth ===
        Rose: 25.0cm, 30 days old
        === Day 1 ===
        Rose: 25.8cm, 31 days old
        === Day 2 ===
        Rose: 26.6cm, 32 days old
        === Day 3 ===
        Rose: 27.4cm, 33 days old
        === Day 4 ===
        Rose: 28.2cm, 34 days old
        === Day 5 ===
        Rose: 29.0cm, 35 days old
        === Day 6 ===
        Rose: 29.8cm, 36 days old
        === Day 7 ===
        Rose: 30.6cm, 37 days old
        Growth this week: 5.6cm"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        cls = self.need_class(ctx, tree, "Plant", "Reuse your Plant class "
                              "from Exercise 1")
        if cls is not None:
            self.need_methods(ctx, cls, ["grow", "age"], GROW_RULE)
            self.need_methods(ctx, cls, ["show"], "Reuse your Plant class "
                              "from Exercise 1")
        self.hardcoded_growth(ctx, tree, WEEK_RULE)

    def probe_code(self, ctx: Ctx) -> str:
        return 'res = run(os.path.join(EX, %r))\n' % self.file + r'''
plants = instances("Plant")
if not plants:
    F("KO", "Aucune instance de Plant créée", "Reuse your Plant class from "
      "Exercise 1")
for p in plants[:1]:
    for meth in ("grow", "age"):
        o = restored(p)
        m = getattr(o, meth, None)
        if not callable(m):
            F("KO", "plant.%s n'est pas une méthode appelable" % meth,
              "Plants need to be able to grow() and age() on their own "
              "(i.e., these will be methods of the class)",
              got="type : %s" % type(m).__name__)
            continue
        before = show_out(o)
        c = call_any(m, (), (1,), (1.0,))
        after = show_out(o)
        if c.exc:
            F("KO", "%s() plante" % meth, got=c.exc)
        elif before and after and before.out == after.out:
            F("KO", "%s() ne modifie pas la plante" % meth,
              "Consider how the plant should change over time when using "
              "grow() and age().", expected="show() différent après %s()"
              % meth, got=before.out + "(identique après %s())" % meth)
out = res.out
GROW_RX = r"(?i)(growth|increase|grew)[^\d\n-]*(-?\d+(?:\.\d+)?)"
m = None
heights = []
for line in out.splitlines():
    g = re.search(GROW_RX, line)
    if g and not line.lstrip().startswith("="):
        m = g
        continue
    h = re.search(r":\s*(-?\d+(?:\.\d+)?)\s*cm", line)
    if h:
        heights.append(float(h.group(1)))
if m and len(heights) >= 2:
    shown = float(m.group(2))
    real = heights[-1] - heights[0]
    if abs(shown - real) > 0.051 and not any(
            abs(shown - (h - heights[0])) <= 0.051 for h in heights):
        F("KO", "Croissance de la semaine incohérente avec les tailles "
          "affichées", "Simulate a week of growth for a plant, then access "
          "the data in the class to get the final height and display the "
          "total week increase.",
          expected="%.1f (taille finale - taille initiale)" % real,
          got=m.group(0))
elif not m:
    F("WARN", "Ligne de croissance totale introuvable",
      "display the total week increase", got=out[-600:])
report("findings", FINDINGS)
'''


class Ex3(M01Exercise):
    ex_id, title, directory = "ex3", "Plant Factory", "ex3"
    files = ["ft_plant_factory.py"]
    file = files[0]
    authorized = {"print", "range", "round"}
    authorized_line = "Authorized: print(), range(), round()"
    expected_output = """
        === Plant Factory Output ===
        Created: Rose: 25.0cm, 30 days old
        Created: Oak: 200.0cm, 365 days old
        Created: Cactus: 5.0cm, 90 days old
        Created: Sunflower: 80.0cm, 45 days old
        Created: Fern: 15.0cm, 120 days old"""
    CTOR = ("Plants need to be created directly with their initial "
            "information (name, starting height, starting age)")

    def static(self, ctx: Ctx, tree: Any) -> None:
        cls = self.need_class(ctx, tree, "Plant", self.CTOR)
        if cls is None:
            return
        init = A.methods(cls).get("__init__")
        if init is None or len(init.args.args) < 4:
            ctx.ko("Constructeur __init__(name, height, age) absent",
                   self.CTOR, file=ctx.rel(self.file),
                   got=("def __init__(%s)" % A.ast.unparse(init.args))
                   if init else "pas de __init__")
        self.need_methods(ctx, cls, ["show"],
                          "You should be able to use the show() method "
                          "unchanged to display the output above.")

    def probe_code(self, ctx: Ctx) -> str:
        return 'res = run(os.path.join(EX, %r))\n' % self.file + r'''
plants = instances("Plant")
if len(plants) < 5:
    F("KO", "Moins de 5 plantes créées",
      "Create at least 5 different plants with varying characteristics",
      got="%d instance(s) de Plant" % len(plants))
Plant = CLASSES.get("Plant")
if Plant is not None:
    c = capture(Plant, "Zinnia", 12.5, 3)
    if c.exc:
        F("KO", "Plant('Zinnia', 12.5, 3) impossible",
          "Plants need to be created directly with their initial "
          "information (name, starting height, starting age)", got=c.exc)
    else:
        s = show_out(c.value)
        if s is None or s.exc:
            F("KO", "show() inutilisable juste après la construction",
              "Each plant should be ready to use immediately after "
              "construction", got=s.exc if s else "pas de show()")
        elif not ("Zinnia" in s.out and "12.5" in s.out
                  and re.search(r"\b3\b", s.out)):
            F("KO", "show() n'affiche pas les valeurs données au "
              "constructeur", "Plants need to be created directly with "
              "their initial information (name, starting height, starting "
              "age)", expected="Zinnia: 12.5cm, 3 days old", got=s.out)
report("findings", FINDINGS)
'''


SEC_RULE = ("Print error messages from the class when invalid values are "
            "provided, leaving data unchanged or creating the plant with "
            "default values")
PROTECT_RULE = ("Use encapsulation: prevent your class attributes from being "
                "used directly by using the “protected” convention (not the "
                "mangling)")


class Ex4(M01Exercise):
    ex_id, title, directory = "ex4", "Garden Security System", "ex4"
    files = ["ft_garden_security.py"]
    file = files[0]
    authorized = {"print", "range", "round"}
    authorized_line = "Authorized: print(), range(), round()"
    expected_output = """
        === Garden Security System ===
        Plant created: Rose: 15.0cm, 10 days old

        Height updated: 25cm
        Age updated: 30 days

        Rose: Error, height can't be negative
        Height update rejected
        Rose: Error, age can't be negative
        Age update rejected

        Current state: Rose: 25.0cm, 30 days old"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        cls = self.need_class(ctx, tree, "Plant", "Improve your Plant class "
                              "in order to protect its data from corruption")
        if cls is None:
            return
        self.need_methods(ctx, cls, ["set_height", "set_age"],
                          "Provide controlled ways to modify plant data: "
                          "set_height(), set_age()")
        self.need_methods(ctx, cls, ["get_height", "get_age"],
                          "Provide safe ways to access plant data: "
                          "get_height(), get_age()")
        attrs = A.self_attr_assigns(cls)
        mangled = [a for a in attrs if a.startswith("__")
                   and not a.endswith("__")]
        public = [a for a in attrs if not a.startswith("_")]
        if mangled:
            ctx.ko("Attributs « mangled » (__x) au lieu de protégés (_x)",
                   PROTECT_RULE, got=", ".join("self." + a for a in mangled),
                   file=ctx.rel(self.file))
        if public:
            ctx.ko("Attributs publics dans Plant", PROTECT_RULE,
                   got=", ".join("self." + a for a in public),
                   expected=", ".join("self._" + a for a in public),
                   file=ctx.rel(self.file))
        if not mangled and not public and attrs:
            ctx.ok("attributs protégés (_x)")

    def probe_code(self, ctx: Ctx) -> str:
        return 'res = run(os.path.join(EX, %r))\n' % self.file + r'''
SEC = ("Print error messages from the class when invalid values are "
       "provided, leaving data unchanged or creating the plant with "
       "default values")
Plant = CLASSES.get("Plant")


def num(c):
    try:
        return float(c.value)
    except (TypeError, ValueError):
        return None


if Plant is not None and all(callable(getattr(Plant, m, None)) for m in
                             ("set_height", "set_age", "get_height",
                              "get_age")):
    c = capture(Plant, "Zinnia", 12.0, 4)
    if c.exc:
        F("KO", "Plant('Zinnia', 12.0, 4) impossible",
          "Plants need to be created directly with their initial "
          "information (name, starting height, starting age)", got=c.exc)
    else:
        p = c.value
        for what, getter, setter, good in (
                ("height", "get_height", "set_height", 12.0),
                ("age", "get_age", "set_age", 4)):
            r = capture(getattr(p, setter), -5)
            after = num(capture(getattr(p, getter)))
            if r.exc:
                F("KO", "%s(-5) lève une exception au lieu d'afficher une "
                  "erreur" % setter, SEC, got=r.exc)
                continue
            if not r.out.strip():
                F("KO", "%s(-5) n'affiche aucun message d'erreur" % setter,
                  SEC, expected="Zinnia: Error, %s can't be negative" % what,
                  got="(rien)")
            elif "Zinnia" not in r.out:
                F("KO", "Message d'erreur de %s() sans le nom de la plante"
                  % setter, "Rose: Error, %s can't be negative" % what,
                  expected="Zinnia: Error, %s can't be negative" % what,
                  got=r.out.rstrip(),
                  detail="Plante créée avec le nom 'Zinnia' : le message "
                         "doit utiliser le nom de la plante concernée "
                         "(pas un nom écrit en dur ni rien).")
            if after != good:
                F("KO", "%s(-5) modifie quand même la valeur" % setter, SEC,
                  expected="%s() == %s" % (getter, good),
                  got="%s() == %s" % (getter, after))
            capture(getattr(p, setter), 30)
            v = num(capture(getattr(p, getter)))
            if v != 30:
                F("KO", "%s(30) ne met pas la valeur à jour" % setter,
                  "Provide controlled ways to modify plant data",
                  expected="%s() == 30" % getter, got="%s() == %s"
                  % (getter, v))
        for label, args, getter in (
                ("hauteur", ("Zinnia", -10.0, 4), "get_height"),
                ("âge", ("Zinnia", 10.0, -4), "get_age")):
            c = capture(Plant, *args)
            if c.exc:
                F("KO", "Plant%r lève une exception" % (args,), SEC,
                  got=c.exc)
                continue
            v = num(capture(getattr(c.value, getter)))
            if v is None or v < 0:
                F("KO", "Le constructeur accepte une %s négative" % label,
                  SEC, expected="%s() >= 0 (valeur par défaut) et un "
                  "message d'erreur" % getter,
                  got="Plant%r -> %s() == %s ; sortie : %r"
                  % (args, getter, v, c.out))
            elif not c.out.strip():
                F("KO", "Le constructeur n'affiche pas d'erreur pour une %s "
                  "négative" % label, SEC, got="Plant%r : aucun message"
                  % (args,))
report("findings", FINDINGS)
'''


TYPES_RULE = ("When creating specialized plants, call the parent methods "
              "from inside your new class using super(). It can be applied "
              "to any method, including __init__()")
SHOW_RULE = ("A call to show() on a specialized class needs to print the "
             "standard Plant output and the extra characteristics of your "
             "specialized plant. Your method override can re-use the "
             "already existing code in the parent.")
PDF_NAMES = ["rose", "oak", "tomato", "sunflower", "cactus", "fern"]


class Ex5(M01Exercise):
    ex_id, title, directory = "ex5", "Specialized Plant Types", "ex5"
    files = ["ft_plant_types.py"]
    file = files[0]
    authorized = {"super", "print", "range", "round"}
    authorized_line = "Authorized: super(), print(), range(), round()"
    SPECS = {"Flower": (["bloom"], ["color"]),
             "Tree": (["produce_shade"], ["trunk_diameter"]),
             "Vegetable": ([], ["harvest_season", "nutritional_value"])}
    expected_output = """
        === Garden Plant Types ===
        === Flower
        Rose: 15.0cm, 10 days old
         Color: red
         Rose has not bloomed yet
        [asking the rose to bloom]
        Rose: 15.0cm, 10 days old
         Color: red
         Rose is blooming beautifully!

        === Tree
        Oak: 200.0cm, 365 days old
         Trunk diameter: 5.0cm
        [asking the oak to produce shade]
        Tree Oak now produces a shade of 200.0cm long and 5.0cm wide.

        === Vegetable
        Tomato: 5.0cm, 10 days old
         Harvest season: April
         Nutritional value: 0
        [make tomato grow and age for 20 days]
        Tomato: 47.0cm, 30 days old
         Harvest season: April
         Nutritional value: 20"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        if self.need_class(ctx, tree, "Plant", "Start with your Plant class "
                           "from the previous exercise") is None:
            return
        self.specialized(ctx, tree, self.SPECS)
        self.hardcoded_strings(ctx, tree, ["Plant"] + list(self.SPECS),
                               PDF_NAMES)

    def specialized(self, ctx: Ctx, tree: Any,
                    specs: dict[str, tuple[list[str], list[str]]]) -> None:
        for name, (meths, attrs) in specs.items():
            cls = self.need_class(ctx, tree, name, "Create specialized "
                                  "types: Flower, Tree, and Vegetable")
            if cls is None:
                continue
            if "Plant" not in A.base_names(cls):
                ctx.ko("%s n'hérite pas de Plant" % name, "Each specialized"
                       " type should inherit the basic plant features",
                       got="class %s(%s)" % (name, ", ".join(
                           A.base_names(cls))), file=ctx.rel(self.file))
            init = A.methods(cls).get("__init__")
            if init is not None and not A.calls_parent_method(
                    init, "__init__", ["Plant"]):
                ctx.ko("%s.__init__ n'appelle pas super().__init__()" % name,
                       TYPES_RULE, file=ctx.rel(self.file))
            elif init is not None and not A.uses_super(init, "__init__"):
                ctx.ko("%s.__init__ n'utilise pas super()" % name,
                       TYPES_RULE, got="Plant.__init__(self, ...)",
                       expected="super().__init__(...)",
                       file=ctx.rel(self.file))
            if "show" not in A.methods(cls):
                other = [m for m in A.methods(cls)
                         if m not in meths and not m.startswith("__")]
                ctx.ko("%s ne redéfinit pas show()" % name, SHOW_RULE,
                       file=ctx.rel(self.file),
                       got="méthodes de %s : %s" % (name, ", ".join(
                           A.methods(cls)) or "aucune"),
                       detail=("Une méthode séparée (%s) ne remplace pas la "
                               "redéfinition de show()." % ", ".join(other))
                       if other else None)
            self.need_methods(ctx, cls, meths, "Flower needs: a color "
                              "attribute and ability to bloom(); Tree needs:"
                              " a trunk_diameter attribute and the ability "
                              "to produce_shade()")
            have = {a.lstrip("_") for a in A.self_attr_assigns(cls)}
            missing = [a for a in attrs if a not in have]
            if missing:
                ctx.warn("Attribut(s) %s absent(s) de %s" % (
                    ", ".join(missing), name),
                    "Flower needs: a color attribute ... Tree needs: a "
                    "trunk_diameter attribute ... Vegetable needs: a "
                    "harvest_season and a nutritional_value attributes",
                    got="attributs : " + ", ".join(sorted(have)),
                    file=ctx.rel(self.file))

    def probe_code(self, ctx: Ctx) -> str:
        return 'res = run(os.path.join(EX, %r))\n' % self.file + \
            "REQUIRED = ['Flower', 'Tree', 'Vegetable']\n" + \
            TYPES_PROBE + "report('findings', FINDINGS)\n"


TYPES_PROBE = r'''
SHOW_RULE = ("A call to show() on a specialized class needs to print the "
             "standard Plant output and the extra characteristics of your "
             "specialized plant.")
ANY = ("You must create a Plant class that serves as a model for any plant, "
       "rather than handling each one individually.")
Plant = CLASSES.get("Plant")
for cname in REQUIRED:
    if not instances(cname) and cname in CLASSES:
        F("KO", "Aucune instance de %s créée" % cname,
          "Create at least one instance of each plant type")


def check_methods(obj, cname, meths):
    o, old = renamed(restored(obj))
    if o is None:
        F("WARN", "%s : attribut du nom introuvable" % cname,
          detail="Test des noms écrits en dur non réalisé.")
        return
    for meth in meths:
        m = getattr(o, meth, None)
        if not callable(m):
            continue
        c = call_any(m, (), (1,))
        txt = c.out + (str(c.value) if isinstance(c.value, str) else "")
        if c.exc:
            F("KO", "%s.%s() plante" % (cname, meth), got=c.exc)
        elif mention(txt, old):
            F("KO", "%s.%s() affiche un nom écrit en dur" % (cname, meth),
              ANY, expected="texte avec 'Zinnia'", got=txt.rstrip(),
              detail="La plante %r a été renommée 'Zinnia' : le texte ne "
                     "doit plus contenir %r." % (old, old))


for obj in instances("Flower")[:1]:
    o = restored(obj)
    s0 = show_out(o)
    if s0 is not None and not s0.exc and Plant is not None:
        base = capture(Plant.show, o)
        if not base.exc and base.out.strip() and \
                base.out.strip().splitlines()[0] not in s0.out:
            F("KO", "Flower.show() n'affiche pas la sortie standard de "
              "Plant", SHOW_RULE, expected=base.out, got=s0.out)
        snap = initial_state(obj)
        extras = [str(v) for k, v in snap.items()
                  if "color" in k.lower() or "colour" in k.lower()]
        if extras and not any(e in s0.out for e in extras):
            F("KO", "Flower.show() n'affiche pas la couleur", SHOW_RULE,
              expected="... %s ..." % extras[0], got=s0.out)
        b = getattr(o, "bloom", None)
        if callable(b):
            capture(b)
            s1 = show_out(o)
            if s1 is not None and s1.out == s0.out:
                F("WARN", "show() identique avant et après bloom()",
                  "Flower needs: a color attribute and ability to bloom()",
                  got=s0.out)
    check_methods(obj, "Flower", ["show", "bloom"])
for obj in instances("Tree")[:1]:
    check_methods(obj, "Tree", ["show", "produce_shade"])
for obj in instances("Vegetable")[:1]:
    check_methods(obj, "Vegetable", ["show"])
    snap = initial_state(obj)
    keys = [k for k in snap if "nutri" in k.lower()]
    if keys:
        k = keys[0]
        if snap[k] != 0:
            F("KO", "La valeur nutritionnelle ne part pas de 0",
              "make the nutritional value start from 0, then increase when "
              "the vegetable's age() and grow() methods are called.",
              expected="0", got=repr(snap[k]))
        o = restored(obj)
        before = getattr(o, k, None)
        for meth in ("grow", "age"):
            m = getattr(o, meth, None)
            if callable(m):
                call_any(m, (), (1,), (1.0,))
        after = getattr(o, k, None)
        try:
            increased = after > before
        except TypeError:
            increased = False
        if not increased:
            F("KO", "grow() et age() n'augmentent pas la valeur "
              "nutritionnelle", "make the nutritional value start from 0, "
              "then increase when the vegetable's age() and grow() methods "
              "are called.", expected="%s > %r" % (k, before),
              got="%s == %r après grow() et age()" % (k, after))
'''


class Ex6(Ex5):
    ex_id, title, directory = "ex6", "Garden Analytics", "ex6"
    files = ["ft_garden_analytics.py"]
    file = files[0]
    authorized = {"super", "print", "range", "round", "staticmethod",
                  "classmethod"}
    authorized_line = ("Authorized: super(), print(), range(), round(), "
                       "staticmethod(), classmethod()")
    expected_output = """
        === Garden statistics ===
        === Check year-old
        Is 30 days more than a year? -> False
        Is 400 days more than a year? -> True

        === Flower
        Rose: 15.0cm, 10 days old
         Color: red
         Rose has not bloomed yet
        [statistics for Rose]
        Stats: 0 grow, 0 age, 1 show
        [asking the rose to grow and bloom]
        Rose: 23.0cm, 10 days old
         Color: red
         Rose is blooming beautifully!
        [statistics for Rose]
        Stats: 1 grow, 0 age, 2 show

        === Tree
        Oak: 200.0cm, 365 days old
         Trunk diameter: 5.0cm
        [statistics for Oak]
        Stats: 0 grow, 0 age, 1 show
         0 shade
        [asking the oak to produce shade]
        Tree Oak now produces a shade of 200.0cm long and 5.0cm wide.
        [statistics for Oak]
        Stats: 0 grow, 0 age, 1 show
         1 shade

        === Seed
        Sunflower: 80.0cm, 45 days old
         Color: yellow
         Sunflower has not bloomed yet
         Seeds: 0
        [make sunflower grow, age and bloom]
        Sunflower: 110.0cm, 65 days old
         Color: yellow
         Sunflower is blooming beautifully!
         Seeds: 42
        [statistics for Sunflower]
        Stats: 1 grow, 1 age, 2 show

        === Anonymous
        Unknown plant: 0.0cm, 0 days old
        [statistics for Unknown plant]
        Stats: 0 grow, 0 age, 1 show"""
    SPECS = {"Flower": (["bloom"], ["color"]),
             "Tree": (["produce_shade"], ["trunk_diameter"])}
    STATS_RULE = ("Each Plant has an internal system, implemented as a nested"
                  " class, that holds statistical data: number of grow() "
                  "calls, number of age() calls, number of show() calls. "
                  "Encapsulation is required, as well as a display "
                  "function.")

    def static(self, ctx: Ctx, tree: Any) -> None:
        super().static(ctx, tree)
        plant = A.classes(tree).get("Plant")
        if plant is None:
            return
        decorated = {n: A.decorator_names(m) for n, m in
                     A.methods(plant).items()}
        assigned = {t.id: A.ast.unparse(n.value) for n in plant.body
                    if isinstance(n, A.ast.Assign)
                    for t in n.targets if isinstance(t, A.ast.Name)}
        static = [n for n, d in decorated.items() if "staticmethod" in d] + \
            [n for n, v in assigned.items() if v.startswith("staticmethod(")]
        clsm = [n for n, d in decorated.items() if "classmethod" in d] + \
            [n for n, v in assigned.items() if v.startswith("classmethod(")]
        if not static:
            ctx.ko("Aucune méthode statique dans Plant", "Create a static "
                   "method for the Plant class that checks if a specific age"
                   " given as a parameter is older than a year.",
                   file=ctx.rel(self.file))
        if not clsm:
            ctx.ko("Aucune méthode de classe dans Plant", "Create a class "
                   "method that allows you to create an “anonymous” plant "
                   "directly when you do not yet have all the information.",
                   file=ctx.rel(self.file))
        seed = self.need_class(ctx, tree, "Seed", "Create a Seed class that "
                               "inherits from Flower")
        if seed is not None:
            if "Flower" not in A.base_names(seed):
                ctx.ko("Seed n'hérite pas de Flower", "Create a Seed class "
                       "that inherits from Flower", file=ctx.rel(self.file),
                       got="class Seed(%s)" % ", ".join(
                           A.base_names(seed)))
            if "show" not in A.methods(seed):
                ctx.ko("Seed ne redéfinit pas show()", "The show() method "
                       "must be improved accordingly.",
                       file=ctx.rel(self.file))
        nested = [n for n in plant.body if isinstance(n, A.ast.ClassDef)]
        if not nested:
            ctx.ko("Pas de classe imbriquée dans Plant pour les "
                   "statistiques", self.STATS_RULE, file=ctx.rel(self.file))
        for n in nested:
            pub = [a for a in A.self_attr_assigns(n) if not
                   a.startswith("_")]
            if pub:
                ctx.ko("Attributs publics dans %s.%s" % (plant.name, n.name),
                       self.STATS_RULE, got=", ".join("self." + a
                                                      for a in pub),
                       file=ctx.rel(self.file))
            if not [m for m in A.methods(n) if not m.startswith("__")]:
                ctx.ko("Pas de fonction d'affichage dans %s.%s"
                       % (plant.name, n.name), self.STATS_RULE,
                       file=ctx.rel(self.file))
        funcs = [f for f in A.functions(tree) if f != "main"]
        if not funcs:
            ctx.ko("Pas de fonction (hors classe) qui affiche les "
                   "statistiques", "Finally, create a unique function, not "
                   "part of any class, that displays statistics for any "
                   "kind of plant.", file=ctx.rel(self.file))

    def probe_code(self, ctx: Ctx) -> str:
        funcs = json.dumps([f for f in A.functions(ctx.tree(self.file))
                            if f != "main"])
        return 'res = run(os.path.join(EX, %r))\nFUNCS = %s\n' % (
            self.file, funcs) + "REQUIRED = ['Flower', 'Tree', 'Seed']\n" \
            + TYPES_PROBE + r'''
Plant = CLASSES.get("Plant")
if Plant is not None:
    for k, v in list(vars(Plant).items()):
        if isinstance(v, staticmethod):
            r30, r400 = capture(v.__func__, 30), capture(v.__func__, 400)
            if r30.exc or r400.exc:
                F("KO", "Méthode statique %s() plante" % k,
                  got=r30.exc or r400.exc)
            elif r30.value is not False or r400.value is not True:
                F("KO", "Méthode statique %s() : résultat faux" % k,
                  "checks if a specific age given as a parameter is older "
                  "than a year.", expected="%s(30) -> False, %s(400) -> "
                  "True" % (k, k), got="%s(30) -> %r, %s(400) -> %r" % (
                      k, r30.value, k, r400.value))
        if isinstance(v, classmethod):
            c = capture(getattr(Plant, k))
            if c.exc:
                F("KO", "Méthode de classe %s() sans argument impossible"
                  % k, "create an “anonymous” plant directly when you do "
                  "not yet have all the information.", got=c.exc)
            elif not isinstance(c.value, Plant):
                F("KO", "Méthode de classe %s() ne renvoie pas une plante"
                  % k, "create an “anonymous” plant", got=repr(c.value))


def stats_of(o):
    for k, v in vars(o).items():
        if type(v).__qualname__.startswith("Plant."):
            try:
                return k, dict(vars(v))
            except TypeError:
                return k, {}
    return None, None


for cname, meths in (("Flower", ("grow", "age", "show")),
                     ("Tree", ("produce_shade",))):
    for obj in instances(cname)[:1]:
        o = restored(obj)
        key, _ = stats_of(o)
        if key is None:
            F("KO", "%s : aucun objet de statistiques (classe imbriquée) "
              "trouvé dans l'instance" % cname, "Each Plant has an internal "
              "system, implemented as a nested class, that holds "
              "statistical data")
            continue
        def state(o):
            d = {("self", k): repr(v) for k, v in vars(o).items()
                 if k != key}
            d.update({("stats", k): repr(v) for k, v in
                      vars(getattr(o, key)).items()})
            return d

        for meth in meths:
            m = getattr(o, meth, None)
            if not callable(m):
                continue
            before = state(o)
            call_any(m, (), (1,), (1.0,))
            after = state(o)
            if before == after:
                rule = ("Trees need an extra piece of statistical data: "
                        "number of produce_shade() calls." if meth ==
                        "produce_shade" else "number of grow() calls, "
                        "number of age() calls, number of show() calls.")
                F("KO", "%s.%s() ne met pas à jour les statistiques"
                  % (cname, meth), rule, got=repr(vars(getattr(o, key))))
report("findings", FINDINGS)
'''


class Module01(Module):
    id = "01"
    title = "Code Cultivation"
    pdf = "python_module_01.pdf"
    signature = ["ex0/ft_garden_intro.py", "ex1/ft_garden_data.py",
                 "ex2/ft_plant_growth.py", "ex3/ft_plant_factory.py",
                 "ex4/ft_garden_security.py", "ex5/ft_plant_types.py",
                 "ex6/ft_garden_analytics.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4(), Ex5(), Ex6()]
    flake8_rule = "Your code must respect the flake8 linter standards"
    hints_rule = ("All functions and methods must include type hints: use "
                  "mypy to check your code")
    only_requested_rule = ("You only need to submit the files requested by "
                           "the subject of this project.")


MODULE = Module01()
