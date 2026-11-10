import sys

if __name__ == "__main__":
    name = sys.argv[1]
    print("=== Cyber Archives Recovery ===")
    print(f"Accessing file '{name}'")
    file = open(name)
    print("---")
    print(file.read(), end="")
    print("---")
    file.close()
    print(f"File '{name}' closed.")
