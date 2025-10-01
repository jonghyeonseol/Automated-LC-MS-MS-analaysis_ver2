"""
Ganglioside Analysis Rules Module
Individual rule files for maintainable, modular analysis
"""

from .rule1_regression import Rule1PrefixRegression
from .rule2_sugar_count import Rule2SugarCount
from .rule3_isomer_classification import Rule3IsomerClassification
from .rule4_oacetylation import Rule4OAcetylation
from .rule5_fragmentation import Rule5Fragmentation

__all__ = [
    "Rule1PrefixRegression",
    "Rule2SugarCount",
    "Rule3IsomerClassification",
    "Rule4OAcetylation",
    "Rule5Fragmentation",
]

# Rule descriptions for documentation
RULE_DESCRIPTIONS = {
    "Rule 1": {
        "name": "Prefix-based Multiple Regression",
        "purpose": "Groups compounds by prefix and performs regression with functional features",
        "features": ["Log P", "Carbon chain", "Unsaturation", "Sugar count", "Modifications"],
        "output": "Valid compounds vs. outliers based on residuals"
    },
    "Rule 2": {
        "name": "Sugar Count Calculation",
        "purpose": "Calculates total sugar count from prefix nomenclature",
        "formula": "total_sugars = sialic_acids + (5 - series_number) + modifications",
        "output": "Sugar composition breakdown for each compound"
    },
    "Rule 3": {
        "name": "Structural Isomer Classification",
        "purpose": "Identifies and classifies structural isomers",
        "isomers": ["GD1a/GD1b", "GM1a/GM1b", "GT1a/GT1b/GT1c", "GQ1b/GQ1c"],
        "output": "Isomer type and species-specific corrections"
    },
    "Rule 4": {
        "name": "O-acetylation Effect Validation",
        "purpose": "Validates that O-acetylation increases retention time",
        "chemistry": "OAc adds hydrophobic character → longer RT",
        "output": "Valid vs. invalid O-acetylated compounds"
    },
    "Rule 5": {
        "name": "In-source Fragmentation Detection",
        "purpose": "Detects and consolidates fragmentation products",
        "criteria": ["Same lipid chain", "Similar RT (±0.1 min)", "Decreasing sugar count"],
        "output": "Parent molecules with consolidated volumes, fragment list"
    }
}


def get_rule_summary() -> str:
    """
    Get a formatted summary of all rules

    Returns:
        Human-readable rule summary
    """
    summary = "📋 GANGLIOSIDE ANALYSIS RULES\n"
    summary += "=" * 70 + "\n\n"

    for rule_num, (rule_name, desc) in enumerate(RULE_DESCRIPTIONS.items(), 1):
        summary += f"{rule_name}: {desc['name']}\n"
        summary += f"Purpose: {desc['purpose']}\n"

        if "features" in desc:
            summary += f"Features: {', '.join(desc['features'])}\n"
        if "formula" in desc:
            summary += f"Formula: {desc['formula']}\n"
        if "isomers" in desc:
            summary += f"Isomers: {', '.join(desc['isomers'])}\n"
        if "chemistry" in desc:
            summary += f"Chemistry: {desc['chemistry']}\n"
        if "criteria" in desc:
            summary += f"Criteria: {', '.join(desc['criteria'])}\n"

        summary += f"Output: {desc['output']}\n"
        summary += "\n"

    return summary


if __name__ == "__main__":
    print(get_rule_summary())
