class Plant:
    def __init__(self, name: str, height: float, age: int) -> None:
        self.name = name
        self.height = height
        self.days = age

    def show(self) -> None:
        print(f"{self.name}: {round(self.height, 1)}cm, {self.days} days old")


if __name__ == "__main__":
    print("=== Plant Factory Output ===")
    for p in (Plant("Rose", 25.0, 30), Plant("Oak", 200.0, 365),
              Plant("Cactus", 5.0, 90)):
        print("Created: ", end="")
        p.show()
