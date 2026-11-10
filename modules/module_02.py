"""Module 02 : Garden Guardian (Data Engineering for Smart Agriculture)."""
from __future__ import annotations

from typing import Any

from core.base import A, Ctx, Exercise, Module, check_script, lines

CRASH_RULE = "Your programs must never crash"
TRY_RULE = ("Exception Handling: All exercises in this module require the "
            "use of try/except blocks for error handling.")


class M02Exercise(Exercise):
    imports: set[str] | None = set()
    tolerated = {"super"}
    type_hints = "required"
    file = ""
    functions: list[str] = []
    classes: list[str] = []
    expected_output = ""
    output_rule = ""

    def check(self, ctx: Ctx) -> None:
        tree = ctx.tree(self.file)
        defined_f = A.functions(tree)
        defined_c = A.classes(tree)
        for f in self.functions:
            if f not in defined_f:
                ctx.ko("Fonction %s() absente" % f, self.output_rule or None,
                       file=ctx.rel(self.file),
                       got="fonctions : " + (", ".join(defined_f) or
                                             "aucune"))
        for c in self.classes:
            if c not in defined_c:
                ctx.ko("Classe %s absente" % c, file=ctx.rel(self.file),
                       got="classes : " + (", ".join(defined_c) or "aucune"))
        if not A.has_try(tree):
            ctx.ko("Aucun bloc try/except", TRY_RULE,
                   file=ctx.rel(self.file))
        self.static(ctx, tree)
        check_script(ctx, self.file, lines(self.expected_output),
                     self.output_rule, crash_rule=CRASH_RULE)
        cases = self.cases()
        if cases:
            ctx.expect_calls(self.file, cases)

    def static(self, ctx: Ctx, tree: Any) -> None:
        pass

    def cases(self) -> list[dict[str, Any]]:
        return []


EX0_RULE = ("Write a simple function input_temperature(temp_str) that: "
            "Takes an input string as a parameter, Converts it to a number, "
            "Returns the temperature as an integer")


class Ex0(M02Exercise):
    ex_id, title, directory = "ex0", "Agricultural Data Validation", "ex0"
    files = ["ft_first_exception.py"]
    file = files[0]
    authorized = {"int", "print"}
    authorized_line = "Authorized: int(), print()"
    functions = ["input_temperature", "test_temperature"]
    output_rule = "Example: $> python3 ft_first_exception.py"
    expected_output = """
        === Garden Temperature ===

        Input data is '25'
        Temperature is now 25°C

        Input data is 'abc'
        Caught input_temperature error: invalid literal for int() with base 10: 'abc'

        All tests completed - program didn't crash!"""  # noqa: E501

    def cases(self) -> list[dict[str, Any]]:
        return [
            {"call": "input_temperature", "args": ["25"], "returns": 25,
             "rule": EX0_RULE},
            {"call": "input_temperature", "args": ["17"], "returns": 17,
             "rule": EX0_RULE},
            {"call": "input_temperature", "args": ["abc"], "raises": "*",
             "rule": "Handle the case when input_temperature() fails; print "
                     "an error message",
             "label": "input_temperature('abc') doit lever une exception"},
        ]


EX1_RULE = ("Check if the temperature is reasonable for plants (0 to 40 "
            "degrees Celsius, limits included). Return the temperature if "
            "it's valid; otherwise, raise an exception.")


class Ex1(M02Exercise):
    ex_id, title, directory = "ex1", "Data Validation Pipeline", "ex1"
    files = ["ft_raise_exception.py"]
    file = files[0]
    authorized = {"int", "print"}
    authorized_line = "Authorized: int(), print()"
    functions = ["input_temperature", "test_temperature"]
    output_rule = "Example: $> python3 ft_raise_exception.py"
    expected_output = """
        === Garden Temperature Checker ===

        Input data is '25'
        Temperature is now 25°C

        Input data is 'abc'
        Caught input_temperature error: invalid literal for int() with base 10: 'abc'

        Input data is '100'
        Caught input_temperature error: 100°C is too hot for plants (max 40°C)

        Input data is '-50'
        Caught input_temperature error: -50°C is too cold for plants (min 0°C)

        All tests completed - program didn't crash!"""  # noqa: E501

    def static(self, ctx: Ctx, tree: Any) -> None:
        guard = A.main_guard(tree)
        body = guard if guard is not None else tree
        if not A.calls_named(body, "test_temperature"):
            ctx.ko("Le programme principal n'appelle pas test_temperature()",
                   "The main part of your file will call "
                   "test_temperature().", file=ctx.rel(self.file))
        fn = A.functions(tree).get("input_temperature")
        if fn is not None and not A.contains_node(fn, A.ast.Raise):
            ctx.ko("input_temperature() ne lève aucune exception (raise)",
                   EX1_RULE, file=ctx.rel(self.file))

    def cases(self) -> list[dict[str, Any]]:
        hot = "%d°C is too hot for plants (max 40°C)"
        cold = "%d°C is too cold for plants (min 0°C)"
        return [
            {"call": "input_temperature", "args": ["25"], "returns": 25,
             "rule": EX1_RULE},
            {"call": "input_temperature", "args": ["0"], "returns": 0,
             "rule": EX1_RULE, "label": "limite incluse : '0'"},
            {"call": "input_temperature", "args": ["40"], "returns": 40,
             "rule": EX1_RULE, "label": "limite incluse : '40'"},
            {"call": "input_temperature", "args": ["41"], "raises": "*",
             "message": hot % 41, "rule": EX1_RULE,
             "label": "'41' (trop chaud)"},
            {"call": "input_temperature", "args": ["-1"], "raises": "*",
             "message": cold % -1, "rule": EX1_RULE,
             "label": "'-1' (trop froid)"},
            {"call": "input_temperature", "args": ["100"], "raises": "*",
             "message": hot % 100, "rule": EX1_RULE},
            {"call": "input_temperature", "args": ["-50"], "raises": "*",
             "message": cold % -50, "rule": EX1_RULE},
            {"call": "input_temperature", "args": ["abc"], "raises": "*",
             "rule": EX1_RULE},
        ]


