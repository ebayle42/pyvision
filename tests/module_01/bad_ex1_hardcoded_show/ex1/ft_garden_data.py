class Plant:
    name: str = ""

    def show(self) -> None:
        if self.name == "Rose":
            print("Rose: 25cm, 30 days old")
        elif self.name == "Sunflower":
            print("Sunflower: 80cm, 45 days old")
        else:
            print("Cactus: 15cm, 120 days old")


if __name__ == "__main__":
    print("=== Garden Plant Registry ===")
    for n in ("Rose", "Sunflower", "Cactus"):
        p = Plant()
        p.name = n
        p.show()
