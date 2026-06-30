import sys

# Define Fuzzy Sets using X/Y coordinates (handles trimf, trapmf, and shoulders automatically)
Server_Temp_Sets = {
    "Low": {"X": [10, 25, 40], "Y": [1, 1, 0]},     # Left-shoulder Trapmf
    "Medium": {"X": [25, 45, 65], "Y": [0, 1, 0]},  # Trimf
    "High": {"X": [50, 70, 90], "Y": [0, 1, 1]}     # Right-shoulder Trapmf
}

Workload_Sets = {
    "Light": {"X": [0, 25, 50], "Y": [1, 1, 0]},
    "Moderate": {"X": [25, 50, 75], "Y": [0, 1, 0]},
    "Heavy": {"X": [50, 75, 100], "Y": [0, 1, 1]}
}

Ambient_Temp_Sets = {
    "Cool": {"X": [10, 18, 25], "Y": [1, 1, 0]},
    "Normal": {"X": [18, 25, 32], "Y": [0, 1, 0]},
    "Hot": {"X": [25, 32, 45], "Y": [0, 1, 1]}
}

Cooling_Sets = {
    "Low": {"X": [0, 15, 30], "Y": [1, 1, 0]},
    "Medium": {"X": [20, 40, 60], "Y": [0, 1, 0]},
    "High": {"X": [50, 67.5, 85], "Y": [0, 1, 0]},
    "Maximum": {"X": [75, 85, 100], "Y": [0, 1, 1]}
}

def interpolate(x, x_coords, y_coords):
    if x <= x_coords[0]: return y_coords[0]
    if x >= x_coords[-1]: return y_coords[-1]
    for i in range(len(x_coords) - 1):
        if x_coords[i] <= x <= x_coords[i+1]:
            x1, x2 = x_coords[i], x_coords[i+1]
            y1, y2 = y_coords[i], y_coords[i+1]
            if x1 == x2: return y1
            return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
    return 0.0

def fuzzify(value, sets):
    memberships = {}
    for label, params in sets.items():
        memberships[label] = interpolate(value, params["X"], params["Y"])
    return memberships

# Return the exact 27 rules defined in FuzzyLogicRules.md
def generate_rules():
    return [
        {"if": {"Temp": "Low", "Workload": "Light", "Ambient": "Cool"}, "then": "Low"},
        {"if": {"Temp": "Low", "Workload": "Light", "Ambient": "Normal"}, "then": "Low"},
        {"if": {"Temp": "Low", "Workload": "Light", "Ambient": "Hot"}, "then": "Low"},
        {"if": {"Temp": "Low", "Workload": "Moderate", "Ambient": "Cool"}, "then": "Low"},
        {"if": {"Temp": "Low", "Workload": "Moderate", "Ambient": "Normal"}, "then": "Low"},
        {"if": {"Temp": "Low", "Workload": "Moderate", "Ambient": "Hot"}, "then": "Medium"},
        {"if": {"Temp": "Low", "Workload": "Heavy", "Ambient": "Cool"}, "then": "Medium"},
        {"if": {"Temp": "Low", "Workload": "Heavy", "Ambient": "Normal"}, "then": "Medium"},
        {"if": {"Temp": "Low", "Workload": "Heavy", "Ambient": "Hot"}, "then": "High"},
        
        {"if": {"Temp": "Medium", "Workload": "Light", "Ambient": "Cool"}, "then": "Low"},
        {"if": {"Temp": "Medium", "Workload": "Light", "Ambient": "Normal"}, "then": "Medium"},
        {"if": {"Temp": "Medium", "Workload": "Light", "Ambient": "Hot"}, "then": "Medium"},
        {"if": {"Temp": "Medium", "Workload": "Moderate", "Ambient": "Cool"}, "then": "Medium"},
        {"if": {"Temp": "Medium", "Workload": "Moderate", "Ambient": "Normal"}, "then": "Medium"},
        {"if": {"Temp": "Medium", "Workload": "Moderate", "Ambient": "Hot"}, "then": "High"},
        {"if": {"Temp": "Medium", "Workload": "Heavy", "Ambient": "Cool"}, "then": "Medium"},
        {"if": {"Temp": "Medium", "Workload": "Heavy", "Ambient": "Normal"}, "then": "High"},
        {"if": {"Temp": "Medium", "Workload": "Heavy", "Ambient": "Hot"}, "then": "High"},
        
        {"if": {"Temp": "High", "Workload": "Light", "Ambient": "Cool"}, "then": "High"},
        {"if": {"Temp": "High", "Workload": "Light", "Ambient": "Normal"}, "then": "High"},
        {"if": {"Temp": "High", "Workload": "Light", "Ambient": "Hot"}, "then": "High"},
        {"if": {"Temp": "High", "Workload": "Moderate", "Ambient": "Cool"}, "then": "High"},
        {"if": {"Temp": "High", "Workload": "Moderate", "Ambient": "Normal"}, "then": "High"},
        {"if": {"Temp": "High", "Workload": "Moderate", "Ambient": "Hot"}, "then": "Maximum"},
        {"if": {"Temp": "High", "Workload": "Heavy", "Ambient": "Cool"}, "then": "Maximum"},
        {"if": {"Temp": "High", "Workload": "Heavy", "Ambient": "Normal"}, "then": "Maximum"},
        {"if": {"Temp": "High", "Workload": "Heavy", "Ambient": "Hot"}, "then": "Maximum"}
    ]

