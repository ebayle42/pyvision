"""Module 09 : Cosmic Data (Discover Pydantic Models & Validation)."""
from __future__ import annotations

import json
import sys
from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines

PYDANTIC_RULE = ("You must use which Pydantic 2.x for every exercise. (It must"
                 " be installed via pip). Only other modules will be listed "
                 "in each exercise’s Allowed section")
STDLIB_RULE = ("Authorized imports: You may import JSON and CSV data from the"
               " tools directory. Standard library modules (json, csv, "
               "datetime, etc.) are allowed.")
V2_RULE = ("Important: This activity focuses on Pydantic v2 syntax. Avoid "
           "deprecated decorators like @validator - use @model_validator for "
           "custom validation instead.")
OUTPUT_RULE = "Expected Output Example"
STDLIB = set(getattr(sys, "stdlib_module_names", ())) | {
    "json", "csv", "datetime", "enum", "typing", "decimal", "uuid", "re",
    "os", "sys", "pathlib", "collections", "dataclasses", "abc"}

# Sonde générique : essaie des variantes d'un jeu de données valide.
PROBE = r'''
import json, datetime
m = load(os.path.join(EX, FILE))
try:
    from pydantic import ValidationError
except ImportError:
    report("no_pydantic", True)
    raise SystemExit
R = {"missing": [], "cases": [], "classes": {}}
for name in NAMES:
    cls = getattr(m, name, None)
    if cls is None:
        R["missing"].append(name)
    else:
        R["classes"][name] = [k.__name__ for k in cls.__mro__]


def build(spec):
    """Remplace les marqueurs {"$enum": [Classe, valeur]} et
    {"$model": [Classe, dict]} par les vrais objets."""
    if isinstance(spec, dict) and "$enum" in spec:
        cls, val = spec["$enum"]
        return getattr(m, cls)(val)
    if isinstance(spec, dict) and "$model" in spec:
        cls, data = spec["$model"]
        return getattr(m, cls)(**build(data))
    if isinstance(spec, dict):
        return {k: build(v) for k, v in spec.items()}
    if isinstance(spec, list):
        return [build(v) for v in spec]
    return spec


for label, cls_name, data, should_pass in CASES:
    cls = getattr(m, cls_name, None)
    if cls is None:
        continue
    def make():
        return cls(**build(data))
    c = capture(make)
    entry = {"label": label, "should": should_pass, "exc": c.exc,
             "exc_type": c.exc_type,
             "validation": isinstance(c.exc_obj, ValidationError)}
    if c.value is not None:
        entry["dump"] = {k: repr(v) for k, v in vars(c.value).items()}
        entry["types"] = {k: type(v).__name__
                          for k, v in vars(c.value).items()}
    R["cases"].append(entry)
report("R", R)
'''


