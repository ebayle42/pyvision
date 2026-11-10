from ex3 import CreatureFactory, FlameFactory, TransformCreatureFactory


def test_factory(factory: CreatureFactory) -> None:
    print("Testing factory")
    for creature in (factory.create_base(), factory.create_evolved()):
        print(creature.describe())
        print(creature.attack())


def battle(first: CreatureFactory, second: CreatureFactory) -> None:
    print("Testing battle")
    a, b = first.create_base(), second.create_base()
    print(a.describe())
    print(" vs.")
    print(b.describe())
    print(" fight!")
    print(a.attack())
    print(b.attack())


if __name__ == "__main__":
    flame, transform = FlameFactory(), TransformCreatureFactory()
    test_factory(flame)
    print()
    test_factory(transform)
    print()
    battle(flame, transform)
