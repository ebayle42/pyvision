from ex3 import TransformCreatureFactory


def show(label: str, creature: object) -> None:
    print(label)
    print(getattr(creature, "describe")())
    print(getattr(creature, "attack")())
    print(getattr(creature, "transform")())
    print(getattr(creature, "attack")())
    print(getattr(creature, "revert")())


if __name__ == "__main__":
    print("Testing Creature with transform capability")
    factory = TransformCreatureFactory()
    show(" base:", factory.create_base())
    show(" evolved:", factory.create_evolved())