class M09Exercise(Exercise):
    type_hints = "required"
    imports = {"pydantic"} | STDLIB
    authorized_line = PYDANTIC_RULE + "\n" + STDLIB_RULE
    file = ""
    names: list[str] = []
    example = ""

    def check(self, ctx: Ctx) -> None:
        f = ctx.rel(self.file)
        tree = ctx.tree(self.file)
        decos = {d for fn in A.all_functions(tree)
                 for d in A.decorator_names(fn)}
        bad = decos & {"validator", "root_validator"}
        if bad:
            ctx.ko("Décorateur Pydantic v1 déprécié", V2_RULE,
                   got=", ".join("@" + b for b in sorted(bad)), file=f)
        if not any(i.root == "pydantic" for i in A.imports(tree)):
            ctx.ko("Pydantic n'est pas utilisé", PYDANTIC_RULE, file=f)
        models = [n for n, c in A.classes(tree).items()
                  if "BaseModel" in A.base_names(c)]
        if not models:
            ctx.ko("Aucun modèle BaseModel", "Inherit from BaseModel to "
                   "create validated data classes.", file=f)
        self.static(ctx, tree)
        try:
            import pydantic
            ok = pydantic.VERSION.startswith("2")
        except ImportError:
            ok = False
        if not ok:
            ctx.warn("Pydantic 2 absent de l'environnement de pyvision",
                     PYDANTIC_RULE, manual="relancez ./install.sh puis "
                                           "pyvision, ou testez à la main.")
            return
        check_script(ctx, self.file, lines(self.example), OUTPUT_RULE,
                     strict=False, crash_rule="Show valid and invalid "
                     "reports with clear error messages.")
        cases = self.cases()
        code = "FILE = %r\nNAMES = %s\nCASES = json.loads(%r)\n" % (
            self.file, json.dumps(self.names), json.dumps(cases))
        res = ctx.probe("import json\n" + code + PROBE)
        if res.probe.get("no_pydantic"):
            return
        R = res.probe.get("R")
        if not R:
            return
        for name in R["missing"]:
            ctx.ko("Classe %s absente" % name, self.class_rule(name), file=f)
        for name, mro in R["classes"].items():
            want = "Enum" if name in ("ContactType", "Rank") else \
                "BaseModel"
            if want not in mro:
                ctx.ko("%s n'hérite pas de %s" % (name, want),
                       self.class_rule(name), got=" -> ".join(mro), file=f)
        for c in R["cases"]:
            if c["should"] and c["exc"]:
                ctx.ko("Donnée valide refusée : %s" % c["label"],
                       self.rule_for(c["label"]), got=c["exc"][-600:],
                       file=f)
            elif not c["should"] and not c["exc"]:
                ctx.ko("Donnée invalide acceptée : %s" % c["label"],
                       self.rule_for(c["label"]), expected="ValidationError",
                       got="objet créé : %s" % c.get("dump"), file=f)
            elif not c["should"] and not c["validation"]:
                ctx.ko("%s : %s au lieu d'une ValidationError" % (
                    c["label"], c["exc_type"]), self.rule_for(c["label"]),
                    got=c["exc"], file=f)
            self.extra(ctx, c)
        if not ctx.has_ko():
            ctx.ok("contraintes et règles de validation respectées")

    def static(self, ctx: Ctx, tree: Any) -> None:
        pass

    def cases(self) -> list[Any]:
        return []

    def class_rule(self, name: str) -> str:
        return ""

    def rule_for(self, label: str) -> str:
        return ""

    def extra(self, ctx: Ctx, case: dict[str, Any]) -> None:
        pass

    def need_model_validator(self, ctx: Ctx, tree: Any, rule: str) -> None:
        found = False
        for fn in A.all_functions(tree):
            for d in fn.decorator_list:
                if isinstance(d, A.ast.Call) and A.call_name(d) == \
                        "model_validator":
                    for kw in d.keywords:
                        if kw.arg == "mode" and isinstance(
                                kw.value, A.ast.Constant) and \
                                kw.value.value == "after":
                            found = True
        if not found:
            ctx.ko("Pas de @model_validator(mode='after')", rule,
                   file=ctx.rel(self.file))


def variants(base: dict[str, Any], cls: str,
             items: list[tuple[str, str, Any, bool]]) -> list[Any]:
    out: list[Any] = [("valide (exemple)", cls, base, True)]
    for label, field, value, ok in items:
        d = dict(base)
        if value is ...:
            d.pop(field, None)
        else:
            d[field] = value
        out.append((label, cls, d, ok))
    return out


STATION_RULE = ("Create a Pydantic model with these validated fields: "
                "station_id: String, 3-10 characters; name: String, 1-50 "
                "characters; crew_size: Integer, 1-20 people; power_level: "
                "Float, 0.0-100.0 percent; oxygen_level: Float, 0.0-100.0 "
                "percent; last_maintenance: DateTime field; is_operational: "
                "Boolean, defaults to True; notes: Optional string, max 200 "
                "characters")


