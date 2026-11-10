"""Registre des modules : chaque fichier modules/module_XX.py définit une
variable MODULE. Ajouter un module = ajouter un fichier."""
from __future__ import annotations

import importlib
import pkgutil

from core.base import Module


def load_modules() -> list[Module]:
    out: list[Module] = []
    for info in sorted(pkgutil.iter_modules(__path__), key=lambda i: i.name):
        if not info.name.startswith("module_"):
            continue
        mod = importlib.import_module(__name__ + "." + info.name)
        m = getattr(mod, "MODULE", None)
        if isinstance(m, Module):
            out.append(m)
    return out
