from collections.abc import Callable


def spell_combiner(spell1: Callable, spell2: Callable) -> Callable:
    def combined(target: str, power: int) -> tuple[str, str]:
        return (spell1(target, power), spell2(target, power))
    return combined


def power_amplifier(base_spell: Callable, multiplier: int) -> Callable:
    def amplified(target: str, power: int) -> str:
        return str(base_spell(target, power * multiplier))
    return amplified


def conditional_caster(condition: Callable, spell: Callable) -> Callable:
    def caster(target: str, power: int) -> str:
        if condition(target, power):
            return str(spell(target, power))
        return "Spell fizzled"
    return caster


def spell_sequence(spells: list[Callable]) -> Callable:
    def sequence(target: str, power: int) -> list[str]:
        return [spell(target, power) for spell in spells]
    return sequence


def fireball(target: str, power: int) -> str:
    return f"Fireball hits {target}"


def heal(target: str, power: int) -> str:
    return f"Heals {target}"


def damage(target: str, power: int) -> int:
    return power


if __name__ == "__main__":
    print()
    print("Testing spell combiner...")
    combined = spell_combiner(fireball, heal)
    print("Combined spell result: " + ", ".join(combined("Dragon", 10)))
    print()
    print("Testing power amplifier...")
    mega = power_amplifier(damage, 3)
    print(f"Original: {damage('Dragon', 10)}, Amplified: {mega('Dragon', 10)}")
