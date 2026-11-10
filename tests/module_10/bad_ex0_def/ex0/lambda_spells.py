def artifact_sorter(artifacts: list[dict]) -> list[dict]:
    def get_power(artifact: dict) -> int:
        return int(artifact["power"])
    return sorted(artifacts, key=get_power)


def power_filter(mages: list[dict], min_power: int) -> list[dict]:
    return [m for m in mages if m["power"] > min_power]


def spell_transformer(spells: list[str]) -> list[str]:
    return list(map(lambda s: f"* {s} *", spells))


def mage_stats(mages: list[dict]) -> dict:
    strongest = max(mages, key=lambda m: m["power"])
    weakest = min(mages, key=lambda m: m["power"])
    total = sum(map(lambda m: m["power"], mages))
    return {"max_power": strongest["power"],
            "min_power": weakest["power"],
            "avg_power": round(total / len(mages), 2)}


if __name__ == "__main__":
    artifacts = [{"name": "Crystal Orb", "power": 85, "type": "orb"},
                 {"name": "Fire Staff", "power": 92, "type": "staff"}]
    print()
    print("Testing artifact sorter...")
    first, second = artifact_sorter(artifacts)[:2]
    print(f"{first['name']} ({first['power']} power) comes before "
          f"{second['name']} ({second['power']} power)")
    print()
    print("Testing spell transformer...")
    print(" ".join(spell_transformer(["fireball", "heal", "shield"])))
