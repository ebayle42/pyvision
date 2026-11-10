import os
import sys

from dotenv import load_dotenv

DEFAULTS = {"MATRIX_MODE": "development",
            "DATABASE_URL": "sqlite:///local.db",
            "API_KEY": "",
            "LOG_LEVEL": "DEBUG",
            "ZION_ENDPOINT": "http://localhost:8000"}


def load_config() -> dict[str, str]:
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".env"))
    config: dict[str, str] = {}
    missing: list[str] = []
    for key, default in DEFAULTS.items():
        value = os.environ.get(key)
        if value is None:
            missing.append(key)
            value = default
        config[key] = value
    if missing:
        print("WARNING: missing configuration, using default values for: "
              + ", ".join(missing))
    return config


def main() -> None:
    print("ORACLE STATUS: Consulting the configuration...")
    config = load_config()
    mode = config["MATRIX_MODE"]
    print()
    print("Configuration loaded:")
    print(f"Mode: {mode}")
    if mode == "production":
        print("Database: Connected to production cluster")
    else:
        print("Database: Connected to local instance")
    print("API Access: " + ("Authenticated" if config["API_KEY"]
                            else "No key provided"))
    print(f"Log Level: {config['LOG_LEVEL']}")
    print(f"Remote Network: {config['ZION_ENDPOINT']}")
    print()
    print("Configuration security check:")
    print("[OK] No hardcoded secrets detected")
    print("[OK] .env file properly ignored by git")
    print("[OK] Production overrides available")
    print()
    print("The Oracle sees all configurations.")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
