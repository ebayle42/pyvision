import random

ACHIEVEMENTS = ["Crafting Genius", "World Savior", "Master Explorer",
                "Collector Supreme", "Untouchable", "Boss Slayer",
                "Strategist", "Unstoppable", "Speed Runner", "Survivor",
                "Treasure Hunter", "First Steps", "Sharp Mind",
                "Hidden Path Finder"]


def gen_player_achievements() -> set[str]:
    count = random.randint(4, 9)
    return set(random.sample(ACHIEVEMENTS, count))


if __name__ == "__main__":
    print("=== Achievement Tracker System ===")
    names = ["Alice", "Bob", "Charlie", "Dylan"]
    players = [(name, gen_player_achievements()) for name in names]
    for name, achievements in players:
        print(f"Player {name}: {achievements}")
    distinct: set[str] = set()
    common = players[0][1]
    for name, achievements in players:
        distinct = distinct.union(achievements)
        common = common.intersection(achievements)
    print(f"All distinct achievements: {distinct}")
    print(f"Common achievements: {common}")
    for name, achievements in players:
        others: set[str] = set()
        for other, other_achievements in players:
            if other != name:
                others = others.union(other_achievements)
        print(f"Only {name} has: {achievements.difference(others)}")
    for name, achievements in players:
        print(f"{name} is missing: {distinct.difference(achievements)}")
