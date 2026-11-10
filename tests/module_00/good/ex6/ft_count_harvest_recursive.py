def count_days(day: int, total: int) -> None:
    if day > total:
        return
    print(f"Day {day}")
    count_days(day + 1, total)


def ft_count_harvest_recursive() -> None:
    days = int(input("Days until harvest: "))
    count_days(1, days)
    print("Harvest time!")
