def show(plant: dict[str, str]) -> None:
    print(f"{plant['name']}: {plant['height']}cm, {plant['age']} days old")


if __name__ == "__main__":
    print("=== Garden Plant Registry ===")
    show({"name": "Rose", "height": "25", "age": "30"})
    show({"name": "Sunflower", "height": "80", "age": "45"})
    show({"name": "Cactus", "height": "15", "age": "120"})
