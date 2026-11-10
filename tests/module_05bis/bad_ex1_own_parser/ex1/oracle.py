import os


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as file:
            for line in file:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    values[key] = value
    return values


def main() -> None:
    values = load_env()
    mode = os.environ.get("MATRIX_MODE", values.get("MATRIX_MODE", "dev"))
    print("ORACLE STATUS: Consulting the configuration...")
    print(f"Mode: {mode}")
    for key in ("DATABASE_URL", "API_KEY", "LOG_LEVEL", "ZION_ENDPOINT"):
        print(f"{key}: {'set' if key in values else 'missing'}")


if __name__ == "__main__":
    main()