class Ex0(M09Exercise):
    ex_id, title, directory = "ex0", "Space Station Data", "ex0"
    files = ["space_station.py"]
    file = files[0]
    names = ["SpaceStation"]
    example = """
        Space Station Data Validation
        ========================================
        Valid station created:
        ID: ISS001
        Name: International Space Station
        Crew: 6 people
        Power: 85.5%
        Oxygen: 92.3%
        Status: Operational

        ========================================
        Expected validation error:
        Input should be less than or equal to 20"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        if "main" not in A.functions(tree):
            ctx.ko("Fonction main() absente", "Include a main() function "
                   "that: Creates a valid space station instance; Displays "
                   "the station information clearly; Attempts to create an "
                   "invalid station (e.g., crew_size > 20); Shows the "
                   "validation error message", file=ctx.rel(self.file))
        if not A.calls_named(tree, "Field"):
            ctx.ko("Field() n'est pas utilisé", "Objective: Learn basic "
                   "Pydantic model creation with BaseModel and Field "
                   "validation.", file=ctx.rel(self.file))

    def class_rule(self, name: str) -> str:
        return STATION_RULE

    def rule_for(self, label: str) -> str:
        return STATION_RULE

    def cases(self) -> list[Any]:
        base = {"station_id": "ISS001", "name": "International Space Station",
                "crew_size": 6, "power_level": 85.5, "oxygen_level": 92.3,
                "last_maintenance": "2024-01-15T10:30:00"}
        return variants(base, "SpaceStation", [
            ("station_id 3 caractères", "station_id", "ABC", True),
            ("station_id 10 caractères", "station_id", "A" * 10, True),
            ("station_id 2 caractères", "station_id", "AB", False),
            ("station_id 11 caractères", "station_id", "A" * 11, False),
            ("name vide", "name", "", False),
            ("name 50 caractères", "name", "N" * 50, True),
            ("name 51 caractères", "name", "N" * 51, False),
            ("crew_size 1", "crew_size", 1, True),
            ("crew_size 20", "crew_size", 20, True),
            ("crew_size 0", "crew_size", 0, False),
            ("crew_size 21", "crew_size", 21, False),
            ("crew_size 'abc'", "crew_size", "abc", False),
            ("power_level 0.0", "power_level", 0.0, True),
            ("power_level 100.0", "power_level", 100.0, True),
            ("power_level -0.1", "power_level", -0.1, False),
            ("power_level 100.1", "power_level", 100.1, False),
            ("oxygen_level -1", "oxygen_level", -1.0, False),
            ("oxygen_level 100.5", "oxygen_level", 100.5, False),
            ("last_maintenance 'pas une date'", "last_maintenance",
             "not a date", False),
            ("last_maintenance absent", "last_maintenance", ..., False),
            ("notes 200 caractères", "notes", "n" * 200, True),
            ("notes 201 caractères", "notes", "n" * 201, False),
            ("is_operational=False", "is_operational", False, True),
        ])

    def extra(self, ctx: Ctx, case: dict[str, Any]) -> None:
        if case["label"] != "valide (exemple)" or "dump" not in case:
            return
        d, t = case["dump"], case["types"]
        f = ctx.rel(self.file)
        if t.get("last_maintenance") != "datetime":
            ctx.ko("last_maintenance n'est pas un datetime", STATION_RULE,
                   got="type : %s" % t.get("last_maintenance"), file=f)
        if d.get("is_operational") != "True":
            ctx.ko("is_operational ne vaut pas True par défaut",
                   STATION_RULE, got=d.get("is_operational"), file=f)
        if d.get("notes") != "None":
            ctx.ko("notes n'est pas optionnel (None par défaut)",
                   STATION_RULE, got=d.get("notes"), file=f)


ALIEN_FIELDS = ("Create a Pydantic model with these fields: contact_id: "
                "String, 5-15 characters; timestamp: DateTime of contact; "
                "location: String, 3-100 characters; contact_type: "
                "ContactType enum; signal_strength: Float, 0.0-10.0 scale; "
                "duration_minutes: Integer, 1-1440 (max 24 hours); "
                "witness_count: Integer, 1-100 people; message_received: "
                "Optional string, max 500 characters; is_verified: Boolean, "
                "defaults to False")
ALIEN_RULES = ("Implement @model_validator(mode=’after’) with these business "
               "rules: Contact ID must start with \"AC\" (Alien Contact); "
               "Physical contact reports must be verified; Telepathic "
               "contact requires at least 3 witnesses; Strong signals (> "
               "7.0) should include received messages")


def enum(cls: str, value: str) -> dict[str, Any]:
    return {"$enum": [cls, value]}


class Ex1(M09Exercise):
    ex_id, title, directory = "ex1", "Alien Contact Logs", "ex1"
    files = ["alien_contact.py"]
    file = files[0]
    names = ["ContactType", "AlienContact"]
    example = """
        Alien Contact Log Validation
        ======================================
        Valid contact report:
        ID: AC_2024_001
        Type: radio
        Location: Area 51, Nevada
        Signal: 8.5/10
        Duration: 45 minutes
        Witnesses: 5
        Message: 'Greetings from Zeta Reticuli'

        ======================================
        Expected validation error:
        Telepathic contact requires at least 3 witnesses"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        self.need_model_validator(ctx, tree, ALIEN_RULES)

    def class_rule(self, name: str) -> str:
        if name == "ContactType":
            return ("ContactType Enum: Define contact types: radio, visual, "
                    "physical, telepathic")
        return ALIEN_FIELDS

    def rule_for(self, label: str) -> str:
        return ALIEN_RULES if "règle" in label else ALIEN_FIELDS

    def cases(self) -> list[Any]:
        base = {"contact_id": "AC_2024_001", "timestamp":
                "2024-03-10T22:15:00", "location": "Area 51, Nevada",
                "contact_type": enum("ContactType", "radio"),
                "signal_strength": 8.5, "duration_minutes": 45,
                "witness_count": 5,
                "message_received": "Greetings from Zeta Reticuli"}
        out = variants(base, "AlienContact", [
            ("contact_id 4 caractères", "contact_id", "AC12", False),
            ("contact_id 16 caractères", "contact_id", "AC" + "1" * 14,
             False),
            ("location 2 caractères", "location", "AB", False),
            ("signal_strength 10.5", "signal_strength", 10.5, False),
            ("signal_strength -1", "signal_strength", -1.0, False),
            ("duration_minutes 0", "duration_minutes", 0, False),
            ("duration_minutes 1441", "duration_minutes", 1441, False),
            ("duration_minutes 1440", "duration_minutes", 1440, True),
            ("witness_count 0", "witness_count", 0, False),
            ("witness_count 101", "witness_count", 101, False),
            ("message_received 501 caractères", "message_received",
             "m" * 501, False),
            ("contact_type 'radio' (texte)", "contact_type", "radio", True),
            ("contact_type inconnu", "contact_type", "smoke", False),
            ("règle : contact_id sans 'AC'", "contact_id", "XX_2024_001",
             False),
        ])
        weak = dict(base, signal_strength=5.0, message_received=None)
        out += [
            ("règle : physical non vérifié", "AlienContact",
             dict(weak, contact_type=enum("ContactType", "physical"),
                  is_verified=False), False),
            ("règle : physical vérifié", "AlienContact",
             dict(weak, contact_type=enum("ContactType", "physical"),
                  is_verified=True), True),
            ("règle : telepathic avec 2 témoins", "AlienContact",
             dict(weak, contact_type=enum("ContactType", "telepathic"),
                  witness_count=2), False),
            ("règle : telepathic avec 3 témoins", "AlienContact",
             dict(weak, contact_type=enum("ContactType", "telepathic"),
                  witness_count=3), True),
            ("règle : signal 8.5 sans message", "AlienContact",
             dict(base, message_received=None), False),
            ("règle : signal 7.0 sans message", "AlienContact",
             dict(base, signal_strength=7.0, message_received=None), True),
            ("règle : visual sans message, signal faible", "AlienContact",
             dict(weak, contact_type=enum("ContactType", "visual")), True),
        ]
        return out

    def extra(self, ctx: Ctx, case: dict[str, Any]) -> None:
        if case["label"] == "valide (exemple)" and "dump" in case:
            if case["dump"].get("is_verified") != "False":
                ctx.ko("is_verified ne vaut pas False par défaut",
                       ALIEN_FIELDS, got=case["dump"].get("is_verified"),
                       file=ctx.rel(self.file))
            if case["types"].get("timestamp") != "datetime":
                ctx.ko("timestamp n'est pas un datetime", ALIEN_FIELDS,
                       got=case["types"].get("timestamp"),
                       file=ctx.rel(self.file))


