"""
Rule 5: In-source Fragmentation Detection
Detects and consolidates fragmentation products based on RT clustering and sugar count
"""

from typing import Any, Dict, List, Callable
import pandas as pd
import numpy as np


class Rule5Fragmentation:
    """
    Rule 5: In-source Fragmentation Detection and Consolidation

    Purpose:
    - Detects in-source fragmentation during LC-MS analysis
    - Fragments have: same lipid chain, similar RT, decreasing sugar count
    - Identifies parent molecule (highest sugar count)
    - Consolidates fragment volumes into parent

    Chemistry:
    - In-source fragmentation: Molecules break before mass analysis
    - GT1(36:1;O2) → GD1(36:1;O2) + sugar
    -                → GM1(36:1;O2) + more sugars
    - All fragments co-elute (same RT ± tolerance)
    - Parent has highest sugar count and lowest Log P

    Algorithm:
    1. Group by lipid chain (suffix)
    2. Cluster by RT (within ±tolerance)
    3. Sort by sugar count (descending) and Log P (ascending)
    4. Keep highest sugar = parent
    5. Mark others as fragments
    6. Consolidate volumes into parent
    """

    def __init__(self, rt_tolerance: float = 0.1, sugar_count_calculator: Callable = None):
        """
        Initialize Rule 5

        Args:
            rt_tolerance: RT window for co-elution (minutes, default: ±0.1 min)
            sugar_count_calculator: Function to calculate sugar count from prefix
        """
        self.rt_tolerance = rt_tolerance
        self.sugar_count_calculator = sugar_count_calculator

        print("🔍 Rule 5: Fragmentation Detection initialized")
        print(f"   - RT tolerance: ±{rt_tolerance} min")

    def apply(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Apply Rule 5 to detect and consolidate fragments

        Args:
            df: DataFrame with compounds (must have: prefix, suffix, RT, Volume)

        Returns:
            Dictionary containing:
            - filtered_compounds: Final compounds after consolidation
            - fragmentation_candidates: Detected fragments
            - consolidation_details: Volume merging information
        """
        print("\n🔍 Applying Rule 5: Fragmentation Detection")

        filtered_compounds = []
        fragmentation_candidates = []
        consolidation_details = []

        # Group by lipid chain (suffix)
        suffix_groups = df.groupby("suffix")
        print(f"   Analyzing {len(suffix_groups)} lipid chain groups")

        for suffix, suffix_group in suffix_groups:
            if pd.isna(suffix):
                continue

            print(f"\n   Lipid chain: ({suffix}) - {len(suffix_group)} compounds")

            if len(suffix_group) <= 1:
                # Single compound - no fragmentation possible
                filtered_compounds.extend(suffix_group.to_dict("records"))
                continue

            # Find RT clusters and consolidate fragments
            result = self._detect_fragments_in_group(suffix_group, suffix)

            filtered_compounds.extend(result["valid_compounds"])
            fragmentation_candidates.extend(result["fragments"])
            consolidation_details.extend(result["consolidations"])

        print(f"\n✅ Rule 5 complete:")
        print(f"   - Final compounds: {len(filtered_compounds)}")
        print(f"   - Fragments detected: {len(fragmentation_candidates)}")
        print(f"   - Volume consolidations: {len(consolidation_details)}")

        return {
            "filtered_compounds": filtered_compounds,
            "fragmentation_candidates": fragmentation_candidates,
            "consolidation_details": consolidation_details,
            "statistics": {
                "final_compounds": len(filtered_compounds),
                "fragments_detected": len(fragmentation_candidates),
                "consolidations": len(consolidation_details),
                "volume_recovered": sum(c["total_volume"] for c in consolidation_details)
            }
        }

    def _detect_fragments_in_group(
        self, suffix_group: pd.DataFrame, suffix: str
    ) -> Dict[str, Any]:
        """
        Detect fragments within a lipid chain group

        Args:
            suffix_group: All compounds with same lipid chain
            suffix: Lipid chain identifier

        Returns:
            Valid compounds, fragments, and consolidation info
        """
        # Sort by RT for clustering
        suffix_group = suffix_group.sort_values("RT").reset_index(drop=True)

        # Find RT clusters
        rt_clusters = self._cluster_by_rt(suffix_group)

        valid_compounds = []
        fragments = []
        consolidations = []

        # Process each RT cluster
        for cluster in rt_clusters:
            if len(cluster) == 1:
                # Single compound - no fragmentation
                valid_compounds.append(cluster[0].to_dict())
            else:
                # Multiple compounds at same RT - potential fragments
                result = self._consolidate_fragments(cluster, suffix)

                valid_compounds.append(result["parent"])
                fragments.extend(result["fragments"])

                if result["consolidated"]:
                    consolidations.append(result["consolidation_info"])

        return {
            "valid_compounds": valid_compounds,
            "fragments": fragments,
            "consolidations": consolidations
        }

    def _cluster_by_rt(self, group: pd.DataFrame) -> List[List[pd.Series]]:
        """
        Cluster compounds by RT tolerance

        Args:
            group: DataFrame sorted by RT

        Returns:
            List of RT clusters (each cluster is a list of compounds)
        """
        if len(group) == 0:
            return []

        rt_clusters = []
        current_cluster = [group.iloc[0]]

        for i in range(1, len(group)):
            current_rt = group.iloc[i]["RT"]
            reference_rt = current_cluster[0]["RT"]

            # Check if within tolerance
            if abs(current_rt - reference_rt) <= self.rt_tolerance:
                current_cluster.append(group.iloc[i])
            else:
                # Start new cluster
                rt_clusters.append(current_cluster)
                current_cluster = [group.iloc[i]]

        # Add last cluster
        if current_cluster:
            rt_clusters.append(current_cluster)

        return rt_clusters

    def _consolidate_fragments(
        self, cluster: List[pd.Series], suffix: str
    ) -> Dict[str, Any]:
        """
        Consolidate fragments in an RT cluster

        Identifies parent (highest sugar count) and merges volumes

        Args:
            cluster: List of compounds co-eluting at same RT
            suffix: Lipid chain

        Returns:
            Parent compound, fragment list, and consolidation info
        """
        # Calculate sugar counts for each compound
        sugar_data = []
        for compound in cluster:
            if self.sugar_count_calculator:
                sugar_info = self.sugar_count_calculator(compound["prefix"])
                sugar_count = sugar_info.get("total", sugar_info.get("total_sugars", 0))
            else:
                # Fallback: use sugar_count column if available
                sugar_count = compound.get("sugar_count", 0)

            sugar_data.append({
                "compound": compound,
                "sugar_count": sugar_count,
                "log_p": compound.get("Log P", 0)
            })

        # Sort by: 1) Highest sugar count, 2) Lowest Log P
        sugar_data.sort(key=lambda x: (-x["sugar_count"], x["log_p"]))

        # Parent = highest sugar count (most complete molecule)
        parent_data = sugar_data[0]
        parent = parent_data["compound"].to_dict()

        # Fragments = rest of the cluster
        fragment_data = sugar_data[1:]

        # Consolidate volumes
        total_volume = parent["Volume"]
        fragment_names = []

        for frag_data in fragment_data:
            total_volume += frag_data["compound"]["Volume"]
            fragment_names.append(frag_data["compound"]["Name"])

        # Update parent with consolidated volume
        parent["Volume"] = total_volume
        parent["original_volume"] = parent_data["compound"]["Volume"]
        parent["merged_compounds"] = len(cluster)
        parent["fragmentation_sources"] = fragment_names

        # Create fragment records
        fragments_list = []
        for frag_data in fragment_data:
            frag_dict = frag_data["compound"].to_dict()
            frag_dict["outlier_reason"] = "Rule 5: In-source fragmentation candidate"
            frag_dict["reference_compound"] = parent["Name"]
            frag_dict["rt_difference"] = abs(frag_dict["RT"] - parent["RT"])
            frag_dict["sugar_difference"] = parent_data["sugar_count"] - frag_data["sugar_count"]
            fragments_list.append(frag_dict)

        # Consolidation info
        consolidation_info = {
            "parent_compound": parent["Name"],
            "parent_sugar_count": parent_data["sugar_count"],
            "suffix": suffix,
            "rt": parent["RT"],
            "fragments": fragment_names,
            "fragment_count": len(fragment_names),
            "original_volume": parent_data["compound"]["Volume"],
            "total_volume": total_volume,
            "volume_increase": total_volume - parent_data["compound"]["Volume"],
            "recovery_rate": (total_volume / parent_data["compound"]["Volume"] - 1) * 100
            if parent_data["compound"]["Volume"] > 0 else 0
        }

        return {
            "parent": parent,
            "fragments": fragments_list,
            "consolidated": len(fragment_names) > 0,
            "consolidation_info": consolidation_info
        }

    def get_fragmentation_summary(self, results: Dict[str, Any]) -> str:
        """
        Generate human-readable fragmentation summary

        Args:
            results: Results from apply() method

        Returns:
            Formatted summary string
        """
        summary = "🔍 FRAGMENTATION DETECTION SUMMARY\n"
        summary += "=" * 50 + "\n\n"

        stats = results["statistics"]
        summary += f"Final compounds: {stats['final_compounds']}\n"
        summary += f"Fragments detected: {stats['fragments_detected']}\n"
        summary += f"Consolidations: {stats['consolidations']}\n"
        summary += f"Total volume recovered: {stats['volume_recovered']:,.0f}\n\n"

        if results["consolidation_details"]:
            summary += "📊 Major consolidation examples:\n"
            # Sort by volume increase
            sorted_consolidations = sorted(
                results["consolidation_details"],
                key=lambda x: x["volume_increase"],
                reverse=True
            )

            for cons in sorted_consolidations[:5]:  # Show top 5
                summary += f"\n   {cons['parent_compound']}:\n"
                summary += f"      - RT: {cons['rt']:.2f} min\n"
                summary += f"      - Sugar count: {cons['parent_sugar_count']}\n"
                summary += f"      - Fragments consolidated: {cons['fragment_count']}\n"
                summary += f"      - Volume: {cons['original_volume']:,.0f} → {cons['total_volume']:,.0f}\n"
                summary += f"      - Recovery: +{cons['recovery_rate']:.1f}%\n"
                summary += f"      - Fragment sources: {', '.join(cons['fragments'][:3])}\n"

        return summary
