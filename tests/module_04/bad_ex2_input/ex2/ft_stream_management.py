import sys
import typing


def error(message: str) -> None:
    sys.stderr.write(f"[STDERR] {message}\n")


def read_file(name: str) -> str | None:
    print(f"Accessing file '{name}'")
    try:
        file: typing.IO[str] = open(name)
    except OSError as err:
        error(f"Error opening file '{name}': {err}")
        return None
    try:
        content = file.read()
    except OSError as err:
        error(f"Error reading file '{name}': {err}")
        file.close()
        return None
    print("---")
    print(content, end="")
    print("---")
    file.close()
    print(f"File '{name}' closed.")
    return content


def save(name: str, content: str) -> None:
    print(f"Saving data to '{name}'")
    try:
        file: typing.IO[str] = open(name, "w")
    except OSError as err:
        error(f"Error opening file '{name}': {err}")
        print("Data not saved.")
        return
    file.write(content)
    file.close()
    print(f"Data saved in file '{name}'.")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <file>")
        return
    print("=== Cyber Archives Recovery & Preservation ===")
    content = read_file(sys.argv[1])
    if content is None:
        return
    new = "".join(line + "#\n" for line in content.splitlines())
    print("Transform data:")
    print("---")
    print(new, end="")
    print("---")
    print("Enter new file name (or empty): ", end="")
    sys.stdout.flush()
    name = input()
    if name == "":
        print("Not saving data.")
    else:
        save(name, new)


if __name__ == "__main__":
    main()
