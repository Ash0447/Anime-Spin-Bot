import json
import random
from typing import Dict, Any

def load_universes(path: str = "universes.json") -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Handle the {"universes": {...}} wrapper if it exists
        return data.get("universes", data)
    except FileNotFoundError:
        print(f"Error: Could not find {path}")
        return {}

def weighted_spin(options: list) -> Dict[str, Any]:
    weights = [item.get("weight", 1) for item in options]
    return random.choices(options, weights=weights, k=1)[0]

def build_character(universe_data: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Spin Faction
    faction_opts = universe_data["faction_spin"]["options"]
    faction_choice = weighted_spin(faction_opts)
    faction_id = faction_choice["id"]
    
    # 2. Retrieve sequence and faction definitions
    sequence_key = f"{faction_id}_sequence"
    spin_sequence = universe_data.get(sequence_key, [])
    faction_pool = universe_data.get(faction_id, {})
    
    selections = {}
    collected_effects = set()
    
    # Map sequence names to faction pool keys in your JSON
    key_mapping = {
        "rank": "ranks",
        "weapon": "weapons",
        "cursed_tool": "cursed_tools",
        "breathing_style": "breathing_styles",
        "blood_demon_art": "blood_demon_arts",
        "cursed_technique": "cursed_techniques",
        "ultimate": "ultimate",
        "regeneration": "regeneration"
    }

    # 3. Spin through the exact sequence
    for step in spin_sequence:
        pool_key = key_mapping.get(step, step)
        available_options = faction_pool.get(pool_key, [])
        if available_options:
            selected_item = weighted_spin(available_options)
            selections[step] = selected_item
            for eff in selected_item.get("effects", []):
                collected_effects.add(eff)

    # 4. Extract Components safely
    rank = selections.get("rank", {})
    weapon = selections.get("weapon") or selections.get("cursed_tool", {})
    technique = (
        selections.get("breathing_style") or 
        selections.get("blood_demon_art") or 
        selections.get("cursed_technique", {})
    )
    ultimate = selections.get("ultimate", {})
    regen_item = selections.get("regeneration", {})

    r_stats = rank.get("stats", {})
    w_stats = weapon.get("stats", {})
    t_stats = technique.get("stats", {})
    u_stats = ultimate.get("stats", {})
    reg_stats = regen_item.get("stats", {})

    # 5. Core Stat Merging & Caps
    base_str = r_stats.get("strength", 20)
    base_spd = r_stats.get("speed", 20)
    base_def = r_stats.get("defense", 20)
    base_sta = r_stats.get("stamina", 30)

    final_strength = min(100, int(base_str + u_stats.get("strength_bonus", 0) + u_stats.get("strength", 0)))
    final_speed = min(100, int(base_spd + (w_stats.get("speed", 0) * 0.15) + (t_stats.get("speed", 0) * 0.15) + u_stats.get("speed_bonus", 0)))
    final_defense = min(100, int(base_def + (w_stats.get("defense", 0) * 0.15) + (t_stats.get("defense", 0) * 0.15) + u_stats.get("defense_bonus", 0)))
    final_stamina = min(100, int(base_sta + (t_stats.get("stamina", 0) * 0.20)))

    # Control Stats
    weapon_ctrl = max(r_stats.get("weapon_control", 20), w_stats.get("weapon_control", w_stats.get("tool_control", 20)))
    technique_ctrl = max(r_stats.get("technique_control", 20), t_stats.get("control", 20))
    breathing_ctrl = max(r_stats.get("breathing_control", 20), t_stats.get("breathing_control", 20))
    ultimate_ctrl = max(r_stats.get("ultimate_control", 10), u_stats.get("ultimate_control", 10))
    domain_ctrl = max(r_stats.get("domain_control", 0), u_stats.get("domain_control", 0))

    # Special Attributes
    perception = max(r_stats.get("perception", 20), u_stats.get("perception_bonus", 0), u_stats.get("perception", 0))
    regeneration_rate = max(r_stats.get("regeneration", 0), reg_stats.get("regeneration_rate", 0), u_stats.get("regeneration", 0))
    cursed_energy = r_stats.get("cursed_energy", 0)

    # HP Calculation Formula: 100 + (Defense * 4) + (Stamina * 5)
    max_hp = 100 + (final_defense * 4) + (final_stamina * 5)

    # Combat Rating
    raw_attack = w_stats.get("attack", t_stats.get("attack", 50))
    avg_control = (weapon_ctrl + technique_ctrl + breathing_ctrl + ultimate_ctrl) / 4
    combat_rating = round(
        final_strength * 0.20 +
        final_speed * 0.15 +
        final_defense * 0.15 +
        final_stamina * 0.10 +
        raw_attack * 0.15 +
        avg_control * 0.15 +
        perception * 0.10, 
        1
    )

    return {
        "universe": universe_data["id"],
        "faction": faction_id,
        "loadout": {
            "rank": rank.get("name", "Unknown"),
            "weapon": weapon.get("name", "None"),
            "technique": technique.get("name", "None"),
            "ultimate": ultimate.get("name", "None"),
            "regeneration": regen_item.get("name", "None") if regen_item else "None"
        },
        "stats": {
            "hp": max_hp,
            "max_hp": max_hp,
            "strength": final_strength,
            "speed": final_speed,
            "defense": final_defense,
            "stamina": final_stamina,
            "attack": raw_attack,
            "weapon_control": weapon_ctrl,
            "breathing_control": breathing_ctrl,
            "technique_control": technique_ctrl,
            "ultimate_control": ultimate_ctrl,
            "domain_control": domain_ctrl,
            "perception": perception,
            "regeneration": regeneration_rate
        },
        "resources": {
            "stamina": final_stamina,
            "max_stamina": final_stamina,
            "cursed_energy": cursed_energy,
            "max_cursed_energy": cursed_energy
        },
        "effects": list(collected_effects),
        "combat_rating": combat_rating
    }
