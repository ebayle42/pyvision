def garden_operations(operation_number: int) -> None:
    if operation_number == 0:
        int("abc")
    elif operation_number == 1:
        print(1 / 0)
    elif operation_number == 2:
        open("/non/existent/file")
    elif operation_number == 3:
        print("abc" + 1)


def test_error_types() -> None:
    print("=== Garden Error Types Demo ===")
    number = 0
    while number < 5:
        print(f"Testing operation {number}...")
        try:
            garden_operations(number)
            print("Operation completed successfully")
        except (ValueError, ZeroDivisionError, FileNotFoundError) as error:
            print(f"Caught {error.__class__.__name__}: {error}")
        number += 1
    print("All error types tested successfully!")


if __name__ == "__main__":
    test_error_types()
