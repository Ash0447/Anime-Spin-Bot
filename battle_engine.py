import random
from typing import Dict, Any, List

def calculate_dodge(defender: Dict[str, Any]) -> bool:
    stats = defender["stats"]
    dodge_prob = (stats["speed"] * 0.35 + stats["perception"] * 0.25) / 100.0
    dodge_prob = min(0.45, dodge_prob) # 45% Cap
    return random.random() < dodge_prob

def calculate_crit(attacker: Dict[str, Any]) -> bool:
    stats = attacker["stats"]
    crit_prob = 0.05 + (stats["perception"] * 0.002) + (stats["speed"] * 0.001)
    crit_prob = min(0.35, crit_prob) # 35% Cap
    return random.random() < crit_prob

def execute_attack(attacker: Dict[str, Any], defender: Dict[str, Any]) -> Dict[str, Any]:
    a_stats = attacker["stats"]
    d_stats = defender["stats"]
    a_res = attacker["resources"]
    
    # Action Logic based on stamina
    action_type = "normal"
    multiplier = 1.0
    stamina_cost = 5
    ce_cost = 0

    if a_res["stamina"] >= 25 and (a_stats["ultimate_control"] >= 40) and random.random() < 0.25:
        action_type = "ultimate"
        multiplier = 2.0
        stamina_cost = 25
        ce_cost = 35 if attacker["universe"] == "jujutsu_kaisen" else 0
    elif a_res["stamina"] >= 15 and random.random() < 0.40:
        action_type = "technique"
        multiplier = 1.5
        stamina_cost = 15
        ce_cost = 15 if attacker["universe"] == "jujutsu_kaisen" else 0
    elif a_res["stamina"] >= 10 and random.random() < 0.50:
        action_type = "heavy"
        multiplier = 1.3
        stamina_cost = 10
    elif a_res["stamina"] < 5:
        action_type = "exhausted"
        multiplier = 0.6
        stamina_cost = 0
        a_res["stamina"] = min(a_res["max_stamina"], a_res["stamina"] + 10) 

    # Resource Deduction
    a_res["stamina"] = max(0, a_res["stamina"] - stamina_cost)
    if ce_cost > 0 and a_res["cursed_energy"] >= ce_cost:
        a_res["cursed_energy"] -= ce_cost
    elif ce_cost > 0:
        multiplier *= 0.7 

    # Low Stamina Penalties
    stamina_pct = a_res["stamina"] / max(1, a_res["max_stamina"])
    if stamina_pct < 0.15:
        multiplier *= 0.60
    elif stamina_pct < 0.30:
        multiplier *= 0.75

    # Dodge Phase
    if calculate_dodge(defender):
        return {"action": action_type, "damage": 0, "is_crit": False, "dodged": True, "text": f"💨 {defender['loadout']['rank']} dodged!"}

    # Control Multipliers
    tech_ctrl = a_stats["technique_control"] if attacker["universe"] != "demon_slayer" else a_stats["breathing_control"]
    control_mult = 0.5 + (tech_ctrl / 200.0)
    w_ctrl = a_stats["weapon_control"]
    weapon_mult = 0.6 + (w_ctrl / 250.0)

    # Damage Calculation & Variance
    variance = random.uniform(0.85, 1.15)
    raw_damage = (a_stats["strength"] * 0.7 + a_stats["attack"] * 0.8) * multiplier * control_mult * weapon_mult * variance

    # Crit Phase
    is_crit = calculate_crit(attacker)
    if is_crit:
        raw_damage *= 1.5

    # Defense Mitigation
    damage_reduction = min(0.60, d_stats["defense"] / 250.0)
    final_damage = max(5, int(raw_damage * (1.0 - damage_reduction)))

    # Apply HP Loss
    d_stats["hp"] = max(0, d_stats["hp"] - final_damage)

    crit_text = " (CRIT!)" if is_crit else ""
    return {"action": action_type, "damage": final_damage, "is_crit": is_crit, "dodged": False, "text": f"⚔️ {action_type.capitalize()} hit for {final_damage} DMG{crit_text}."}

def process_regeneration(character: Dict[str, Any], opponent: Dict[str, Any]) -> int:
    if "demon_regeneration_suppression" in opponent["effects"]:
        return 0
    rate = character["stats"]["regeneration"]
    if rate <= 0 or character["stats"]["hp"] <= 0:
        return 0
    heal_amount = int(character["stats"]["max_hp"] * (rate / 1000.0))
    character["stats"]["hp"] = min(character["stats"]["max_hp"], character["stats"]["hp"] + heal_amount)
    return heal_amount

def simulate_battle(p1: Dict[str, Any], p2: Dict[str, Any], p1_name: str, p2_name: str) -> List[str]:
    logs = []
    round_count = 1
    max_rounds = 15

    while p1["stats"]["hp"] > 0 and p2["stats"]["hp"] > 0 and round_count <= max_rounds:
        # Initiative
        init_p1 = p1["stats"]["speed"] + random.randint(1, 20)
        init_p2 = p2["stats"]["speed"] + random.randint(1, 20)
        turn_order = [(p1, p2, p1_name, p2_name), (p2, p1, p2_name, p1_name)] if init_p1 >= init_p2 else [(p2, p1, p2_name, p1_name), (p1, p2, p1_name, p2_name)]
        
        for attacker, defender, a_name, d_name in turn_order:
            if attacker["stats"]["hp"] <= 0: continue
            
            result = execute_attack(attacker, defender)
            logs.append(f"<b>{a_name}</b>: {result['text']}")

            healed = process_regeneration(attacker, defender)
            if healed > 0:
                logs.append(f"🩹 <b>{a_name}</b> regenerated +{healed} HP.")

            if defender["stats"]["hp"] <= 0:
                logs.append(f"💀 <b>{d_name}</b> has been defeated!")
                break
        round_count += 1
        
    # Tie breaker if max rounds hit
    if p1["stats"]["hp"] > 0 and p2["stats"]["hp"] > 0:
        if p1["stats"]["hp"] > p2["stats"]["hp"]:
            p2["stats"]["hp"] = 0
            logs.append(f"⏱️ Time limit reached! <b>{p2_name}</b> collapsed from exhaustion.")
        else:
            p1["stats"]["hp"] = 0
            logs.append(f"⏱️ Time limit reached! <b>{p1_name}</b> collapsed from exhaustion.")

    return logs
