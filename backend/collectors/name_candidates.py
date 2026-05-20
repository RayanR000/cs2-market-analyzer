"""
Helpers for building marketplace-style item name candidates.
"""

from typing import List, Optional

CS2_CONDITIONS = [
    "Factory New",
    "Minimal Wear",
    "Field-Tested",
    "Well-Worn",
    "Battle-Scarred",
]


def build_marketplace_name_candidates(item_name: str, item_type: Optional[str] = None) -> List[str]:
    """
    Build likely market hash names for an item.

    This keeps the matching logic generic so collectors can use it without
    hard-coding a specific marketplace.
    """
    candidates: List[str] = []

    def add(candidate: str) -> None:
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    add(item_name)

    is_skin = (item_type or "").lower() == "skin"
    has_pipe = " | " in item_name

    if is_skin and not has_pipe:
        parts = item_name.split(" ", 1)
        if len(parts) == 2:
            weapon, skin = parts
            pipe_name = f"{weapon} | {skin}"
            add(pipe_name)
            for condition in CS2_CONDITIONS:
                add(f"{pipe_name} ({condition})")
                add(f"{item_name} ({condition})")
    elif is_skin and has_pipe:
        for condition in CS2_CONDITIONS:
            add(f"{item_name} ({condition})")
        weapon, skin = item_name.split(" | ", 1)
        add(f"{weapon} {skin}")

    return candidates
