from abc import ABC, abstractmethod


class Creature(ABC):
    def __init__(self, name: str, kind: str) -> None:
        self._name = name
        self._kind = kind

    @abstractmethod
    def attack(self) -> str:
        pass

    def get_name(self) -> str:
        return self._name

    def describe(self) -> str:
        return f"{self._name} is a {self._kind} type Creature"


class TransformCapability(Creature):
    def __init__(self, name: str, kind: str) -> None:
        super().__init__(name, kind)
        self._transformed = False

    @abstractmethod
    def transform(self) -> str:
        pass

    @abstractmethod
    def revert(self) -> str:
        pass
