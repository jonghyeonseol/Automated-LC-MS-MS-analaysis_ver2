"""
Rule 2: Sugar Count Calculation
Calculates total sugar count from ganglioside prefix nomenclature
"""

from typing import Any, Dict
import pandas as pd


class Rule2SugarCount:
    """
    Rule 2: Sugar Count Calculation

    Purpose:
    - Calculates total sugar count from prefix nomenclature
    - Ganglioside naming: G[d][e][f]
      - d: Always 'G' for ganglioside
      - e: Sialic acid count (A=0, M=1, D=2, T=3, Q=4, P=5)
      - f: Series number (1-4), where total neutral sugars = 5 - f
    - Example: GM1 = G + M(1 sialic) + 1 → 1 + (5-1) = 5 total sugars
    - Accounts for additional modifications (+dHex, +HexNAc, etc.)
    """

    def __init__(self):
        """Initialize Rule 2"""

        # e-component mapping (sialic acid count)
        self.sialic_acid_mapping = {
            "A": 0,  # Asialo (no sialic acid)
            "M": 1,  # Monosialic
            "D": 2,  # Disialic
            "T": 3,  # Trisialic
            "Q": 4,  # Quadrasialic
            "P": 5   # Pentasialic
        }

        # Additional sugar modifications
        self.modification_sugars = {
            "dHex": 1,    # Deoxyhexose (fucose)
            "HexNAc": 1,  # N-acetylhexosamine
            "Hex": 1,     # Hexose
            "NeuAc": 1,   # N-acetylneuraminic acid
            "NeuGc": 1    # N-glycolylneuraminic acid
        }

        print("🧬 Rule 2: Sugar Count Calculation initialized")
        print(f"   - Sialic acid types: {list(self.sialic_acid_mapping.keys())}")
        print(f"   - Recognized modifications: {list(self.modification_sugars.keys())}")

    def apply(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Apply Rule 2 to calculate sugar counts

        Args:
            df: DataFrame with 'prefix' column

        Returns:
            Dictionary containing sugar analysis for each compound
        """
        print("\n🧬 Applying Rule 2: Sugar Count Calculation")

        sugar_analysis = {}

        for _, row in df.iterrows():
            compound_name = row["Name"]
            prefix = row["prefix"]

            sugar_info = self.calculate_sugar_count(prefix)
            sugar_analysis[compound_name] = sugar_info

        print(f"✅ Rule 2 complete: Analyzed {len(sugar_analysis)} compounds")

        # Calculate statistics
        total_sugars = [info["total_sugars"] for info in sugar_analysis.values()]
        avg_sugars = sum(total_sugars) / len(total_sugars) if total_sugars else 0

        print(f"   - Average sugar count: {avg_sugars:.1f}")
        print(f"   - Sugar count range: {min(total_sugars) if total_sugars else 0} - {max(total_sugars) if total_sugars else 0}")

        return {
            "sugar_analysis": sugar_analysis,
            "statistics": {
                "total_compounds": len(sugar_analysis),
                "average_sugars": avg_sugars,
                "min_sugars": min(total_sugars) if total_sugars else 0,
                "max_sugars": max(total_sugars) if total_sugars else 0
            }
        }

    def calculate_sugar_count(self, prefix: str) -> Dict[str, Any]:
        """
        Calculate sugar count from prefix

        Args:
            prefix: Ganglioside prefix (e.g., "GM1", "GD1+dHex", "GT1+OAc")

        Returns:
            Dictionary with detailed sugar breakdown:
            - d_component: 'G' for ganglioside
            - e_component: Sialic acid count
            - f_component: Series number
            - neutral_sugars: 5 - f
            - additional_sugars: From modifications
            - total_sugars: e + (5-f) + additional
        """
        if len(prefix) < 3:
            return {
                "d_component": None,
                "e_component": 0,
                "f_component": 0,
                "neutral_sugars": 0,
                "sialic_acids": 0,
                "additional_sugars": 0,
                "modifications": [],
                "total_sugars": 0,
                "formula": "Invalid prefix"
            }

        # Extract d, e, f from first 3 characters
        d_char = prefix[0]  # Should be 'G'
        e_char = prefix[1]  # Sialic acid (M/D/T/Q/P)
        f_char = prefix[2]  # Series number (1/2/3/4)

        # Calculate sialic acid count (e-component)
        sialic_acids = self.sialic_acid_mapping.get(e_char, 0)

        # Calculate neutral sugars (f-component)
        try:
            f_num = int(f_char)
            neutral_sugars = 5 - f_num
        except (ValueError, TypeError):
            f_num = 0
            neutral_sugars = 0

        # Check for additional modifications
        modifications = []
        additional_sugars = 0

        for mod_name, sugar_count in self.modification_sugars.items():
            if f"+{mod_name}" in prefix:
                modifications.append(mod_name)
                additional_sugars += sugar_count
            # Check for multiple (e.g., +2OAc)
            elif f"+2{mod_name}" in prefix:
                modifications.append(f"2{mod_name}")
                additional_sugars += 2 * sugar_count

        # Total sugar count
        total_sugars = sialic_acids + neutral_sugars + additional_sugars

        # Generate formula
        formula_parts = []
        if sialic_acids > 0:
            formula_parts.append(f"{sialic_acids} sialic acid{'s' if sialic_acids > 1 else ''}")
        if neutral_sugars > 0:
            formula_parts.append(f"{neutral_sugars} neutral sugar{'s' if neutral_sugars > 1 else ''}")
        if additional_sugars > 0:
            formula_parts.append(f"{additional_sugars} additional")

        formula = f"{total_sugars} = {' + '.join(formula_parts)}" if formula_parts else "0"

        return {
            "d_component": d_char,
            "e_component": sialic_acids,
            "f_component": f_num,
            "neutral_sugars": neutral_sugars,
            "sialic_acids": sialic_acids,
            "additional_sugars": additional_sugars,
            "modifications": modifications,
            "total_sugars": total_sugars,
            "formula": formula
        }