CREW_FIELDS = ("CrewMember Model: member_id: String, 3-10 characters; name: "
               "String, 2-50 characters; rank: Rank enum; age: Integer, 18-80"
               " years; specialization: String, 3-30 characters; "
               "years_experience: Integer, 0-50 years; is_active: Boolean, "
               "defaults to True")
MISSION_FIELDS = ("SpaceMission Model: mission_id: String, 5-15 characters; "
                  "mission_name: String, 3-100 characters; destination: "
                  "String, 3-50 characters; launch_date: DateTime; "
                  "duration_days: Integer, 1-3650 days (max 10 years); crew:"
                  " List of CrewMember, 1-12 members; mission_status: String,"
                  " defaults to \"planned\"; budget_millions: Float, "
                  "1.0-10000.0 million dollars")
MISSION_RULES = ("Implement @model_validator(mode=’after’) with these safety "
                 "requirements: Mission ID must start with \"M\"; Must have "
                 "at least one Commander or Captain; Long missions (> 365 "
                 "days) need 50% experienced crew (5+ years); All crew "
                 "members must be active")


def member(name: str, rank: str, years: int, active: bool = True,
           **kw: Any) -> dict[str, Any]:
    d = {"member_id": "CM" + name[:3].upper(), "name": name,
         "rank": enum("Rank", rank), "age": 35,
         "specialization": "Engineering", "years_experience": years}
    if not active:
        d["is_active"] = False
    d.update(kw)
    return d


