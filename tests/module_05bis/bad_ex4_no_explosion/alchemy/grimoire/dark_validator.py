def dark_validate_ingredients(ingredients: str) -> str:
    lowered = ingredients.lower()
    for allowed in ("bats", "frogs", "arsenic", "eyeball"):
        if allowed in lowered:
            return f"{ingredients} - VALID"
    return f"{ingredients} - INVALID"
