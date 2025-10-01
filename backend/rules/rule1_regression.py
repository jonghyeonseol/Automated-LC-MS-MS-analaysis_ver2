"""
Rule 1: Prefix-based Multiple Regression Analysis
Groups compounds by prefix and performs multiple regression with functional features
"""

from typing import Any, Dict, List
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import r2_score


class Rule1PrefixRegression:
    """
    Rule 1: Prefix-based regression analysis with multiple features

    Purpose:
    - Groups compounds by their prefix (e.g., GD1, GM1, GT1)
    - Performs multiple regression: RT = f(Log P, Carbon, Sugar Count, Modifications, etc.)
    - Identifies outliers based on standardized residuals
    - Only uses anchor compounds (Anchor='T') for training
    """

    def __init__(
        self,
        r2_threshold: float = 0.99,
        outlier_threshold: float = 2.0,
        use_ridge: bool = True,
        regularization_alpha: float = 1.0
    ):
        """
        Initialize Rule 1

        Args:
            r2_threshold: Minimum R² for valid regression (default: 0.99)
            outlier_threshold: Standardized residual threshold for outliers (default: 2.0σ)
            use_ridge: Use Ridge regression instead of LinearRegression (default: True)
            regularization_alpha: Ridge regularization strength (default: 1.0)
                                 Higher values = more regularization
                                 Recommended range: 0.1 - 10.0
        """
        self.r2_threshold = r2_threshold
        self.outlier_threshold = outlier_threshold
        self.use_ridge = use_ridge
        self.regularization_alpha = regularization_alpha

        # Feature names for multiple regression
        self.feature_names = [
            "Log P",
            "a_component",      # Carbon chain length
            "b_component",      # Unsaturation
            "oxygen_count",     # Oxygen atoms
            "sugar_count",      # Total sugars
            "sialic_acid_count", # Sialic acids (e-component)
            "has_OAc",          # O-acetylation (binary)
            "has_dHex",         # Deoxyhexose (binary)
            "has_HexNAc"        # N-acetylhexosamine (binary)
        ]

        print("📊 Rule 1: Prefix-based Regression initialized")
        print(f"   - R² threshold: {r2_threshold}")
        print(f"   - Outlier threshold: ±{outlier_threshold}σ")
        print(f"   - Regularization: {'Ridge (α=' + str(regularization_alpha) + ')' if use_ridge else 'None (LinearRegression)'}")
        print(f"   - Features: {len(self.feature_names)}")

    def apply(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Apply Rule 1 to the dataset

        Args:
            df: Preprocessed DataFrame with all features extracted

        Returns:
            Dictionary containing:
            - regression_results: Regression model for each prefix group
            - valid_compounds: Compounds that pass regression validation
            - outliers: Compounds flagged as outliers
        """
        print("\n📊 Applying Rule 1: Prefix-based Regression")

        regression_results = {}
        valid_compounds = []
        outliers = []

        # Group by prefix
        prefix_groups = df.groupby("prefix")
        print(f"   Found {len(prefix_groups)} prefix groups")

        for prefix, prefix_group in prefix_groups:
            print(f"\n   Analyzing group: {prefix} ({len(prefix_group)} compounds)")

            # Get anchor compounds (training set)
            anchor_compounds = prefix_group[prefix_group["Anchor"] == "T"]

            if len(anchor_compounds) < 2:
                print(f"      ⚠️ Insufficient anchor compounds ({len(anchor_compounds)})")
                # Mark all as outliers
                for _, row in prefix_group.iterrows():
                    row_dict = row.to_dict()
                    row_dict["outlier_reason"] = "Rule 1: Insufficient anchor compounds"
                    outliers.append(row_dict)
                continue

            # Perform regression
            result = self._perform_multiple_regression(
                anchor_compounds, prefix_group, prefix
            )

            if result["success"]:
                regression_results[prefix] = result["regression_info"]
                valid_compounds.extend(result["valid_compounds"])
                outliers.extend(result["outliers"])
            else:
                # Regression failed - mark all as outliers
                for _, row in prefix_group.iterrows():
                    row_dict = row.to_dict()
                    row_dict["outlier_reason"] = f"Rule 1: {result['reason']}"
                    outliers.append(row_dict)

        # Fallback: If no groups formed, try overall regression
        if len(regression_results) == 0:
            print("\n   📊 Fallback: Overall regression with all anchors")
            fallback_result = self._fallback_regression(df)

            if fallback_result["success"]:
                regression_results["Overall_Fallback"] = fallback_result["regression_info"]
                valid_compounds = fallback_result["valid_compounds"]
                outliers = fallback_result["outliers"]

        print(f"\n✅ Rule 1 complete:")
        print(f"   - Regression groups: {len(regression_results)}")
        print(f"   - Valid compounds: {len(valid_compounds)}")
        print(f"   - Outliers: {len(outliers)}")

        return {
            "regression_results": regression_results,
            "valid_compounds": valid_compounds,
            "outliers": outliers,
            "statistics": {
                "total_groups": len(regression_results),
                "total_valid": len(valid_compounds),
                "total_outliers": len(outliers),
                "avg_r2": np.mean([r["r2"] for r in regression_results.values()])
                if regression_results else 0
            }
        }

    def _perform_multiple_regression(
        self, anchor_compounds: pd.DataFrame, full_group: pd.DataFrame, group_name: str
    ) -> Dict[str, Any]:
        """
        Perform multiple regression for a prefix group

        Args:
            anchor_compounds: Training data (Anchor='T')
            full_group: All compounds in this group
            group_name: Name of the group

        Returns:
            Success status, regression info, and classified compounds
        """
        try:
            # Select available features
            available_features = [
                col for col in self.feature_names if col in anchor_compounds.columns
            ]

            # Prepare training data
            X = anchor_compounds[available_features].values
            y = anchor_compounds["RT"].values

            # Check for sufficient variation
            if len(np.unique(X[:, 0])) < 2:
                return {
                    "success": False,
                    "reason": f"Insufficient Log P variation in {group_name}",
                    "valid_compounds": [],
                    "outliers": []
                }

            # Train model
            if self.use_ridge:
                model = Ridge(alpha=self.regularization_alpha)
            else:
                model = LinearRegression()

            model.fit(X, y)

            # Predict on training set
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)

            reg_type = f"Ridge(α={self.regularization_alpha})" if self.use_ridge else "LinearReg"
            print(f"      R² = {r2:.4f}, Features = {len(available_features)}, Model = {reg_type}")

            # Check R² threshold
            if r2 < self.r2_threshold:
                return {
                    "success": False,
                    "reason": f"R² ({r2:.4f}) below threshold ({self.r2_threshold})",
                    "valid_compounds": [],
                    "outliers": []
                }

            # Apply to full group
            all_X = full_group[available_features].values
            all_pred = model.predict(all_X)
            residuals = full_group["RT"].values - all_pred

            # Standardized residuals
            std_residuals = residuals / np.std(residuals) if np.std(residuals) > 0 else np.zeros_like(residuals)

            # Classify compounds
            outlier_mask = np.abs(std_residuals) >= self.outlier_threshold

            valid_compounds = []
            outliers = []

            for idx, (_, row) in enumerate(full_group.iterrows()):
                row_dict = row.to_dict()
                row_dict["predicted_rt"] = float(all_pred[idx])
                row_dict["residual"] = float(residuals[idx])
                row_dict["standardized_residual"] = float(std_residuals[idx])
                row_dict["regression_group"] = group_name

                if outlier_mask[idx]:
                    row_dict["outlier_reason"] = f"Rule 1: Residual {std_residuals[idx]:.2f}σ exceeds threshold"
                    outliers.append(row_dict)
                else:
                    valid_compounds.append(row_dict)

            # Generate equation
            equation_parts = [f"{model.intercept_:.4f}"]
            for coef, feat in zip(model.coef_, available_features):
                sign = "+" if coef >= 0 else "-"
                equation_parts.append(f"{sign} {abs(coef):.4f}*{feat}")
            equation = f"RT = {' '.join(equation_parts)}"

            # Coefficient details
            coefficient_info = {}
            for feat, coef in zip(available_features, model.coef_):
                coefficient_info[feat] = float(coef)

            # Durbin-Watson statistic
            dw_stat = self._durbin_watson_test(residuals)

            regression_info = {
                "intercept": float(model.intercept_),
                "coefficients": coefficient_info,
                "feature_names": available_features,
                "n_features": len(available_features),
                "r2": float(r2),
                "n_samples": len(full_group),
                "n_anchors": len(anchor_compounds),
                "equation": equation,
                "durbin_watson": dw_stat,
                "rmse": float(np.sqrt(np.mean(residuals**2))),
                "regularization": "Ridge" if self.use_ridge else "None",
                "regularization_alpha": float(self.regularization_alpha) if self.use_ridge else 0.0,
                # Legacy compatibility
                "slope": float(model.coef_[0]) if len(model.coef_) > 0 else 0,
            }

            return {
                "success": True,
                "regression_info": regression_info,
                "valid_compounds": valid_compounds,
                "outliers": outliers
            }

        except Exception as e:
            print(f"      ❌ Regression failed: {e}")
            return {
                "success": False,
                "reason": str(e),
                "valid_compounds": [],
                "outliers": []
            }

    def _fallback_regression(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Fallback: Overall regression when no prefix groups work

        Uses all anchor compounds regardless of prefix
        """
        anchor_compounds = df[df["Anchor"] == "T"]

        if len(anchor_compounds) < 2:
            return {
                "success": False,
                "reason": "Insufficient anchor compounds for fallback",
                "valid_compounds": [],
                "outliers": []
            }

        return self._perform_multiple_regression(
            anchor_compounds, df, "Overall_Fallback"
        )

    def _durbin_watson_test(self, residuals: np.ndarray) -> float:
        """
        Calculate Durbin-Watson statistic for autocorrelation

        DW ≈ 2 indicates no autocorrelation
        DW < 2 indicates positive autocorrelation
        DW > 2 indicates negative autocorrelation
        """
        if len(residuals) < 2:
            return 2.0

        diff_residuals = np.diff(residuals)
        dw = np.sum(diff_residuals**2) / np.sum(residuals**2)
        return float(dw)
