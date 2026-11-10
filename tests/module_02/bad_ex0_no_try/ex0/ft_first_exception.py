def input_temperature(temp_str: str) -> int:
    if temp_str.isdigit():
        return int(temp_str)
    return -1


def test_temperature() -> None:
    print("=== Garden Temperature ===")
    print("Input data is '25'")
    print(f"Temperature is now {input_temperature('25')}°C")
    print("Input data is 'abc'")
    print("Caught input_temperature error: "
          "invalid literal for int() with base 10: 'abc'")
    print("All tests completed - program didn't crash!")


if __name__ == "__main__":
    test_temperature()
