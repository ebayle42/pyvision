import sys

sys.path.append("..")

from alchemy.potions import strength_potion  # noqa: E402


def lead_to_gold() -> str:
    return ("Recipe transmuting Lead to Gold: brew 'Air element created' "
            f"and '{strength_potion()}' mixed with 'Fire element created'")
