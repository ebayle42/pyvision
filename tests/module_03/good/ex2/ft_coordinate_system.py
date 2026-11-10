import math


def get_player_pos() -> tuple[float, float, float]:
    while True:
        text = input("Enter new coordinates as floats in format 'x,y,z': ")
        try:
            raw_x, raw_y, raw_z = text.split(",")
        except ValueError:
            print("Invalid syntax")
            continue
        values: list[float] = []
        try:
            for part in (raw_x, raw_y, raw_z):
                current = part
                values.append(float(part))
        except ValueError as error:
            print(f"Error on parameter '{current.strip()}': {error}")
            continue
        return (values[0], values[1], values[2])


def distance(a: tuple[float, float, float],
             b: tuple[float, float, float]) -> float:
    return math.sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
                     + (b[2] - a[2]) ** 2)


if __name__ == "__main__":
    print("=== Game Coordinate System ===")
    print()
    print("Get a first set of coordinates")
    first = get_player_pos()
    print(f"Got a first tuple: {first}")
    print(f"It includes: X={first[0]}, Y={first[1]}, Z={first[2]}")
    print(f"Distance to center: {round(distance((0, 0, 0), first), 4)}")
    print()
    print("Get a second set of coordinates")
    second = get_player_pos()
    print("Distance between the 2 sets of coordinates: "
          f"{round(distance(first, second), 4)}")
