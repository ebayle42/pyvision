import typing
from abc import ABC, abstractmethod
from typing import Any


class DataProcessor(ABC):
    def __init__(self) -> None:
        self._data: list[tuple[int, str]] = []
        self._rank = 0
        self._total = 0

    @abstractmethod
    def validate(self, data: Any) -> bool:
        pass

    @abstractmethod
    def ingest(self, data: Any) -> None:
        pass

    def _store(self, value: str) -> None:
        self._data.append((self._rank, value))
        self._rank += 1
        self._total += 1

    def output(self) -> tuple[int, str]:
        return self._data.pop(0)

    def remaining(self) -> int:
        return len(self._data)

    def total(self) -> int:
        return self._total


class NumericProcessor(DataProcessor):
    name = "Numeric Processor"

    @staticmethod
    def _is_number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def validate(self, data: Any) -> bool:
        if isinstance(data, list):
            return all(self._is_number(item) for item in data)
        return self._is_number(data)

    def ingest(self, data: int | float | list[int | float]) -> None:
        if not self.validate(data):
            raise ValueError("Improper numeric data")
        items = data if isinstance(data, list) else [data]
        for item in items:
            self._store(str(item))


class TextProcessor(DataProcessor):
    name = "Text Processor"

    def validate(self, data: Any) -> bool:
        if isinstance(data, list):
            return all(isinstance(item, str) for item in data)
        return isinstance(data, str)

    def ingest(self, data: str | list[str]) -> None:
        if not self.validate(data):
            raise ValueError("Improper text data")
        items = data if isinstance(data, list) else [data]
        for item in items:
            self._store(item)


class LogProcessor(DataProcessor):
    name = "Log Processor"

    @staticmethod
    def _is_log(value: Any) -> bool:
        return isinstance(value, dict) and all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in value.items())

    def validate(self, data: Any) -> bool:
        if isinstance(data, list):
            return all(self._is_log(item) for item in data)
        return self._is_log(data)

    def ingest(self, data: dict[str, str] | list[dict[str, str]]) -> None:
        if not self.validate(data):
            raise ValueError("Improper log data")
        items = data if isinstance(data, list) else [data]
        for item in items:
            self._store(f"{item.get('log_level', '')}: "
                        f"{item.get('log_message', '')}")


class DataStream:
    def __init__(self) -> None:
        self._processors: list[DataProcessor] = []

    def register_processor(self, proc: DataProcessor) -> None:
        self._processors.append(proc)

    def process_stream(self, stream: list[typing.Any]) -> None:
        for element in stream:
            for proc in self._processors:
                if proc.validate(element):
                    proc.ingest(element)
                    break
            else:
                print("DataStream error - Can't process element in stream: "
                      f"{element}")

    def print_processors_stats(self) -> None:
        print("== DataStream statistics ==")
        if not self._processors:
            print("No processor found, no data")
        for proc in self._processors:
            print(f"{getattr(proc, 'name', 'Processor')}: total "
                  f"{proc.total()} items processed, remaining "
                  f"{proc.remaining()} on processor")


BATCH: list[typing.Any] = [
    "Hello world", [3.14, -1, 2.71],
    [{"log_level": "WARNING", "log_message": "Telnet access! Use ssh instead"},
     {"log_level": "INFO", "log_message": "User wil is connected"}],
    42, ["Hi", "five"]]


def main() -> None:
    print("=== Code Nexus - Data Stream ===")
    print()
    print("Initialize Data Stream...")
    stream = DataStream()
    stream.print_processors_stats()
    print()
    print("Registering Numeric Processor")
    num = NumericProcessor()
    stream.register_processor(num)
    print()
    print(f"Send first batch of data on stream: {BATCH}")
    stream.process_stream(BATCH)
    stream.print_processors_stats()
    print()
    print("Registering other data processors")
    text, log = TextProcessor(), LogProcessor()
    stream.register_processor(text)
    stream.register_processor(log)
    print("Send the same batch again")
    stream.process_stream(BATCH)
    stream.print_processors_stats()
    print()
    print("Consume some elements from the data processors: "
          "Numeric 3, Text 2, Log 1")
    for proc, count in ((num, 3), (text, 2), (log, 1)):
        for _ in range(count):
            proc.output()
    stream.print_processors_stats()


if __name__ == "__main__":
    main()
