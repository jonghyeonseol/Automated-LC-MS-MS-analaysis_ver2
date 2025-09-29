"""
Data Structures for LC-MS-MS Analysis
Common data structures and type definitions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import numpy as np


@dataclass
class CompoundData:
    """Single compound data structure"""
    name: str
    rt: float  # Retention Time
    volume: float
    log_p: float  # Partition Coefficient (Log P)
    anchor: str  # 'T' or 'F'

    # Derived properties
    prefix: Optional[str] = None
    suffix: Optional[str] = None
    a_component: Optional[int] = None
    b_component: Optional[int] = None
    c_component: Optional[str] = None

    # Analysis results
    predicted_rt: Optional[float] = None
    residual: Optional[float] = None
    std_residual: Optional[float] = None
    outlier_reason: Optional[str] = None


@dataclass
class VisualizationData:
    """3D visualization data structure"""
    x_data: List[float]  # Mass-to-charge ratio (m/z)
    y_data: List[float]  # Retention Time
    z_data: List[float]  # Partition Coefficient (Log P)

    # Additional properties
    labels: List[str]
    colors: List[str]
    sizes: List[float]
    anchor_mask: List[bool]

    # Metadata
    title: str
    x_label: str = "Mass-to-Charge (m/z)"
    y_label: str = "Retention Time (min)"
    z_label: str = "Partition Coefficient (Log P)"

    # Optional data for enhanced visualization
    outlier_mask: Optional[List[bool]] = None
    prefix_groups: Optional[Dict[str, List[int]]] = None


def calculate_mass_to_charge(compound_name: str, base_mass: Optional[float] = None) -> float:
    """
    Calculate mass-to-charge ratio from compound name

    Args:
        compound_name: Compound name like "GD1a(36:1;O2)"
        base_mass: Optional base mass for the ganglioside class

    Returns:
        Estimated m/z ratio
    """
    import re

    # Extract fatty acid composition (e.g., "36:1;O2")
    pattern = r'\((\d+):(\d+);O(\d+)\)'
    match = re.search(pattern, compound_name)

    if not match:
        return 800.0  # Default fallback

    carbon_count = int(match.group(1))
    unsaturation = int(match.group(2))
    oxygen_count = int(match.group(3))

    # Estimate molecular weight based on fatty acid composition
    # Carbon: 12.01, Hydrogen: 1.008, Oxygen: 15.999
    fatty_acid_mw = carbon_count * 12.01 + (2 * carbon_count - 2 * unsaturation) * 1.008 + oxygen_count * 15.999

    # Base molecular weights for ganglioside classes (approximate)
    ganglioside_base_weights = {
        'GM3': 1200,   # Simplest ganglioside
        'GM2': 1400,
        'GM1': 1500,
        'GD3': 1500,
        'GD2': 1700,
        'GD1': 1800,
        'GT3': 1800,
        'GT2': 2000,
        'GT1': 2100,
        'GQ1': 2400,
        'GP1': 2700,
    }

    # Extract ganglioside class
    for prefix, base_weight in ganglioside_base_weights.items():
        if compound_name.startswith(prefix):
            total_mw = base_weight + fatty_acid_mw
            return total_mw  # Assuming z=1 (singly charged)

    # Default calculation
    return 1500 + fatty_acid_mw


@dataclass
class RegressionResult:
    """Regression analysis result"""
    prefix: str
    slope: float
    intercept: float
    r2: float
    n_samples: int
    equation: str
    p_value: float

    def predict(self, log_p_values: np.ndarray) -> np.ndarray:
        """Predict RT values from Log P"""
        return self.slope * log_p_values + self.intercept


@dataclass
class AnalysisResults:
    """Complete analysis results structure"""
    valid_compounds: List[CompoundData]
    outliers: List[CompoundData]
    regression_results: Dict[str, RegressionResult]
    statistics: Dict[str, Any]

    # Additional analysis data
    sugar_analysis: Dict[str, Any]
    oacetylation_analysis: Dict[str, Any]
    detailed_analysis: Dict[str, Any]