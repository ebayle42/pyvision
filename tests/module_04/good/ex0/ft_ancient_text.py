import sys
import typing


def recover(name: str) -> None:
    print("=== Cyber Archives Recovery ===")
    print(f"Accessing file '{name}'")
    try:
        file: typing.IO[str] = open(name)
    except OSError as error:
        print(f"Error opening file '{name}': {error}")
        return
    try:
        content = file.read()
    except OSError as error:
        print(f"Error reading file '{name}': {error}")
        file.close()
        return
    print("---")
    print()
    print(content)
    print("---")
    file.close()
    print(f"File '{name}' closed.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file>")
    else:
        recover(sys.argv[1])
