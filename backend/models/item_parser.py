"""
Parse CS2 item names into structured fields for feature engineering.

Examples:
    AK-47 | Redline (Field-Tested)
    StatTrak™ M4A4 | Desolate (Factory New)
    ★ Bayonet | Doppler (Factory New)
    Sticker | s1mple (Holo) | Paris 2024
    Souvenir AWP | Safari Mesh (Battle-Scarred)
    Glove Case
    Special Agent Ava | FBI
    Music Kit | PVRIS, Evergreen
    Sealed Graffiti | X-Axes (Blood Red)
    Charm | Gritty
"""

import re

QUALITY_RANK = {
    "Factory New": 5,
    "Minimal Wear": 4,
    "Field-Tested": 3,
    "Well-Worn": 2,
    "Battle-Scarred": 1,
    "FN": 5,
    "MW": 4,
    "FT": 3,
    "WW": 2,
    "BS": 1,
}

QUALITY_CANONICAL = {
    "Factory New": "Factory New",
    "FN": "Factory New",
    "Minimal Wear": "Minimal Wear",
    "MW": "Minimal Wear",
    "Field-Tested": "Field-Tested",
    "FT": "Field-Tested",
    "Well-Worn": "Well-Worn",
    "WW": "Well-Worn",
    "Battle-Scarred": "Battle-Scarred",
    "BS": "Battle-Scarred",
}


def parse_item_name(name: str) -> dict:
    """Parse a CS2 item name into structured identity fields.

    Returns a dict with keys: weapon, skin_name, quality, quality_rank,
    is_stattrak, is_souvenir, is_knife, is_glove, is_sticker, is_case,
    is_capsule, is_agent, is_music_kit, is_graffiti, is_charm, is_patch.
    """
    result = {
        "weapon": None,
        "skin_name": None,
        "quality": None,
        "quality_rank": 0,
        "is_stattrak": False,
        "is_souvenir": False,
        "is_knife": False,
        "is_glove": False,
        "is_sticker": False,
        "is_case": False,
        "is_capsule": False,
        "is_agent": False,
        "is_music_kit": False,
        "is_graffiti": False,
        "is_charm": False,
        "is_patch": False,
    }

    if not name or not isinstance(name, str):
        return result

    # StatTrak / Souvenir prefix detection
    if "StatTrak" in name or name.startswith("StatTrak\u2122"):
        result["is_stattrak"] = True
    if name.startswith("Souvenir"):
        result["is_souvenir"] = True

    # ★ prefix → knife or glove
    if name.startswith("\u2605"):
        is_glove = "Glove" in name or "Gloves" in name
        result["is_knife"] = not is_glove
        result["is_glove"] = is_glove

    # Category prefixes — use "in name" rather than startswith to handle
    # cases like "StatTrak™ Music Kit | ...", "Sticker Slab | ..." etc.
    if name.startswith("Sticker |") or name.startswith("Sticker Slab |"):
        result["is_sticker"] = True
    elif "|" in name and "Music Kit" in name and name.index("Music Kit") < name.index("|"):
        result["is_music_kit"] = True
    elif name.startswith("Sealed Graffiti |"):
        result["is_graffiti"] = True
    elif name.startswith("Agent |") or name.startswith("Special Agent"):
        result["is_agent"] = True
    elif name.startswith("Charm |"):
        result["is_charm"] = True
    elif "Patch" in name and ("Patch Pack" in name or name.startswith("Patch |")):
        result["is_patch"] = True

    # Case / Capsule detection (must check after category prefixes)
    if name.endswith("Case") and not result["is_patch"]:
        result["is_case"] = True
    if name.endswith("Capsule"):
        result["is_capsule"] = True

    # Quality extraction from parenthetical suffix
    quality_match = re.search(r"\(([^)]+)\)\s*$", name)
    if quality_match:
        raw_quality = quality_match.group(1).strip()
        result["quality"] = QUALITY_CANONICAL.get(raw_quality, raw_quality)
        result["quality_rank"] = QUALITY_RANK.get(raw_quality, 0)

    # Weapon & skin name extraction (only for skin-type items)
    if not any([
        result["is_sticker"], result["is_music_kit"],
        result["is_graffiti"], result["is_agent"], result["is_charm"],
    ]):
        clean = name
        if result["is_souvenir"]:
            clean = re.sub(r"^Souvenir\s+", "", clean)
        clean = re.sub(r"^StatTrak\u2122\s*", "", clean)
        clean = re.sub(r"^\u2605\s*", "", clean)

        if "|" in clean:
            parts = [p.strip() for p in clean.split("|")]
            if len(parts) >= 2:
                result["weapon"] = parts[0]
                skin_part = parts[1]
                skin_match = re.match(r"^(.+?)\s*\([^)]+\)\s*$", skin_part)
                if skin_match:
                    result["skin_name"] = skin_match.group(1).strip()
                else:
                    result["skin_name"] = skin_part

    return result
