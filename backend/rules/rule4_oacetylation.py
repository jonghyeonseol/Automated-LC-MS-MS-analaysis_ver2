"""
Rule 4: O-acetylation Effect Validation
Validates that O-acetylation increases retention time as expected
"""

from typing import Any, Dict, List
import pandas as pd


class Rule4OAcetylation:
    """
    Rule 4: O-acetylation Effect Validation

    Purpose:
    - Validates chemical behavior of O-acetylation
    - O-acetyl groups add hydrophobic character → increases RT
    - Compares OAc-modified compounds to their base structures
    - Flags compounds where OAc decreases RT (unexpected behavior)

    Chemistry:
    - O-acetylation: Addition of -COCH₃ group to hydroxyl (-OH)
    - Increases lipophilicity → Longer retention time
    - Expected: RT(compound+OAc) > RT(compound)
    """

    def __init__(self, min_rt_increase: float = 0.0):
        """
        Initialize Rule 4

        Args:
            min_rt_increase: Minimum expected RT increase (minutes)
                            0.0 = any increase is valid
        """
        self.min_rt_increase = min_rt_increase

        print("⚗️ Rule 4: O-acetylation Validation initialized")
        print(f"   - Min RT increase: {min_rt_increase} min")

    def apply(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Apply Rule 4 to validate O-acetylation effects

        Args:
            df: DataFrame with 'prefix', 'suffix', and 'RT' columns

        Returns:
            Dictionary containing:
            - oacetylation_analysis: Validation results for each OAc compound
            - valid_oacetyl: Compounds with expected RT increase
            - invalid_oacetyl: Compounds with unexpected RT behavior
        """
        print("\n⚗️ Applying Rule 4: O-acetylation Validation")

        oacetylation_analysis = {}
        valid_oacetyl_compounds = []
        invalid_oacetyl_compounds = []

        # Find all OAc-containing compounds
        oacetyl_compounds = df[df["prefix"].str.contains("OAc", na=False)]

        print(f"   Found {len(oacetyl_compounds)} O-acetylated compounds")

        for _, oacetyl_row in oacetyl_compounds.iterrows():
            # Find corresponding base compound (without OAc)
            base_result = self._find_base_compound(oacetyl_row, df)

            if base_result["found"]:
                # Validate RT increase
                validation = self._validate_rt_increase(
                    oacetyl_row, base_result["base_compound"]
                )

                compound_name = oacetyl_row["Name"]
                oacetylation_analysis[compound_name] = validation

                # Classify compound
                row_dict = oacetyl_row.to_dict()
                row_dict["base_compound"] = base_result["base_name"]
                row_dict["base_rt"] = validation["base_rt"]
                row_dict["oacetyl_rt"] = validation["oacetyl_rt"]
                row_dict["rt_change"] = validation["rt_change"]

                if validation["is_valid"]:
                    valid_oacetyl_compounds.append(row_dict)
                else:
                    row_dict["outlier_reason"] = validation["reason"]
                    invalid_oacetyl_compounds.append(row_dict)

            else:
                # Base compound not found - cannot validate
                compound_name = oacetyl_row["Name"]
                row_dict = oacetyl_row.to_dict()
                row_dict["outlier_reason"] = "Rule 4: Base compound not found for validation"
                invalid_oacetyl_compounds.append(row_dict)

                oacetylation_analysis[compound_name] = {
                    "is_valid": False,
                    "reason": "Base compound not found",
                    "base_rt": None,
                    "oacetyl_rt": float(oacetyl_row["RT"]),
                    "rt_change": None
                }

        print(f"✅ Rule 4 complete:")
        print(f"   - Valid OAc compounds: {len(valid_oacetyl_compounds)}")
        print(f"   - Invalid OAc compounds: {len(invalid_oacetyl_compounds)}")

        validation_rate = (
            len(valid_oacetyl_compounds) / len(oacetyl_compounds) * 100
            if len(oacetyl_compounds) > 0
            else 0
        )
        print(f"   - Validation rate: {validation_rate:.1f}%")

        return {
            "oacetylation_analysis": oacetylation_analysis,
            "valid_oacetyl": valid_oacetyl_compounds,
            "invalid_oacetyl": invalid_oacetyl_compounds,
            "statistics": {
                "total_oacetyl": len(oacetyl_compounds),
                "valid": len(valid_oacetyl_compounds),
                "invalid": len(invalid_oacetyl_compounds),
                "validation_rate": validation_rate
            }
        }

    def _find_base_compound(
        self, oacetyl_row: pd.Series, df: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Find the base compound (without OAc) for comparison

        Args:
            oacetyl_row: Row with OAc-modified compound
            df: Full dataset

        Returns:
            Dictionary with base compound info or None if not found
        """
        # Remove OAc from prefix to get base prefix
        base_prefix = oacetyl_row["prefix"].replace("+OAc", "").replace("+2OAc", "")

        # Same lipid chain (suffix) required
        target_suffix = oacetyl_row["suffix"]

        # Find matching base compound
        base_compounds = df[
            (df["prefix"] == base_prefix) & (df["suffix"] == target_suffix)
        ]

        if len(base_compounds) > 0:
            base_compound = base_compounds.iloc[0]
            return {
                "found": True,
                "base_compound": base_compound,
                "base_name": base_compound["Name"],
                "base_prefix": base_prefix
            }
        else:
            return {
                "found": False,
                "base_compound": None,
                "base_name": None,
                "base_prefix": base_prefix
            }

    def _validate_rt_increase(
        self, oacetyl_compound: pd.Series, base_compound: pd.Series
    ) -> Dict[str, Any]:
        """
        Validate that OAc increases RT

        Args:
            oacetyl_compound: OAc-modified compound
            base_compound: Base compound without OAc

        Returns:
            Validation result with RT comparison
        """
        base_rt = float(base_compound["RT"])
        oacetyl_rt = float(oacetyl_compound["RT"])
        rt_change = oacetyl_rt - base_rt

        # Validation: OAc should increase RT
        is_valid = rt_change >= self.min_rt_increase

        if is_valid:
            reason = f"Valid: RT increased by {rt_change:.3f} min"
        else:
            if rt_change < 0:
                reason = f"Invalid: RT decreased by {abs(rt_change):.3f} min (expected increase)"
            else:
                reason = f"Invalid: RT increase ({rt_change:.3f} min) below threshold ({self.min_rt_increase} min)"

        return {
            "is_valid": is_valid,
            "reason": reason,
            "base_rt": base_rt,
            "oacetyl_rt": oacetyl_rt,
            "rt_change": rt_change,
            "percent_change": (rt_change / base_rt * 100) if base_rt > 0 else 0
        }

    def get_validation_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate human-readable validation summary

        Args:
            results: Results from apply() method

        Returns:
            Formatted summary string
        """
        summary = "⚗️ O-ACETYLATION VALIDATION SUMMARY\n"
        summary += "=" * 50 + "\n\n"

        stats = results["statistics"]
        summary += f"Total OAc compounds: {stats['total_oacetyl']}\n"
        summary += f"Valid (RT increased): {stats['valid']}\n"
        summary += f"Invalid (unexpected RT): {stats['invalid']}\n"
        summary += f"Validation rate: {stats['validation_rate']:.1f}%\n\n"

        if results["valid_oacetyl"]:
            summary += "✅ Valid O-acetylation examples:\n"
            for comp in results["valid_oacetyl"][:5]:  # Show first 5
                summary += f"   - {comp['Name']}: "
                summary += f"RT {comp['base_rt']:.2f} → {comp['oacetyl_rt']:.2f} "
                summary += f"(+{comp['rt_change']:.3f} min)\n"

        if results["invalid_oacetyl"]:
            summary += "\n❌ Invalid O-acetylation examples:\n"
            for comp in results["invalid_oacetyl"][:5]:  # Show first 5
                summary += f"   - {comp['Name']}: "
                summary += f"{comp.get('outlier_reason', 'Unknown issue')}\n"

        return summary
