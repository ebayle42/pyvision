import random
from typing import Generator

PLAYERS = ["alice", "bob", "charlie", "dylan"]
ACTIONS = ["run", "eat", "sleep", "grab", "move", "climb", "swim", "use",
           "release"]


def gen_event() -> Generator[tuple[str, str], None, None]:
    while True:
        yield (random.choice(PLAYERS), random.choice(ACTIONS))


def consume_event(events: list[tuple[str, str]]
                  ) -> Generator[tuple[str, str], None, None]:
    while len(events) > 0:
        event = random.choice(events)
        events.remove(event)
        yield event


if __name__ == "__main__":
    print("=== Game Data Stream Processor ===")
    stream = gen_event()
    for index in range(100):
        name, action = next(stream)
        print(f"Event {index}: Player {name} did action {action}")
    events = [next(stream) for _ in range(10)]
    print(f"Built list of 10 events: {events}")
    consumer = consume_event(events)
    while len(events) > 0:
        print(f"Got event from list: {next(consumer)}")
        print(f"Remains in list: {events}")
