"""
Stepwise Analysis Service - Rule-by-Rule Interactive Analysis
Allows frontend to supervise and control each analysis rule separately
"""

from typing import Any, Dict, Optional
import pandas as pd
import numpy as np
from .ganglioside_processor import GangliosideProcessor


class StepwiseAnalyzer:
    """
    Provides step-by-step analysis with rule separation for interactive supervision
    """

    def __init__(self):
        self.processor = GangliosideProcessor()
        self.current_data = None
        self.preprocessed_data = None
        self.rule_results = {}
        self.analysis_state = "initialized"

        print("🔬 Stepwise Analyzer 초기화 완료")

    def load_data(self, df: pd.DataFrame, data_type: str = "Porcine") -> Dict[str, Any]:
        """
        Step 0: Load and preprocess data

        Returns:
            Preprocessing results with feature extraction details
        """
        self.current_data = df.copy()
        self.data_type = data_type
        self.analysis_state = "data_loaded"

        # Preprocess data
        self.preprocessed_data = self.processor._preprocess_data(df.copy())

        # Extract feature statistics
        feature_stats = {
            "total_compounds": len(self.preprocessed_data),
            "features_extracted": {
                "log_p": {
                    "mean": float(self.preprocessed_data["Log P"].mean()),
                    "min": float(self.preprocessed_data["Log P"].min()),
                    "max": float(self.preprocessed_data["Log P"].max()),
                },
                "carbon_chain": {
                    "mean": float(self.preprocessed_data["a_component"].mean()),
                    "range": [
                        int(self.preprocessed_data["a_component"].min()),
                        int(self.preprocessed_data["a_component"].max())
                    ]
                },
                "unsaturation": {
                    "mean": float(self.preprocessed_data["b_component"].mean()),
                    "values": sorted(self.preprocessed_data["b_component"].unique().tolist())
                },
                "sugar_count": {
                    "mean": float(self.preprocessed_data["sugar_count"].mean()),
                    "distribution": dict(self.preprocessed_data["sugar_count"].value_counts().to_dict())
                },
                "modifications": {
                    "has_OAc": int(self.preprocessed_data["has_OAc"].sum()),
                    "has_dHex": int(self.preprocessed_data["has_dHex"].sum()),
                    "has_HexNAc": int(self.preprocessed_data["has_HexNAc"].sum()),
                }
            },
            "prefix_distribution": dict(self.preprocessed_data["prefix"].value_counts().to_dict()),
            "suffix_distribution": dict(self.preprocessed_data["suffix"].value_counts().to_dict()),
        }

        return {
            "status": "preprocessed",
            "feature_stats": feature_stats,
            "data_preview": self.preprocessed_data.head(10).to_dict('records'),
            "columns": list(self.preprocessed_data.columns)
        }

    def execute_rule1(self) -> Dict[str, Any]:
        """
        Step 1: Execute Rule 1 - Prefix-based Regression Analysis

        Returns:
            Rule 1 results with regression details and classification
        """
        if self.preprocessed_data is None:
            return {"error": "Data not loaded. Call load_data() first."}

        print("\n📊 Executing Rule 1: Prefix-based Regression Analysis")
        rule1_results = self.processor._apply_rule1_prefix_regression(self.preprocessed_data)
        self.rule_results["rule1"] = rule1_results
        self.analysis_state = "rule1_completed"

        # Format for frontend visualization
        return {
            "status": "completed",
            "rule_name": "Rule 1: Prefix-based Regression",
            "description": "Groups compounds by prefix and performs multiple regression analysis",
            "results": {
                "regression_groups": len(rule1_results["regression_results"]),
                "valid_compounds": len(rule1_results["valid_compounds"]),
                "outliers_detected": len(rule1_results["outliers"]),
                "regression_details": {
                    group_name: {
                        "r2": reg_result["r2"],
                        "n_features": reg_result.get("n_features", 1),
                        "feature_names": reg_result.get("feature_names", ["Log P"]),
                        "equation": reg_result["equation"],
                        "n_samples": reg_result["n_samples"],
                        "coefficients": reg_result.get("coefficients", {}),
                    }
                    for group_name, reg_result in rule1_results["regression_results"].items()
                },
                "valid_compounds_preview": rule1_results["valid_compounds"][:10],
                "outliers_preview": rule1_results["outliers"][:10],
            },
            "visualization_data": {
                "scatter_data": [
                    {
                        "name": comp["Name"],
                        "log_p": comp.get("Log P", 0),
                        "rt": comp.get("RT", 0),
                        "predicted_rt": comp.get("predicted_rt", comp.get("RT", 0)),
                        "residual": comp.get("residual", 0),
                        "status": "valid"
                    }
                    for comp in rule1_results["valid_compounds"]
                ] + [
                    {
                        "name": comp["Name"],
                        "log_p": comp.get("Log P", 0),
                        "rt": comp.get("RT", 0),
                        "predicted_rt": comp.get("predicted_rt", comp.get("RT", 0)),
                        "residual": comp.get("residual", 0),
                        "status": "outlier",
                        "reason": comp.get("outlier_reason", "Unknown")
                    }
                    for comp in rule1_results["outliers"]
                ]
            }
        }

    def execute_rule23(self) -> Dict[str, Any]:
        """
        Step 2: Execute Rules 2-3 - Sugar Count Calculation and Isomer Classification

        Returns:
            Rules 2-3 results with sugar analysis and isomer detection
        """
        if self.preprocessed_data is None:
            return {"error": "Data not loaded. Call load_data() first."}

        print("\n🧬 Executing Rules 2-3: Sugar Count & Isomer Classification")
        rule23_results = self.processor._apply_rule2_3_sugar_count(
            self.preprocessed_data, self.data_type
        )
        self.rule_results["rule23"] = rule23_results
        self.analysis_state = "rule23_completed"

        # Count isomers
        isomer_candidates = sum(
            1 for info in rule23_results["sugar_analysis"].values()
            if info["can_have_isomers"]
        )

        # Group by sugar count
        sugar_distribution = {}
        for compound_name, info in rule23_results["sugar_analysis"].items():
            sugar_count = info["total_sugars"]
            if sugar_count not in sugar_distribution:
                sugar_distribution[sugar_count] = []
            sugar_distribution[sugar_count].append(compound_name)

        return {
            "status": "completed",
            "rule_name": "Rules 2-3: Sugar Count & Isomer Classification",
            "description": "Calculates total sugar count and identifies structural isomers",
            "results": {
                "total_analyzed": len(rule23_results["sugar_analysis"]),
                "isomer_candidates": isomer_candidates,
                "sugar_distribution": {
                    str(k): len(v) for k, v in sorted(sugar_distribution.items())
                },
                "sugar_analysis_preview": dict(list(rule23_results["sugar_analysis"].items())[:10]),
            },
            "visualization_data": {
                "sugar_histogram": [
                    {"sugar_count": k, "compound_count": len(v), "compounds": v[:5]}
                    for k, v in sorted(sugar_distribution.items())
                ],
                "isomer_details": [
                    {
                        "compound": name,
                        "sugar_count": info["total_sugars"],
                        "isomer_type": info["isomer_type"],
                        "can_have_isomers": info["can_have_isomers"]
                    }
                    for name, info in rule23_results["sugar_analysis"].items()
                    if info["can_have_isomers"]
                ]
            }
        }

    def execute_rule4(self) -> Dict[str, Any]:
        """
        Step 3: Execute Rule 4 - O-acetylation Effect Validation

        Returns:
            Rule 4 results with O-acetylation validation
        """
        if self.preprocessed_data is None:
            return {"error": "Data not loaded. Call load_data() first."}

        print("\n⚗️ Executing Rule 4: O-acetylation Effect Validation")
        rule4_results = self.processor._apply_rule4_oacetylation(self.preprocessed_data)
        self.rule_results["rule4"] = rule4_results
        self.analysis_state = "rule4_completed"

        total_oacetyl = len(rule4_results["valid_oacetyl"]) + len(rule4_results["invalid_oacetyl"])

        return {
            "status": "completed",
            "rule_name": "Rule 4: O-acetylation Effect Validation",
            "description": "Validates that O-acetylation increases retention time",
            "results": {
                "total_oacetyl_compounds": total_oacetyl,
                "valid_oacetyl": len(rule4_results["valid_oacetyl"]),
                "invalid_oacetyl": len(rule4_results["invalid_oacetyl"]),
                "validation_rate": (len(rule4_results["valid_oacetyl"]) / total_oacetyl * 100)
                if total_oacetyl > 0 else 0,
                "valid_compounds_preview": rule4_results["valid_oacetyl"][:5],
                "invalid_compounds_preview": rule4_results["invalid_oacetyl"][:5],
            },
            "visualization_data": {
                "oacetyl_comparison": [
                    {
                        "compound": comp["Name"],
                        "base_rt": comp["base_rt"],
                        "oacetyl_rt": comp["RT"],
                        "rt_increase": comp["rt_increase"],
                        "status": "valid"
                    }
                    for comp in rule4_results["valid_oacetyl"]
                ] + [
                    {
                        "compound": comp["Name"],
                        "base_rt": comp.get("base_rt", 0),
                        "oacetyl_rt": comp["RT"],
                        "rt_decrease": comp.get("rt_decrease", 0),
                        "status": "invalid",
                        "reason": comp.get("outlier_reason", "Unknown")
                    }
                    for comp in rule4_results["invalid_oacetyl"]
                ]
            }
        }

    def execute_rule5(self) -> Dict[str, Any]:
        """
        Step 4: Execute Rule 5 - RT Filtering and In-source Fragmentation Detection

        Returns:
            Rule 5 results with fragmentation analysis
        """
        if self.preprocessed_data is None:
            return {"error": "Data not loaded. Call load_data() first."}

        print("\n🔍 Executing Rule 5: In-source Fragmentation Detection")
        rule5_results = self.processor._apply_rule5_rt_filtering(self.preprocessed_data)
        self.rule_results["rule5"] = rule5_results
        self.analysis_state = "rule5_completed"

        # Analyze fragmentation patterns
        fragmentation_by_suffix = {}
        for frag in rule5_results["fragmentation_candidates"]:
            suffix = frag.get("suffix", "Unknown")
            if suffix not in fragmentation_by_suffix:
                fragmentation_by_suffix[suffix] = []
            fragmentation_by_suffix[suffix].append(frag["Name"])

        # Volume consolidation stats
        merged_compounds = [
            comp for comp in rule5_results["filtered_compounds"]
            if comp.get("merged_compounds", 1) > 1
        ]

        return {
            "status": "completed",
            "rule_name": "Rule 5: In-source Fragmentation Detection",
            "description": "Detects and consolidates fragmentation products within RT tolerance",
            "results": {
                "total_fragments_detected": len(rule5_results["fragmentation_candidates"]),
                "compounds_after_filtering": len(rule5_results["filtered_compounds"]),
                "volume_consolidations": len(merged_compounds),
                "rt_tolerance_used": self.processor.rt_tolerance,
                "fragmentation_by_suffix": {
                    suffix: len(frags) for suffix, frags in fragmentation_by_suffix.items()
                },
                "merged_compounds_preview": merged_compounds[:5],
                "fragments_preview": rule5_results["fragmentation_candidates"][:10],
            },
            "visualization_data": {
                "fragmentation_series": [
                    {
                        "parent": comp["Name"],
                        "rt": comp["RT"],
                        "original_volume": comp["Volume"] / comp.get("merged_compounds", 1),
                        "consolidated_volume": comp["Volume"],
                        "merged_count": comp.get("merged_compounds", 1),
                        "fragments": comp.get("fragmentation_sources", [])
                    }
                    for comp in merged_compounds
                ],
                "fragment_details": [
                    {
                        "fragment": frag["Name"],
                        "rt": frag["RT"],
                        "parent": frag.get("reference_compound", "Unknown"),
                        "rt_difference": frag.get("rt_difference", 0),
                        "sugar_count": self.processor._calculate_sugar_count(
                            frag.get("prefix", "")
                        )["total"]
                    }
                    for frag in rule5_results["fragmentation_candidates"]
                ]
            }
        }

    def get_final_summary(self) -> Dict[str, Any]:
        """
        Get final analysis summary combining all rules

        Returns:
            Comprehensive summary with statistics from all rules
        """
        if not self.rule_results:
            return {"error": "No analysis has been performed yet"}

        # Compile statistics from all rules
        rule1 = self.rule_results.get("rule1", {})
        rule23 = self.rule_results.get("rule23", {})
        rule4 = self.rule_results.get("rule4", {})
        rule5 = self.rule_results.get("rule5", {})

        total_compounds = len(self.preprocessed_data) if self.preprocessed_data is not None else 0
        valid_after_rule1 = len(rule1.get("valid_compounds", []))
        outliers_rule1 = len(rule1.get("outliers", []))
        fragments_rule5 = len(rule5.get("fragmentation_candidates", []))
        final_compounds = len(rule5.get("filtered_compounds", []))

        return {
            "status": "analysis_complete",
            "overall_statistics": {
                "total_input_compounds": total_compounds,
                "after_rule1_regression": {
                    "valid": valid_after_rule1,
                    "outliers": outliers_rule1
                },
                "after_rule5_fragmentation": {
                    "final_compounds": final_compounds,
                    "fragments_detected": fragments_rule5
                },
                "success_rate": (final_compounds / total_compounds * 100) if total_compounds > 0 else 0
            },
            "rule_summary": {
                "rule1": {
                    "regression_groups": len(rule1.get("regression_results", {})),
                    "avg_r2": np.mean([r["r2"] for r in rule1.get("regression_results", {}).values()])
                    if rule1.get("regression_results") else 0
                },
                "rule23": {
                    "isomer_candidates": sum(
                        1 for info in rule23.get("sugar_analysis", {}).values()
                        if info.get("can_have_isomers", False)
                    )
                },
                "rule4": {
                    "oacetyl_validated": len(rule4.get("valid_oacetyl", []))
                },
                "rule5": {
                    "fragments_consolidated": fragments_rule5
                }
            }
        }

    def reset(self):
        """Reset analyzer state for new analysis"""
        self.current_data = None
        self.preprocessed_data = None
        self.rule_results = {}
        self.analysis_state = "initialized"
        print("🔄 Stepwise Analyzer 초기화됨")
