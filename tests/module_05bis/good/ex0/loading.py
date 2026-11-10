import importlib

REAGENTS = {"pandas": "Data manipulation ready",
            "numpy": "Numerical computation ready"}


def main() -> None:
    print("REAGENT STATUS: Loading reagents...")
    print()
    print("Checking dependencies:")
    missing = []
    for name, role in REAGENTS.items():
        try:
            module = importlib.import_module(name)
        except ImportError:
            print(f"[MISSING] {name} - not installed")
            missing.append(name)
            continue
        print(f"[OK] {name} ({module.__version__}) - {role}")
    print()
    print("pip vs Poetry:")
    print("  requirements.txt declares what to install; pip resolves it at "
          "install time.")
    print("  pyproject.toml declares the same constraints, and Poetry pins "
          "the resolved")
    print("  versions in poetry.lock so every install is identical.")
    print()
    if missing:
        print("Some reagents are missing. Install them with:")
        print("  pip install -r ex0/requirements.txt")
        print("  poetry install")
    else:
        print("All reagents present and accounted for.")


if __name__ == "__main__":
    main()
