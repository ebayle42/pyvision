#!/usr/bin/env python3
"""Validation de pyvision sur les jeux de test.

tests/module_XX/good/        : rendu correct -> OK partout
tests/module_XX/<cas>/       : fichiers qui remplacent ceux de good/,
                               plus expect.json :
    {"expect": {"ex1": "KO"},          statut attendu (les autres : OK)
     "titles": {"ex1": ["prompt"]},    morceaux de titres de problème
                                       qui doivent apparaître
     "delete": ["ex1/file.py"],        fichiers de good/ à supprimer
     "ko_count": {"ex1": 1},           nombre exact de KO affichés
                                       (vérifie le regroupement)
     "module": "00"}                   (facultatif) module forcé
Usage : python3 tests/run_tests.py [module_00 ...] [-k cas]
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYVISION = HERE.parent / "pyvision.py"


def run(root: Path, module: str) -> dict:
    proc = subprocess.run([sys.executable, str(PYVISION), "--json", "-m",
                           module, "-C", str(root)],
                          capture_output=True, text=True, timeout=900)
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print(proc.stdout, proc.stderr)
        raise


def main() -> int:
    args = sys.argv[1:]
    only = None
    if "-k" in args:
        i = args.index("-k")
        only = args[i + 1]
        del args[i:i + 2]
    mods = args or sorted(p.name for p in HERE.glob("module_*"))
    failures = 0
    total = 0
    for mod in mods:
        mdir = HERE / mod
        mid = mod.removeprefix("module_")
        good = mdir / "good"
        base_spec = {}
        if (good / "expect.json").exists():
            base_spec = json.loads((good / "expect.json").read_text())
        for case in sorted(p for p in mdir.iterdir() if p.is_dir()):
            if only and only not in case.name:
                continue
            total += 1
            spec = {}
            if (case / "expect.json").exists():
                spec = json.loads((case / "expect.json").read_text())
            with tempfile.TemporaryDirectory(prefix="pvt-") as tmp:
                root = Path(tmp) / "repo"
                shutil.copytree(good, root)
                if case != good:
                    for f in spec.get("delete", []):
                        target = root / f
                        if target.is_dir():
                            shutil.rmtree(target)
                        elif target.exists():
                            target.unlink()
                    for p in case.rglob("*"):
                        rel = p.relative_to(case)
                        if rel.name == "expect.json":
                            continue
                        dest = root / rel
                        if p.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(p, dest)
                if spec.get("git_commit"):
                    g = ["git", "-C", str(root)]
                    subprocess.run(g + ["init", "-q"], check=True)
                    subprocess.run(g + ["add", "-f"] + spec["git_commit"],
                                   check=True)
                    subprocess.run(g + ["-c", "user.name=t", "-c",
                                        "user.email=t@t", "commit", "-qm",
                                        "t"], check=True)
                out = run(root, spec.get("module", mid))
            expect = dict(base_spec.get("expect", {}))
            expect.update(spec.get("expect", {}))
            titles = spec.get("titles", {})
            ko_count = spec.get("ko_count", {})
            errors = []
            for r in out["results"]:
                want = expect.get(r["ex"], "OK")
                if r["status"] != want:
                    errors.append("%s: attendu %s, obtenu %s %s" % (
                        r["ex"], want, r["status"],
                        [i["title"] for i in r["issues"]]))
                # Titres cherchés aussi dans les problèmes regroupés.
                all_titles = [i["title"] for i in r["issues"]] + [
                    j["title"] for i in r["issues"]
                    for j in i.get("related", [])]
                for t in titles.get(r["ex"], []):
                    if not any(t.lower() in a.lower() for a in all_titles):
                        errors.append("%s: problème « %s » non détecté %s"
                                      % (r["ex"], t, [i["title"] for i in
                                                      r["issues"]]))
                n_ko = sum(1 for i in r["issues"] if i["level"] == "KO")
                if r["ex"] in ko_count and n_ko != ko_count[r["ex"]]:
                    errors.append("%s: %d KO affiché(s), attendu %d %s" % (
                        r["ex"], n_ko, ko_count[r["ex"]],
                        [i["title"] for i in r["issues"]]))
            name = "%s/%s" % (mod, case.name)
            if errors:
                failures += 1
                print("\033[31mÉCHEC\033[0m", name)
                for e in errors:
                    print("     ", e)
            else:
                print("\033[32mOK   \033[0m", name)
    print("\n%d/%d jeux de test conformes" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
