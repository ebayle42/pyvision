class Plant:
    name: str
    height: int
    age: int

    def show(self) -> None:
        print(f"{self.name}: {self.height}cm, {self.age} days old")


if __name__ == "__main__":
    rose = Plant()
    rose.name, rose.height, rose.age = "Rose", 25, 30
    sunflower = Plant()
    sunflower.name, sunflower.height, sunflower.age = "Sunflower", 80, 45
    cactus = Plant()
    cactus.name, cactus.height, cactus.age = "Cactus", 15, 120
    print("=== Garden Plant Registry ===")
    for plant in (rose, sunflower, cactus):
        plant.show()
