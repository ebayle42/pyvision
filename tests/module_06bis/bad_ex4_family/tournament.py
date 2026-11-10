from ex3 import CreatureFactory, FlameFactory, TransformCreatureFactory
from ex4 import (AggressiveStrategy, BattleStrategy, NormalStrategy,
                 StrategyError)


def battle(opponents: list[tuple[CreatureFactory, BattleStrategy]]) -> None:
    print("*** Tournament ***")
    print(f"{len(opponents)} opponents involved")
    fighters = [(f.create_base(), s) for f, s in opponents]
    try:
        for i, (first, s1) in enumerate(fighters):
            for second, s2 in fighters[i + 1:]:
                print()
                print("* Battle *")
                print(first.describe())
                print(" vs.")
                print(second.describe())
                print(" now fight!")
                s1.act(first)
                s2.act(second)
    except ValueError as error:
        print(f"Battle error, aborting tournament: {error}")


if __name__ == "__main__":
    flame, transform = FlameFactory(), TransformCreatureFactory()
    normal, aggressive = NormalStrategy(), AggressiveStrategy()
    print("Tournament 0 (basic)")
    print(" [ (Flameling+Normal), (Shiftling+Aggressive) ]")
    battle([(flame, normal), (transform, aggressive)])
    print()
    print("Tournament 1 (error)")
    print(" [ (Shiftling+Aggressive), (Flameling+Aggressive) ]")
    battle([(transform, aggressive), (flame, aggressive)])