RULES = generate_rules()

def evaluate_rules(mem_temp, mem_workload, mem_ambient):
    rule_strengths = {"Low": [], "Medium": [], "High": [], "Maximum": []}
    for rule in RULES:
        strength = min(
            mem_temp[rule["if"]["Temp"]],
            mem_workload[rule["if"]["Workload"]],
            mem_ambient[rule["if"]["Ambient"]]
        )
        if strength > 0:
            rule_strengths[rule["then"]].append(strength)
    
    aggregated = {}
    for output_label, strengths in rule_strengths.items():
        aggregated[output_label] = max(strengths) if strengths else 0.0
    return aggregated

def defuzzify(aggregated_outputs):
    numerator = 0.0
    denominator = 0.0
    for x in range(1, 101):
        low_val = interpolate(x, Cooling_Sets["Low"]["X"], Cooling_Sets["Low"]["Y"])
        med_val = interpolate(x, Cooling_Sets["Medium"]["X"], Cooling_Sets["Medium"]["Y"])
        high_val = interpolate(x, Cooling_Sets["High"]["X"], Cooling_Sets["High"]["Y"])
        max_val = interpolate(x, Cooling_Sets["Maximum"]["X"], Cooling_Sets["Maximum"]["Y"])
        
        low_clipped = min(aggregated_outputs.get("Low", 0.0), low_val)
        med_clipped = min(aggregated_outputs.get("Medium", 0.0), med_val)
        high_clipped = min(aggregated_outputs.get("High", 0.0), high_val)
        max_clipped = min(aggregated_outputs.get("Maximum", 0.0), max_val)
        
        agg_y = max(low_clipped, med_clipped, high_clipped, max_clipped)
        
        numerator += agg_y * x
        denominator += agg_y
        
    return numerator / denominator if denominator != 0 else 0.0

if __name__ == "__main__":
    print("=" * 60)
    print("🧠 DATA CENTER FUZZY LOGIC CONTROLLER CLI UTILITY")
    print("=" * 60)
    
    def get_input(prompt, min_val, max_val):
        while True:
            try:
                val = float(input(f"{prompt} (range: {min_val} to {max_val}): "))
                if min_val <= val <= max_val:
                    return val
                else:
                    print(f"⚠️ Value must be between {min_val} and {max_val}. Try again.")
            except ValueError:
                print("⚠️ Invalid number. Please enter a valid decimal number.")

    temp_in = get_input("🌡️ Enter Server Temperature (°C)", 10.0, 90.0)
    work_in = get_input("⚙️ Enter CPU Workload (%)", 0.0, 100.0)
    amb_in = get_input("❄️ Enter Room Ambient Temperature (°C)", 10.0, 45.0)
    
    print("\n" + "-" * 30 + " EVALUATION " + "-" * 30)
    
    # Fuzzification
    mem_temp = fuzzify(temp_in, Server_Temp_Sets)
    mem_work = fuzzify(work_in, Workload_Sets)
    mem_amb = fuzzify(amb_in, Ambient_Temp_Sets)
    
    print(f"\n📈 Fuzzification Results:")
    print(f"  * Server Temperature: " + ", ".join([f"{k} = {v:.3f}" for k, v in mem_temp.items()]))
    print(f"  * CPU Workload:       " + ", ".join([f"{k} = {v:.3f}" for k, v in mem_work.items()]))
    print(f"  * Room Ambient Temp:  " + ", ".join([f"{k} = {v:.3f}" for k, v in mem_amb.items()]))
    
    # Rules firing
    print(f"\n📜 Fired Rules (Mamdani Min-Clip):")
    fired_any = False
    for idx, rule in enumerate(RULES, start=1):
        strength = min(
            mem_temp[rule["if"]["Temp"]],
            mem_work[rule["if"]["Workload"]],
            mem_amb[rule["if"]["Ambient"]]
        )
        if strength > 0:
            print(f"  * [Rule #{idx:02d}] IF Temp is {rule['if']['Temp']} ({mem_temp[rule['if']['Temp']]:.2f}) "
                  f"AND Workload is {rule['if']['Workload']} ({mem_work[rule['if']['Workload']]:.2f}) "
                  f"AND Ambient is {rule['if']['Ambient']} ({mem_amb[rule['if']['Ambient']]:.2f}) "
                  f"-> THEN Cooling is {rule['then']} (Fired Strength: {strength:.3f})")
            fired_any = True
    
    if not fired_any:
        print("  * No rules fired with strength > 0.")
        
    # Aggregation & Defuzzification
    agg_rules = evaluate_rules(mem_temp, mem_work, mem_amb)
    print(f"\n🗳️ Aggregated Set Strengths: " + ", ".join([f"{k} = {v:.3f}" for k, v in agg_rules.items()]))
    
    cooling_output = defuzzify(agg_rules)
    print(f"\n🎯 CALCULATED OUTCOME:")
    print(f"  👉 Cooling Power Utilized: {cooling_output:.2f}%")
    print("=" * 60)
