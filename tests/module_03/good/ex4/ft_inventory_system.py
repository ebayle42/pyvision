import sys


def main() -> None:
    print("=== Inventory System Analysis ===")
    inventory: dict[str, int] = {}
    for arg in sys.argv[1:]:
        parts = arg.split(":")
        if len(parts) != 2:
            print(f"Error - invalid parameter '{arg}'")
            continue
        name, quantity = parts
        if name in inventory.keys():
            print(f"Redundant item '{name}' - discarding")
            continue
        try:
            inventory.update({name: int(quantity)})
        except ValueError as error:
            print(f"Quantity error for '{name}': {error}")
    print(f"Got inventory: {inventory}")
    items = list(inventory.keys())
    print(f"Item list: {items}")
    total = sum(inventory.values())
    print(f"Total quantity of the {len(items)} items: {total}")
    if total == 0:
        return
    for name in items:
        print(f"Item {name} represents "
              f"{round(inventory[name] / total * 100, 1)}%")
    most = items[0]
    least = items[0]
    for name in items:
        if inventory[name] > inventory[most]:
            most = name
        if inventory[name] < inventory[least]:
            least = name
    print(f"Item most abundant: {most} with quantity {inventory[most]}")
    print(f"Item least abundant: {least} with quantity {inventory[least]}")
    inventory.update({"magic_item": 1})
    print(f"Updated inventory: {inventory}")


if __name__ == "__main__":
    main()
