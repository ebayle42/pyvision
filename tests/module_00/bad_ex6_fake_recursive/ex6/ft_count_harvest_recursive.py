def ft_count_harvest_recursive() -> None:
    days = int(input("Days until harvest: "))
    for day in range(1, days + 1):
        print(f"Day {day}")
    print("Harvest time!")