class Ex2(M09Exercise):
    ex_id, title, directory = "ex2", "Space Crew Management", "ex2"
    files = ["space_crew.py"]
    file = files[0]
    names = ["Rank", "CrewMember", "SpaceMission"]
    example = """
        Space Mission Crew Validation
        =========================================
        Valid mission created:
        Mission: Mars Colony Establishment
        ID: M2024_MARS
        Destination: Mars
        Duration: 900 days
        Budget: $2500.0M
        Crew size: 3
        Crew members:
        - Sarah Connor (commander) - Mission Command
        - John Smith (lieutenant) - Navigation
        - Alice Johnson (officer) - Engineering

        =========================================
        Expected validation error:
        Mission must have at least one Commander or Captain"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        self.need_model_validator(ctx, tree, MISSION_RULES)

    def class_rule(self, name: str) -> str:
        if name == "Rank":
            return ("Rank Enum: Define crew ranks: cadet, officer, "
                    "lieutenant, captain, commander")
        return CREW_FIELDS if name == "CrewMember" else MISSION_FIELDS

    def rule_for(self, label: str) -> str:
        if "règle" in label:
            return MISSION_RULES
        return CREW_FIELDS if "membre" in label else MISSION_FIELDS

    def cases(self) -> list[Any]:
        sarah = member("Sarah Connor", "commander", 20)
        john = member("John Smith", "lieutenant", 8)
        alice = member("Alice Johnson", "officer", 2)
        crew_m = [{"$model": ["CrewMember", c]}
                  for c in (sarah, john, alice)]
        base = {"mission_id": "M2024_MARS",
                "mission_name": "Mars Colony Establishment",
                "destination": "Mars", "launch_date": "2025-06-01T09:00:00",
                "duration_days": 900, "crew": crew_m,
                "budget_millions": 2500.0}
        out: list[Any] = [
            ("membre valide", "CrewMember", sarah, True),
            ("membre : member_id 2 caractères", "CrewMember",
             dict(sarah, member_id="AB"), False),
            ("membre : name 1 caractère", "CrewMember",
             dict(sarah, name="S"), False),
            ("membre : age 17", "CrewMember", dict(sarah, age=17), False),
            ("membre : age 81", "CrewMember", dict(sarah, age=81), False),
            ("membre : specialization 2 caractères", "CrewMember",
             dict(sarah, specialization="AB"), False),
            ("membre : years_experience 51", "CrewMember",
             dict(sarah, years_experience=51), False),
            ("membre : rang inconnu", "CrewMember",
             dict(sarah, rank="admiral"), False),
        ]
        out += variants(base, "SpaceMission", [
            ("mission_id 4 caractères", "mission_id", "M123", False),
            ("mission_name 2 caractères", "mission_name", "Ab", False),
            ("destination 2 caractères", "destination", "Ab", False),
            ("duration_days 3651", "duration_days", 3651, False),
            ("duration_days 0", "duration_days", 0, False),
            ("crew vide", "crew", [], False),
            ("budget 0.5", "budget_millions", 0.5, False),
            ("budget 10000.5", "budget_millions", 10000.5, False),
            ("membre invalide dans crew", "crew", [dict(sarah, age=10)],
             False),
            ("crew de 13 membres", "crew", [{"$model": ["CrewMember",
                                                        sarah]}] * 13,
             False),
            ("règle : mission_id sans 'M'", "mission_id", "X2024_MARS",
             False),
        ])
        no_lead = [{"$model": ["CrewMember", c]} for c in (john, alice)]
        out += [
            ("règle : sans commander ni captain", "SpaceMission",
             dict(base, crew=no_lead), False),
            ("règle : captain suffit", "SpaceMission",
             dict(base, crew=[{"$model": ["CrewMember", member(
                 "Kate Bishop", "captain", 9)]}]), True),
            ("règle : mission longue, 1/3 expérimentés", "SpaceMission",
             dict(base, crew=[{"$model": ["CrewMember", c]} for c in (
                 member("Sarah Connor", "commander", 6),
                 member("Bob Lee", "cadet", 1),
                 member("Tim Doe", "cadet", 0))]), False),
            ("règle : mission longue, 50% expérimentés", "SpaceMission",
             dict(base, crew=[{"$model": ["CrewMember", c]} for c in (
                 member("Sarah Connor", "commander", 6),
                 member("Bob Lee", "cadet", 1))]), True),
            ("règle : mission courte, peu d'expérience", "SpaceMission",
             dict(base, duration_days=200, crew=[{"$model": [
                 "CrewMember", c]} for c in (
                 member("Sarah Connor", "commander", 1),
                 member("Bob Lee", "cadet", 0))]), True),
            ("règle : membre inactif", "SpaceMission",
             dict(base, crew=[{"$model": ["CrewMember", c]} for c in (
                 sarah, member("Bob Lee", "officer", 9, active=False))]),
             False),
        ]
        return out

    def extra(self, ctx: Ctx, case: dict[str, Any]) -> None:
        if case["label"] == "valide (exemple)" and "dump" in case:
            if case["dump"].get("mission_status") != "'planned'":
                ctx.ko("mission_status ne vaut pas \"planned\" par défaut",
                       MISSION_FIELDS, got=case["dump"].get(
                           "mission_status"), file=ctx.rel(self.file))
        if case["label"] == "membre valide" and "dump" in case:
            if case["dump"].get("is_active") != "True":
                ctx.ko("is_active ne vaut pas True par défaut", CREW_FIELDS,
                       got=case["dump"].get("is_active"),
                       file=ctx.rel(self.file))


class Module09(Module):
    id = "09"
    title = "Cosmic Data"
    pdf = "python_module_09.pdf"
    signature = ["ex0/space_station.py", "ex1/alien_contact.py",
                 "ex2/space_crew.py"]
    exercises = [Ex0(), Ex1(), Ex2()]
    flake8_rule = "Your project must adhere to the flake8 coding standard."
    hints_rule = ("All code must include comprehensive type annotations. "
                  "Check this using mypy.")
    only_requested_rule = ("You need to return only the files requested by "
                           "the subject of this activity.")


MODULE = Module09()
