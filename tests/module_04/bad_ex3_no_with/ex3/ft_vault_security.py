def secure_archive(name: str, action: str = "r",
                   content: str = "") -> tuple[bool, str]:
    try:
        if action == "w":
            file = open(name, "w")
            file.write(content)
            file.close()
            return (True, "Content successfully written to file")
        file = open(name)
        data = file.read()
        file.close()
        return (True, data)
    except FileNotFoundError as error:
        return (False, str(error))


if __name__ == "__main__":
    print("=== Cyber Archives Security ===")
    print(secure_archive("/not/existing/file"))
