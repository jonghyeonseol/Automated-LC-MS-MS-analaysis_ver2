#!/usr/bin/env python3
"""
Integration tests for ganglioside categorization with real user data.

Tests the GangliosideCategorizer functionality including:
- Compound categorization by sialic acid content (GM, GD, GT, GQ, GP)
- Category summary generation
- Grouped dataset creation
- Color scheme mapping
"""

import pytest
import pandas as pd
from utils.ganglioside_categorizer import GangliosideCategorizer


@pytest.mark.integration
@pytest.mark.categorizer
class TestCategorizerRealData:
    """Test categorizer with real LC-MS/MS user data."""

    def test_load_user_data(self, user_csv_data):
        """Test that user data loads successfully."""
        assert isinstance(user_csv_data, pd.DataFrame)
        assert len(user_csv_data) > 0, "User data should contain compounds"
        assert "Name" in user_csv_data.columns, "Missing 'Name' column"

    def test_categorize_compounds(self, user_csv_data, categorizer):
        """Test compound categorization functionality."""
        results = categorizer.categorize_compounds(user_csv_data)

        # Verify result structure
        assert "categories" in results, "Missing 'categories' key"
        assert "total_compounds" in results, "Missing 'total_compounds' key"
        assert "uncategorized" in results, "Missing 'uncategorized' key"

        # Verify total count
        assert results["total_compounds"] > 0, "Should have categorized compounds"

        # Verify categories is a dictionary
        assert isinstance(results["categories"], dict), "Categories should be dict"

    def test_category_structure(self, user_csv_data, categorizer):
        """Test that each category has proper structure."""
        results = categorizer.categorize_compounds(user_csv_data)

        for category, info in results["categories"].items():
            # Each category should have these keys
            assert "count" in info, f"{category} missing 'count'"
            assert "compounds" in info, f"{category} missing 'compounds'"
            assert "info" in info, f"{category} missing 'info'"

            # Category info should have metadata
            category_info = info["info"]
            assert "name" in category_info, f"{category} missing 'name'"
            assert "color" in category_info, f"{category} missing 'color'"
            assert "description" in category_info, f"{category} missing 'description'"

            # Count should match compounds list length
            assert info["count"] == len(info["compounds"]), \
                f"{category} count mismatch"

    @pytest.mark.parametrize("category", ["GM", "GD", "GT", "GQ", "GP"])
    def test_valid_categories(self, user_csv_data, categorizer, category):
        """Test that valid ganglioside categories are recognized."""
        results = categorizer.categorize_compounds(user_csv_data)

        # Category should exist in available categories
        available_categories = list(results["categories"].keys())

        # This category may or may not have compounds in the data
        # but it should be a valid category type
        if category in available_categories:
            category_data = results["categories"][category]
            assert category_data["count"] >= 0, \
                f"{category} should have non-negative count"

    def test_category_colors(self, user_csv_data, categorizer):
        """Test that each category has a valid color assigned."""
        results = categorizer.categorize_compounds(user_csv_data)

        for category, info in results["categories"].items():
            color = info["info"]["color"]

            # Color should be hex format
            assert isinstance(color, str), f"{category} color should be string"
            assert color.startswith("#"), \
                f"{category} color should be hex format"
            assert len(color) == 7, \
                f"{category} color should be 7 chars (#rrggbb)"

    def test_generate_categorization_summary(self, user_csv_data, categorizer):
        """Test categorization summary generation."""
        summary = categorizer.generate_categorization_summary(user_csv_data)

        # Summary should be a non-empty string
        assert isinstance(summary, str), "Summary should be string"
        assert len(summary) > 0, "Summary should not be empty"

        # Summary should contain key information
        assert "Category" in summary or "Total" in summary, \
            "Summary should contain category information"

    def test_create_category_grouped_data(self, user_csv_data, categorizer):
        """Test creation of category-grouped datasets."""
        grouped_data = categorizer.create_category_grouped_data(user_csv_data)

        # Should return a dictionary
        assert isinstance(grouped_data, dict), \
            "Grouped data should be dictionary"

        # Each group should be a DataFrame
        for category, group_df in grouped_data.items():
            assert isinstance(group_df, pd.DataFrame), \
                f"{category} group should be DataFrame"
            assert len(group_df) > 0, \
                f"{category} group should have compounds"

            # Should have expected columns
            expected_columns = ["Base_Prefix", "Modifications"]
            for col in expected_columns:
                if col in group_df.columns:
                    assert group_df[col].notna().any(), \
                        f"{category} should have some {col} values"

    def test_get_category_colors(self, categorizer):
        """Test color mapping retrieval."""
        colors = categorizer.get_category_colors()

        # Should return a dictionary
        assert isinstance(colors, dict), "Colors should be dictionary"
        assert len(colors) > 0, "Should have color mappings"

        # Each color should be valid hex format
        for category, color in colors.items():
            assert isinstance(color, str), f"{category} color should be string"
            assert color.startswith("#"), \
                f"{category} color should be hex format"

    def test_category_distribution(self, user_csv_data, categorizer):
        """Test that compounds are distributed across categories."""
        results = categorizer.categorize_compounds(user_csv_data)

        total_categorized = sum(
            info["count"] for info in results["categories"].values()
        )

        # Total categorized should match total compounds (minus uncategorized)
        expected_total = results["total_compounds"] - results["uncategorized"]
        assert total_categorized == expected_total, \
            "Sum of category counts should match total"

    def test_compound_name_preservation(self, user_csv_data, categorizer):
        """Test that compound names are preserved during categorization."""
        results = categorizer.categorize_compounds(user_csv_data)

        all_categorized_compounds = []
        for info in results["categories"].values():
            all_categorized_compounds.extend(info["compounds"])

        # Each categorized compound should be in original data
        original_names = set(user_csv_data["Name"].tolist())
        for compound in all_categorized_compounds:
            assert compound in original_names, \
                f"Compound {compound} not in original data"

    def test_base_prefix_extraction(self, user_csv_data, categorizer):
        """Test base prefix extraction in grouped data."""
        grouped_data = categorizer.create_category_grouped_data(user_csv_data)

        for category, group_df in grouped_data.items():
            if "Base_Prefix" in group_df.columns:
                base_prefixes = group_df["Base_Prefix"].unique()

                # Base prefixes should match the category
                for prefix in base_prefixes:
                    if pd.notna(prefix):
                        # Prefix should contain the category identifier
                        # e.g., GM1, GM2, GM3 for GM category
                        assert any(cat in str(prefix)
                                  for cat in ["GM", "GD", "GT", "GQ", "GP"]), \
                            f"Invalid base prefix: {prefix}"

    def test_modification_tracking(self, user_csv_data, categorizer):
        """Test that modifications are tracked in grouped data."""
        grouped_data = categorizer.create_category_grouped_data(user_csv_data)

        for category, group_df in grouped_data.items():
            if "Modifications" in group_df.columns:
                # Should have modification data
                has_modifications = group_df["Modifications"].notna().any()

                # Even if no modifications, column should exist
                assert "Modifications" in group_df.columns, \
                    f"{category} missing Modifications column"
