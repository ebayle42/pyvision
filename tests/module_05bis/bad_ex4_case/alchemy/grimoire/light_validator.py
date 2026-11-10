from .light_spellbook import light_spell_allowed_ingredients


def validate_ingredients(ingredients: str) -> str:
    for allowed in light_spell_allowed_ingredients():
        if allowed in ingredients:
            return f"{ingredients} - VALID"
    return f"{ingredients} - INVALID"
