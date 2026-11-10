import sys


def recover(name: str) -> None:
    print("=== Cyber Archives Recovery ===")
    print(f"Accessing file '{name}'")
    try:
        with open(name) as file:
            content = file.read()
    except OSError as error:
        print(f"Error opening file '{name}': {error}")
        return
    print("---")
    print(content, end="")
    print("---")
    print(f"File '{name}' closed.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file>")
    else:
        recover(sys.argv[1])
