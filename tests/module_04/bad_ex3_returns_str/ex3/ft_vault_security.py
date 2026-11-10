def secure_archive(name: str, action: str = "r",
                   content: str = "") -> str:
    try:
        if action == "w":
            with open(name, "w") as file:
                file.write(content)
            return "Content successfully written to file"
        with open(name) as file:
            return file.read()
    except OSError as error:
        return str(error)


if __name__ == "__main__":
    print("=== Cyber Archives Security ===")
    print(secure_archive("/not/existing/file"))
