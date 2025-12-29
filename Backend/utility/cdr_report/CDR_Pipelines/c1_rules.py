# rules.py

# ==================== PROMPTS ====================
SYSTEM_PROMPT = """
You are a senior electrical safety engineer.
Classify components conservatively.
If uncertain, mark as CRITICAL with lower confidence.
"""

USER_PROMPT = """
Below is a list of components. For EACH item, determine whether it is CRITICAL.

Rules:
1. Required by standard or controlling document
2. Located in safety circuitry
3. Located in hazardous circuitry
4. Encloses or prevents access to hazardous circuitry
5. Used to maintain spacings or segregation
6. Special evaluation performed
7. Relied upon for safe abnormal operation
8. Other hazard may occur if item is changed or deleted

Return STRICT JSON ARRAY in SAME ORDER:

[
  {{
    "row_id": "<row_id>",
    "is_critical": true | false,
    "triggered_rules": [1,4,7],
    "confidence_score": 0.0-1.0,
    "reasoning": "short technical justification"
  }}
]

Components:
{components_json}
"""

# ==================== LOGIC FUNCTIONS ====================
def confidence_level(score):
    score = float(score)
    if score >= 0.8:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"

def visual_confidence_from_distance(d, applicability):
    if applicability == "Direct" and d < 0.30:
        return "Visual support present"
    if applicability == "Indirect" and d < 0.22:
        return "Visual context only"
    return "No visual evidence"

def visual_applicability(component_name, description):
    text = f"{component_name} {description}".lower()

    if any(k in text for k in [
        "enclosure", "housing", "cabinet", "cover", "case",
        "fan", "vent", "ventilation",
        "label", "marking", "nameplate",
        "power inlet", "ac inlet", "connector",
        "earth", "ground", "protective earth"
    ]):
        return "Direct"

    if any(k in text for k in [
        "fuse", "transformer", "power supply",
        "relay", "switch", "terminal"
    ]):
        return "Indirect"

    return "Not applicable"