EX2_RULE = ("For each value of operation_number between 0 and 3, a different"
            " piece of faulty code will raise one of the following exception:"
            " ValueError, ZeroDivisionError, FileNotFoundError, TypeError. "
            "Other values of operation_number will not contain faulty code "
            "and simply return.")


class Ex2(M02Exercise):
    ex_id, title, directory = "ex2", "Different Types of Problems", "ex2"
    files = ["ft_different_errors.py"]
    file = files[0]
    authorized = {"print", "open", "int"}
    authorized_line = "Authorized: print(), open(), int()"
    functions = ["garden_operations", "test_error_types"]
    mypy_expected = r"Unsupported operand types for \+|\[operator\]"
    mypy_note = ("mypy will display an error for the faulty code that raises "
                 "the TypeError. That's its job!")
    output_rule = "Example: $> python3 ft_different_errors.py"
    expected_output = """
        === Garden Error Types Demo ===
        Testing operation 0...
        Caught ValueError: invalid literal for int() with base 10: 'abc'
        Testing operation 1...
        Caught ZeroDivisionError: division by zero
        Testing operation 2...
        Caught FileNotFoundError: [Errno 2] No such file or directory: '/non/existent/file'
        Testing operation 3...
        Caught TypeError: can only concatenate str (not "int") to str
        Testing operation 4...
        Operation completed successfully

        All error types tested successfully!"""  # noqa: E501

    def static(self, ctx: Ctx, tree: Any) -> None:
        multi = [h for h in A.ast.walk(tree)
                 if isinstance(h, A.ast.ExceptHandler)
                 and isinstance(h.type, A.ast.Tuple)]
        if not multi:
            ctx.ko("Aucun except qui attrape plusieurs types à la fois",
                   "Shows how to catch multiple error types with one try: "
                   "block", file=ctx.rel(self.file),
                   expected="except (ValueError, TypeError) as e:")

    def cases(self) -> list[dict[str, Any]]:
        out = []
        for n, exc in enumerate(["ValueError", "ZeroDivisionError",
                                 "FileNotFoundError", "TypeError"]):
            out.append({"call": "garden_operations", "args": [n],
                        "raises": exc, "rule": EX2_RULE})
        out.append({"call": "garden_operations", "args": [4],
                    "no_raise": True, "rule": EX2_RULE,
                    "label": "garden_operations(4) ne lève rien"})
        out.append({"call": "garden_operations", "args": [42],
                    "no_raise": True, "rule": EX2_RULE,
                    "label": "garden_operations(42) ne lève rien"})
        return out


EX3_RULE = ("Each custom exception should: Be a simple class that inherits "
            "from Exception (or GardenError); Have a specific default error "
            "message (e.g., “Unknown plant error”) if none is provided")


