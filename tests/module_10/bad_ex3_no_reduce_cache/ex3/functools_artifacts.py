import functools
import operator
from collections.abc import Callable
from typing import Any

OPERATIONS: dict[str, Callable[[int, int], int]] = {
    "add": operator.add, "multiply": operator.mul, "max": max, "min": min}


def spell_reducer(spells: list[int], operation: str) -> int:
    if not spells:
        return 0
    total = spells[0]
    for value in spells[1:]:
        total = OPERATIONS[operation](total, value)
    return total


def partial_enchanter(base_enchantment: Callable) -> dict[str, Callable]:
    return {element: functools.partial(base_enchantment, power=50,
                                       element=element)
            for element in ("fire", "ice", "storm")}


def memoized_fibonacci(n: int) -> int:
    if n < 2:
        return n
    return memoized_fibonacci(n - 1) + memoized_fibonacci(n - 2)


def spell_dispatcher() -> Callable[[Any], str]:
    @functools.singledispatch
    def cast(spell: Any) -> str:
        return "Unknown spell type"

    @cast.register
    def _(spell: int) -> str:
        return f"Damage spell: {spell} damage"

    @cast.register
    def _(spell: str) -> str:
        return f"Enchantment: {spell}"

    @cast.register
    def _(spell: list) -> str:
        return f"Multi-cast: {len(spell)} spells"
    return cast


if __name__ == "__main__":
    print()
    print("Testing spell reducer...")
    powers = [10, 20, 30, 40]
    print(f"Sum: {spell_reducer(powers, 'add')}")
    print(f"Product: {spell_reducer(powers, 'multiply')}")
    print(f"Max: {spell_reducer(powers, 'max')}")
    print()
    print("Testing memoized fibonacci...")
    for n in (0, 1, 10, 15):
        print(f"Fib({n}): {memoized_fibonacci(n)}")
    print()
    print("Testing spell dispatcher...")
    dispatch = spell_dispatcher()
    for spell in (42, "fireball", ["a", "b", "c"], 3.5):
        print(dispatch(spell))
