import math


def get_player_pos() -> list[float]:
    text = input("Enter new coordinates as floats in format 'x,y,z': ")
    parts = text.split(",")
    return [float(parts[0]), float(parts[1]), float(parts[2])]


if __name__ == "__main__":
    print("=== Game Coordinate System ===")
    print("Get a first set of coordinates")
    first = get_player_pos()
    print(f"Got a first tuple: {first}")
    print(f"Distance to center: {round(math.sqrt(first[0] ** 2), 4)}")
