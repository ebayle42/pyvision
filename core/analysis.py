"""Analyse statique du code élève avec ast (le code n'est jamais exécuté)."""
from __future__ import annotations

import ast
import builtins
from dataclasses import dataclass
from typing import Iterator

BUILTIN_NAMES = set(dir(builtins))
EXCEPTION_NAMES = {n for n in BUILTIN_NAMES
                   if isinstance(getattr(builtins, n), type)
                   and issubclass(getattr(builtins, n), BaseException)}


@dataclass
class Source:
    path: str
    text: str
    tree: ast.Module | None
    error: str | None = None

    def segment(self, node: ast.AST) -> str:
        return ast.get_source_segment(self.text, node) or ""


def parse(path: str, text: str) -> Source:
    try:
        return Source(path, text, ast.parse(text, filename=path))
    except SyntaxError as e:
        return Source(path, text, None,
                      "SyntaxError ligne %s : %s" % (e.lineno, e.msg))


def walk(node: ast.AST) -> Iterator[ast.AST]:
    return ast.walk(node)


def is_main_guard(node: ast.AST) -> bool:
    """`if __name__ == "__main__":`"""
    if not isinstance(node, ast.If):
        return False
    t = node.test
    if isinstance(t, ast.Compare) and len(t.ops) == 1 \
            and isinstance(t.ops[0], ast.Eq):
        sides = [t.left, t.comparators[0]]
        names = [s for s in sides if isinstance(s, ast.Name)
                 and s.id == "__name__"]
        consts = [s for s in sides if isinstance(s, ast.Constant)
                  and s.value == "__main__"]
        return bool(names and consts)
    return False


def main_guard(tree: ast.Module) -> ast.If | None:
    for node in tree.body:
        if is_main_guard(node):
            assert isinstance(node, ast.If)
            return node
    return None


def is_docstring(node: ast.stmt) -> bool:
    return isinstance(node, ast.Expr) and isinstance(node.value,
                                                     ast.Constant) \
        and isinstance(node.value.value, str)


def toplevel_code(tree: ast.Module) -> list[ast.stmt]:
    """Instructions de niveau module qui ne sont ni des définitions, ni des
    imports, ni des docstrings."""
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef, ast.Import, ast.ImportFrom)):
            continue
        if is_docstring(node):
            continue
        out.append(node)
    return out


def functions(tree: ast.AST) -> dict[str, ast.FunctionDef]:
    """Fonctions définies au niveau module."""
    body = tree.body if isinstance(tree, ast.Module) else []
    return {n.name: n for n in body if isinstance(n, ast.FunctionDef)}


def all_functions(tree: ast.AST) -> list[ast.FunctionDef]:
    return [n for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def classes(tree: ast.AST) -> dict[str, ast.ClassDef]:
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


def methods(cls: ast.ClassDef) -> dict[str, ast.FunctionDef]:
    return {n.name: n for n in cls.body if isinstance(n, ast.FunctionDef)}


def base_names(cls: ast.ClassDef) -> list[str]:
    out = []
    for b in cls.bases:
        if isinstance(b, ast.Name):
            out.append(b.id)
        elif isinstance(b, ast.Attribute):
            out.append(b.attr)
        elif isinstance(b, ast.Subscript):
            v = b.value
            out.append(v.id if isinstance(v, ast.Name) else
                       getattr(v, "attr", "?"))
    return out


def decorator_names(fn: ast.FunctionDef | ast.ClassDef) -> list[str]:
    out = []
    for d in fn.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if isinstance(target, ast.Name):
            out.append(target.id)
        elif isinstance(target, ast.Attribute):
            out.append(target.attr)
    return out


def call_name(node: ast.Call) -> str | None:
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def calls(node: ast.AST) -> list[ast.Call]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Call)]


def calls_named(node: ast.AST, name: str) -> list[ast.Call]:
    return [c for c in calls(node) if call_name(c) == name]


