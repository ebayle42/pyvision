class Plant:
    def __init__(self, name: str, height: float, age: int) -> None:
        self.name = name
        self.height = height
        self.days = age

    def show(self) -> None:
        print(f"{self.name}: {round(self.height, 1)}cm, {self.days} days old")

    def grow(self) -> None:
        self.height += 1

    def age(self) -> None:
        self.days += 1


if __name__ == "__main__":
    plants = [Plant("Rose", 25.0, 30), Plant("Oak", 200.0, 365),
              Plant("Cactus", 5.0, 90), Plant("Sunflower", 80.0, 45),
              Plant("Fern", 15.0, 120)]
    print("=== Plant Factory Output ===")
    for plant in plants:
        print("Created: ", end="")
        plant.show()
