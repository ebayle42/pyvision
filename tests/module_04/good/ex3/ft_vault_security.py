def secure_archive(name: str, action: str = "r",
                   content: str = "") -> tuple[bool, str]:
    try:
        if action == "w":
            with open(name, "w") as file:
                file.write(content)
            return (True, "Content successfully written to file")
        with open(name) as file:
            return (True, file.read())
    except OSError as error:
        return (False, str(error))


if __name__ == "__main__":
    print("=== Cyber Archives Security ===")
    print()
    print("Using 'secure_archive' to read from a nonexistent file:")
    print(secure_archive("/not/existing/file"))
    print()
    print("Using 'secure_archive' to read from an inaccessible file:")
    print(secure_archive("/etc/master.passwd"))
    print()
    print("Using 'secure_archive' to read from a regular file:")
    result = secure_archive("ancient_fragment.txt")
    print(result)
    print()
    print("Using 'secure_archive' to write previous content to a new file:")
    print(secure_archive("new_fragment.txt", "w", result[1]))