class Ex3(M02Exercise):
    ex_id, title, directory = "ex3", "Making Your Own Error Types", "ex3"
    files = ["ft_custom_errors.py"]
    file = files[0]
    authorized = {"print"}
    authorized_line = "Authorized: print()"
    classes = ["GardenError", "PlantError", "WaterError"]
    output_rule = "Example: $> python3 ft_custom_errors.py"
    expected_output = """
        === Custom Garden Errors Demo ===

        Testing PlantError...
        Caught PlantError: The tomato plant is wilting!

        Testing WaterError...
        Caught WaterError: Not enough water in the tank!

        Testing catching all garden errors...
        Caught GardenError: The tomato plant is wilting!
        Caught GardenError: Not enough water in the tank!

        All custom error types work correctly!"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        cls = A.classes(tree)
        parents = {"GardenError": "Exception", "PlantError": "GardenError",
                   "WaterError": "GardenError"}
        for name, parent in parents.items():
            c = cls.get(name)
            if c is not None and parent not in A.base_names(c):
                ctx.ko("%s n'hérite pas de %s" % (name, parent),
                       "GardenError - A basic error for garden problems; "
                       "PlantError - inherits from GardenError; WaterError - "
                       "inherits from GardenError",
                       got="class %s(%s)" % (name, ", ".join(
                           A.base_names(c))), file=ctx.rel(self.file))
        raising = [f.name for f in A.all_functions(tree)
                   if A.contains_node(f, A.ast.Raise)
                   and f.name != "__init__"]
        if not raising:
            ctx.ko("Aucune fonction ne lève vos exceptions",
                   "Create functions that: Raise your custom errors in "
                   "different situations", file=ctx.rel(self.file))

    def check(self, ctx: Ctx) -> None:
        super().check(ctx)
        code = """
        try:
            m = load(os.path.join(EX, %r))
        except ImportError as e:
            report("err", str(e))
        else:
            out = {}
            for n in ("GardenError", "PlantError", "WaterError"):
                cls = getattr(m, n, None)
                if cls is None:
                    continue
                c = capture(cls)
                out[n] = {"exc": c.exc,
                          "default": str(c.value) if c.value is not None
                          else None,
                          "custom": str(cls("custom message")),
                          "mro": [k.__name__ for k in cls.__mro__]}
            report("classes", out)
        """ % self.file
        p = ctx.probe(code).probe
        for name, d in (p.get("classes") or {}).items():
            if d["exc"]:
                ctx.ko("%s() sans message impossible" % name, EX3_RULE,
                       got=d["exc"], file=ctx.rel(self.file))
                continue
            if not d["default"]:
                ctx.ko("%s n'a pas de message par défaut" % name, EX3_RULE,
                       expected="str(%s()) non vide (ex : 'Unknown plant "
                                "error')" % name, got=repr(d["default"]),
                       file=ctx.rel(self.file))
            if d["custom"] != "custom message":
                ctx.ko("%s ignore le message fourni" % name, EX3_RULE,
                       expected="'custom message'", got=repr(d["custom"]),
                       file=ctx.rel(self.file))
            if "Exception" not in d["mro"]:
                ctx.ko("%s n'est pas une Exception" % name, EX3_RULE,
                       file=ctx.rel(self.file))


EX4_RULE = ("Write a function water_plant(plant_name) that: Tries to water "
            "the plant; Succeeds if the plant name is capitalized; Raises an "
            "error if the plant name is not capitalized (use your PlantError "
            "exception from the previous exercise); Prints a message on "
            "success")


class Ex4(M02Exercise):
    ex_id, title, directory = "ex4", "Finally Block", "ex4"
    files = ["ft_finally_block.py"]
    file = files[0]
    authorized = {"print"}
    authorized_line = "Authorized: print(), str.capitalize()"
    functions = ["water_plant", "test_watering_system"]
    output_rule = "Example: $> python3 ft_finally_block.py"
    expected_output = """
        === Garden Watering System ===

        Testing valid plants...
        Opening watering system
        Watering Tomato: [OK]
        Watering Lettuce: [OK]
        Watering Carrots: [OK]
        Closing watering system

        Testing invalid plants...
        Opening watering system
        Watering Tomato: [OK]
        Caught PlantError: Invalid plant name to water: 'lettuce'
        .. ending tests and returning to main
        Closing watering system

        Cleanup always happens, even with errors!"""

    def static(self, ctx: Ctx, tree: Any) -> None:
        fn = A.functions(tree).get("test_watering_system")
        if fn is None:
            return
        tries = [n for n in A.ast.walk(fn) if isinstance(n, A.ast.Try)]
        if not any(t.finalbody and t.handlers for t in tries):
            ctx.ko("Pas de structure try/except/finally dans "
                   "test_watering_system()",
                   "Uses try/except/finally structure; Always closes the "
                   "watering system in a finally block",
                   file=ctx.rel(self.file))

    def cases(self) -> list[dict[str, Any]]:
        return [
            {"call": "water_plant", "args": ["Basil"], "rule": EX4_RULE,
             "out": ["Watering Basil: [OK]"]},
            {"call": "water_plant", "args": ["basil"], "rule": EX4_RULE,
             "raises": "PlantError",
             "message": "Invalid plant name to water: 'basil'"},
            {"call": "water_plant", "args": ["Rosemary"], "rule": EX4_RULE,
             "out": ["Watering Rosemary: [OK]"]},
        ]


class Module02(Module):
    id = "02"
    title = "Garden Guardian"
    pdf = "python_module_02.pdf"
    signature = ["ex0/ft_first_exception.py", "ex1/ft_raise_exception.py",
                 "ex2/ft_different_errors.py", "ex3/ft_custom_errors.py",
                 "ex4/ft_finally_block.py"]
    exercises = [Ex0(), Ex1(), Ex2(), Ex3(), Ex4()]
    hints_rule = ("All functions and methods must include type hints: use "
                  "mypy to check your code")
    only_requested_rule = ("You need to submit only the files requested by "
                           "the subject of this project.")


MODULE = Module02()
