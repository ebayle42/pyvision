class GardenError(Exception):
    pass


class PlantError(GardenError):
    pass


class WaterError(Exception):
    pass


def check_plant() -> None:
    raise PlantError("The tomato plant is wilting!")


def check_water() -> None:
    raise WaterError("Not enough water in the tank!")


def main() -> None:
    print("=== Custom Garden Errors Demo ===")
    print("Testing PlantError...")
    try:
        check_plant()
    except PlantError as error:
        print(f"Caught PlantError: {error}")
    print("Testing WaterError...")
    try:
        check_water()
    except WaterError as error:
        print(f"Caught WaterError: {error}")
    print("Testing catching all garden errors...")
    for test in (check_plant, check_water):
        try:
            test()
        except (GardenError, WaterError) as error:
            print(f"Caught GardenError: {error}")
    print("All custom error types work correctly!")


if __name__ == "__main__":
    main()
