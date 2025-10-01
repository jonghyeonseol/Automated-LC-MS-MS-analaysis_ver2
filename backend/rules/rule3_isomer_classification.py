"""
Rule 3: Structural Isomer Classification
Identifies and classifies structural isomers based on modifications and biological source
"""

from typing import Any, Dict
import pandas as pd


class Rule3IsomerClassification:
    """
    Rule 3: Structural Isomer Classification

    Purpose:
    - Identifies compounds that can exist as structural isomers
    - Classifies isomers based on sugar modifications:
      * GD1 series: GD1a (+HexNAc) vs GD1b (+dHex)
      * GQ1 series: GQ1b vs GQ1c (species-dependent)
      * GT1 series: GT1a vs GT1b vs GT1c
    - Uses biological source (Porcine/Human/Mouse) for species-specific rules
    """

    def __init__(self):
        """Initialize Rule 3"""

        # Isomer classification rules
        self.isomer_rules = {
            "GD1": {
                "can_have_isomers": True,
                "isomers": {
                    "GD1a": {"modification": "+HexNAc", "description": "N-acetylhexosamine"},
                    "GD1b": {"modification": "+dHex", "description": "Deoxyhexose (fucose)"},
                    "GD1": {"modification": "none", "description": "Base structure"}
                },
                "note": "Differentiated by neutral sugar composition"
            },
            "GQ1": {
                "can_have_isomers": True,
                "isomers": {
                    "GQ1b": {"species": ["Porcine"], "alias": "GQ1bα"},
                    "GQ1c": {"species": ["Human", "Mouse"], "description": "Alternative isomer"}
                },
                "note": "Species-specific isomers"
            },
            "GT1": {
                "can_have_isomers": True,
                "isomers": {
                    "GT1a": {"description": "α-series"},
                    "GT1b": {"description": "β-series (most common)"},
                    "GT1c": {"description": "γ-series"}
                },
                "note": "Sialic acid linkage position"
            },
            "GM1": {
                "can_have_isomers": True,
                "isomers": {
                    "GM1a": {"description": "α-series (common)"},
                    "GM1b": {"description": "β-series"}
                },
                "note": "Sialic acid linkage position"
            }
        }

        print("🧬 Rule 3: Isomer Classification initialized")
        print(f"   - Recognized isomer groups: {list(self.isomer_rules.keys())}")

    def apply(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """
        Apply Rule 3 to classify isomers

        Args:
            df: DataFrame with 'prefix' column
            data_type: Biological source (Porcine/Human/Mouse)

        Returns:
            Dictionary containing isomer classification for each compound
        """
        print(f"\n🧬 Applying Rule 3: Isomer Classification (Data type: {data_type})")

        isomer_classification = {}
        isomer_corrections = {}
        isomer_candidates = 0

        for _, row in df.iterrows():
            compound_name = row["Name"]
            prefix = row["prefix"]

            # Classify isomer
            isomer_info = self.classify_isomer(prefix, data_type)
            isomer_classification[compound_name] = isomer_info

            if isomer_info["can_have_isomers"]:
                isomer_candidates += 1

            # Apply corrections if needed
            if isomer_info["corrected_name"] != prefix:
                isomer_corrections[compound_name] = {
                    "original": prefix,
                    "corrected": isomer_info["corrected_name"],
                    "reason": isomer_info["correction_reason"]
                }

        print(f"✅ Rule 3 complete:")
        print(f"   - Total compounds: {len(isomer_classification)}")
        print(f"   - Isomer candidates: {isomer_candidates}")
        print(f"   - Corrections applied: {len(isomer_corrections)}")

        return {
            "isomer_classification": isomer_classification,
            "isomer_corrections": isomer_corrections,
            "statistics": {
                "total_compounds": len(isomer_classification),
                "isomer_candidates": isomer_candidates,
                "corrections_applied": len(isomer_corrections)
            }
        }

    def classify_isomer(self, prefix: str, data_type: str) -> Dict[str, Any]:
        """
        Classify a compound as an isomer

        Args:
            prefix: Compound prefix (e.g., "GD1", "GD1+dHex")
            data_type: Biological source

        Returns:
            Dictionary with isomer classification details
        """
        # Extract base prefix (first 3 characters)
        base_prefix = prefix[:3] if len(prefix) >= 3 else prefix

        # Check if this compound can have isomers
        if base_prefix not in self.isomer_rules:
            return {
                "base_prefix": base_prefix,
                "can_have_isomers": False,
                "isomer_type": None,
                "corrected_name": prefix,
                "correction_reason": None,
                "species_specific": False
            }

        isomer_info = self.isomer_rules[base_prefix]

        # Determine specific isomer type
        isomer_type = self._determine_isomer_type(prefix, base_prefix, data_type, isomer_info)

        # Check if correction is needed
        corrected_name = prefix
        correction_reason = None

        if base_prefix == "GD1":
            if "+HexNAc" in prefix and not prefix.startswith("GD1a"):
                corrected_name = prefix.replace("GD1", "GD1a")
                correction_reason = "HexNAc modification indicates GD1a"
            elif "+dHex" in prefix and not prefix.startswith("GD1b"):
                corrected_name = prefix.replace("GD1", "GD1b")
                correction_reason = "dHex modification indicates GD1b"

        elif base_prefix == "GQ1" and data_type == "Porcine":
            if prefix.startswith("GQ1b") and "GQ1bα" not in prefix:
                corrected_name = prefix.replace("GQ1b", "GQ1bα")
                correction_reason = "Porcine-specific GQ1bα nomenclature"

        return {
            "base_prefix": base_prefix,
            "can_have_isomers": True,
            "isomer_type": isomer_type,
            "corrected_name": corrected_name,
            "correction_reason": correction_reason,
            "species_specific": base_prefix == "GQ1",
            "isomer_info": isomer_info["note"]
        }

    def _determine_isomer_type(
        self, prefix: str, base_prefix: str, data_type: str, isomer_info: Dict
    ) -> str:
        """
        Determine the specific isomer type based on modifications

        Args:
            prefix: Full prefix
            base_prefix: Base prefix (first 3 chars)
            data_type: Biological source
            isomer_info: Isomer rules for this base

        Returns:
            Isomer type string (e.g., "GD1a", "GD1b", "GQ1bα")
        """
        # GD1 series: Check for modifications
        if base_prefix == "GD1":
            if "+HexNAc" in prefix:
                return "GD1a"
            elif "+dHex" in prefix:
                return "GD1b"
            else:
                return "GD1"  # Base structure, may need RT-based classification

        # GQ1 series: Species-dependent
        elif base_prefix == "GQ1":
            if data_type == "Porcine":
                return "GQ1bα"  # Porcine-specific
            else:
                return "GQ1c"  # Other species

        # For other isomers (GM1, GT1), can't distinguish without RT analysis
        else:
            return base_prefix


    def get_isomer_summary(self) -> str:
        """
        Get a human-readable summary of isomer classification rules

        Returns:
            Formatted summary string
        """
        summary = "🧬 ISOMER CLASSIFICATION RULES\n"
        summary += "=" * 50 + "\n\n"

        for base, rules in self.isomer_rules.items():
            summary += f"📊 {base} Series:\n"
            summary += f"   Can have isomers: {rules['can_have_isomers']}\n"
            summary += f"   Note: {rules['note']}\n"

            if "isomers" in rules:
                summary += "   Isomers:\n"
                for isomer_name, isomer_data in rules["isomers"].items():
                    summary += f"   - {isomer_name}: "
                    if "modification" in isomer_data:
                        summary += f"{isomer_data['modification']}"
                    if "description" in isomer_data:
                        summary += f" ({isomer_data['description']})"
                    if "species" in isomer_data:
                        summary += f" [Species: {', '.join(isomer_data['species'])}]"
                    summary += "\n"

            summary += "\n"

        return summary
