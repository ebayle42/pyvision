import numpy
import pandas


def main() -> None:
    print("REAGENT STATUS: Loading reagents...")
    print(f"[OK] pandas ({pandas.__version__})")
    print(f"[OK] numpy ({numpy.__version__})")


if __name__ == "__main__":
    main()