def defined_names(tree: ast.AST) -> set[str]:
    """Noms définis par l'élève (fonctions, classes, variables, params)."""
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            out.add(n.name)
        elif isinstance(n, ast.arg):
            out.add(n.arg)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            out.add(n.id)
        elif isinstance(n, ast.alias):
            out.add((n.asname or n.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
    return out


def builtin_calls(tree: ast.AST) -> list[tuple[str, int]]:
    """Appels directs à des fonctions natives (print, len, ...) qui ne sont
    pas redéfinies par l'élève."""
    local = defined_names(tree)
    out = []
    for c in calls(tree):
        if isinstance(c.func, ast.Name) and c.func.id in BUILTIN_NAMES \
                and c.func.id not in local:
            out.append((c.func.id, c.lineno))
    return out


def builtin_refs(tree: ast.AST) -> list[tuple[str, int]]:
    """Fonctions natives passées en argument sans être appelées
    (ex: map(len, ...), sorted(key=len))."""
    local = defined_names(tree)
    out = []
    for c in calls(tree):
        for a in list(c.args) + [k.value for k in c.keywords]:
            if isinstance(a, ast.Name) and a.id in BUILTIN_NAMES \
                    and a.id not in local and callable(
                        getattr(builtins, a.id, None)):
                out.append((a.id, a.lineno))
    return out


@dataclass
class ImportInfo:
    module: str           # "sys", "alchemy.elements", ".dark_validator"
    names: list[str]      # noms importés (from ... import a, b)
    kind: str             # "import" | "from"
    level: int
    lineno: int
    toplevel: bool

    @property
    def root(self) -> str:
        return self.module.lstrip(".").split(".")[0] if self.module else ""


def imports(tree: ast.Module) -> list[ImportInfo]:
    top = {id(n) for n in tree.body}
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.append(ImportInfo(a.name, [], "import", 0, n.lineno,
                                      id(n) in top))
        elif isinstance(n, ast.ImportFrom):
            mod = "." * n.level + (n.module or "")
            out.append(ImportInfo(mod, [a.name for a in n.names], "from",
                                  n.level, n.lineno, id(n) in top))
    return out


def missing_annotations(tree: ast.AST) -> list[tuple[str, int, str]]:
    """Fonctions/méthodes sans type hints (paramètres ou retour)."""
    out = []
    for fn in all_functions(tree):
        args = fn.args
        params = args.posonlyargs + args.args + args.kwonlyargs
        if args.vararg:
            params.append(args.vararg)
        if args.kwarg:
            params.append(args.kwarg)
        for i, a in enumerate(params):
            if a.annotation is None and not (i == 0 and a.arg in
                                             ("self", "cls")):
                out.append((fn.name, fn.lineno,
                            "paramètre '%s' sans annotation" % a.arg))
        if fn.returns is None:
            out.append((fn.name, fn.lineno, "type de retour manquant"))
    return out


def self_attr_assigns(cls: ast.ClassDef) -> dict[str, int]:
    """Attributs affectés via self.xxx = ... dans les méthodes."""
    out: dict[str, int] = {}
    for n in ast.walk(cls):
        targets: list[ast.expr] = []
        if isinstance(n, ast.Assign):
            targets = list(n.targets)
        elif isinstance(n, (ast.AnnAssign, ast.AugAssign)):
            targets = [n.target]
        for t in targets:
            for sub in ast.walk(t):
                if isinstance(sub, ast.Attribute) and isinstance(
                        sub.value, ast.Name) and sub.value.id == "self":
                    out.setdefault(sub.attr, sub.lineno)
    return out


def uses_super(fn: ast.AST, method: str | None = None) -> bool:
    for c in calls(fn):
        f = c.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call) \
                and call_name(f.value) == "super":
            if method is None or f.attr == method:
                return True
    return False


def calls_parent_method(fn: ast.AST, method: str, parents: list[str]
                        ) -> bool:
    """super().method(...) ou Parent.method(self, ...)."""
    if uses_super(fn, method):
        return True
    for c in calls(fn):
        f = c.func
        if isinstance(f, ast.Attribute) and f.attr == method \
                and isinstance(f.value, ast.Name) and f.value.id in parents:
            return True
    return False


def has_try(node: ast.AST) -> bool:
    return any(isinstance(n, (ast.Try, getattr(ast, "TryStar", ast.Try)))
               for n in ast.walk(node))


def has_yield(fn: ast.AST) -> bool:
    return any(isinstance(n, (ast.Yield, ast.YieldFrom))
               for n in ast.walk(fn))


def has_with(node: ast.AST) -> bool:
    return any(isinstance(n, (ast.With, ast.AsyncWith))
               for n in ast.walk(node))


def has_global(node: ast.AST) -> list[int]:
    return [n.lineno for n in ast.walk(node) if isinstance(n, ast.Global)]


def string_constants(node: ast.AST) -> list[tuple[str, int]]:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append((n.value, n.lineno))
    return out


def const_arith(node: ast.AST) -> list[tuple[str, int]]:
    """Calculs entre constantes numériques (ex: 0.8 * 7) : signe d'un
    résultat écrit en dur."""
    out = []

    def is_num(e: ast.AST) -> bool:
        if isinstance(e, ast.Constant):
            return isinstance(e.value, (int, float)) and not isinstance(
                e.value, bool)
        if isinstance(e, ast.UnaryOp):
            return is_num(e.operand)
        if isinstance(e, ast.BinOp):
            return is_num(e.left) and is_num(e.right)
        return False

    for n in ast.walk(node):
        if isinstance(n, ast.BinOp) and is_num(n):
            out.append((ast.unparse(n), n.lineno))
    return out


def comprehensions(node: ast.AST) -> dict[str, int]:
    out = {"list": 0, "dict": 0, "set": 0, "gen": 0}
    for n in ast.walk(node):
        if isinstance(n, ast.ListComp):
            out["list"] += 1
        elif isinstance(n, ast.DictComp):
            out["dict"] += 1
        elif isinstance(n, ast.SetComp):
            out["set"] += 1
        elif isinstance(n, ast.GeneratorExp):
            out["gen"] += 1
    return out


def lambdas(node: ast.AST) -> list[ast.Lambda]:
    return [n for n in ast.walk(node) if isinstance(n, ast.Lambda)]


def contains_node(node: ast.AST, kind: type) -> bool:
    return any(isinstance(n, kind) for n in ast.walk(node))


def function_calls_function(fn: ast.AST, name: str) -> bool:
    return bool(calls_named(fn, name))


def is_recursive(fn: ast.FunctionDef, tree: ast.AST) -> bool:
    """Vraie récursion : la fonction (ou une fonction auxiliaire qu'elle
    appelle) s'appelle elle-même."""
    funcs = {f.name: f for f in all_functions(tree)}

    def reachable(start: str) -> set[str]:
        seen: set[str] = set()
        todo = [start]
        while todo:
            cur = todo.pop()
            f = funcs.get(cur)
            if f is None:
                continue
            for c in calls(f):
                nm = call_name(c)
                if nm in funcs and nm not in seen:
                    seen.add(nm)
                    todo.append(nm)
        return seen

    for name in {fn.name} | reachable(fn.name):
        if name in reachable(name):
            return True
    return False
