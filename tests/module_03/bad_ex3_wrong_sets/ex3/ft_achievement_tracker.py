import random

ACHIEVEMENTS = ["Crafting Genius", "World Savior", "Master Explorer",
                "Collector Supreme", "Untouchable", "Boss Slayer",
                "Strategist", "Unstoppable", "Speed Runner", "Survivor"]


def gen_player_achievements() -> set[str]:
    return set(random.sample(ACHIEVEMENTS, 5))


if __name__ == "__main__":
    print("=== Achievement Tracker System ===")
    names = ["Alice", "Bob", "Charlie", "Dylan"]
    players = [(name, gen_player_achievements()) for name in names]
    for name, achievements in players:
        print(f"Player {name}: {achievements}")
    distinct: set[str] = set()
    for name, achievements in players:
        distinct = distinct.union(achievements)
    print(f"All distinct achievements: {distinct}")
    print(f"Common achievements: {distinct}")
    for name, achievements in players:
        print(f"Only {name} has: {achievements}")
    for name, achievements in players:
        print(f"{name} is missing: {distinct.difference(achievements)}")
