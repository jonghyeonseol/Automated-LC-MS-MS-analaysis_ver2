"""
Ganglioside Categorization Module
Provides prefix-based categorization for ganglioside data visualization
"""

import re
import pandas as pd
from typing import Dict, List, Any, Tuple
from collections import defaultdict


class GangliosideCategorizer:
    """
    Categorizes gangliosides based on their prefix patterns for better visualization grouping.

    Examples:
    - GD1(34:1;O2) → Base: GD1, Category: GD (disialo)
    - GD1+dHex(36:1;O2) → Base: GD1, Category: GD (disialo), Modified: dHex
    - GM3+OAc(18:1;O2) → Base: GM3, Category: GM (monosialo), Modified: OAc
    """

    def __init__(self):
        # Define ganglioside categories based on sialic acid content
        self.ganglioside_categories = {
            'GM': {
                'name': 'Monosialogangliosides',
                'description': 'Gangliosides with 1 sialic acid',
                'color': '#1f77b4',  # Blue
                'subcategories': ['GM1', 'GM2', 'GM3', 'GM4']
            },
            'GD': {
                'name': 'Disialogangliosides',
                'description': 'Gangliosides with 2 sialic acids',
                'color': '#ff7f0e',  # Orange
                'subcategories': ['GD1', 'GD2', 'GD3']
            },
            'GT': {
                'name': 'Trisialogangliosides',
                'description': 'Gangliosides with 3 sialic acids',
                'color': '#2ca02c',  # Green
                'subcategories': ['GT1', 'GT2', 'GT3']
            },
            'GQ': {
                'name': 'Tetrasialogangliosides',
                'description': 'Gangliosides with 4 sialic acids',
                'color': '#d62728',  # Red
                'subcategories': ['GQ1', 'GQ2']
            },
            'GP': {
                'name': 'Pentasialogangliosides',
                'description': 'Gangliosides with 5 sialic acids',
                'color': '#9467bd',  # Purple
                'subcategories': ['GP1']
            }
        }

        # Modification patterns
        self.modification_patterns = {
            'OAc': 'O-acetylation',
            'dHex': 'Deoxyhexose (fucose)',
            'Hex': 'Hexose (glucose/galactose)',
            'HexNAc': 'N-acetylhexosamine',
            'NeuAc': 'N-acetylneuraminic acid',
            'NeuGc': 'N-glycolylneuraminic acid'
        }

        print("📊 Ganglioside Categorizer 초기화 완료")

    def extract_base_prefix(self, compound_name: str) -> Tuple[str, str, List[str]]:
        """
        Extract base prefix, category, and modifications from compound name

        Args:
            compound_name: e.g., "GD1+dHex+OAc(36:1;O2)"

        Returns:
            Tuple of (base_prefix, category, modifications)
            e.g., ("GD1", "GD", ["dHex", "OAc"])
        """
        # Remove lipid composition part (everything after opening parenthesis)
        base_name = compound_name.split('(')[0]

        # Extract base ganglioside (GM1, GD1, GT1, etc.)
        base_match = re.match(r'^([A-Z]{2}\d+)', base_name)
        if not base_match:
            return compound_name, 'Unknown', []

        base_prefix = base_match.group(1)

        # Determine category (GM, GD, GT, GQ, GP)
        category = base_prefix[:2]

        # Extract modifications (+dHex, +OAc, etc.)
        modifications = []
        mod_part = base_name[len(base_prefix):]

        if mod_part:
            # Handle multiple modifications like +dHex+OAc or +2OAc
            mod_matches = re.findall(r'\+(\d*)([A-Za-z]+)', mod_part)
            for count, mod in mod_matches:
                if count:
                    modifications.append(f"{count}{mod}")
                else:
                    modifications.append(mod)

        return base_prefix, category, modifications

    def categorize_compounds(self, df: pd.DataFrame, name_column: str = 'Name') -> Dict[str, Any]:
        """
        Categorize all compounds in the dataframe

        Args:
            df: DataFrame with compound data
            name_column: Column name containing compound names

        Returns:
            Dictionary with categorization results
        """
        categorization_results = {
            'categories': {},
            'base_prefixes': {},
            'modifications': defaultdict(list),
            'compound_mapping': {},
            'statistics': {}
        }

        category_counts = defaultdict(int)
        base_prefix_counts = defaultdict(int)
        modification_counts = defaultdict(int)

        # Process each compound - vectorized using apply
        def process_compound(row):
            compound_name = row[name_column]
            base_prefix, category, modifications = self.extract_base_prefix(compound_name)
            return {
                'compound_name': compound_name,
                'base_prefix': base_prefix,
                'category': category,
                'modifications': modifications,
                'index': row.name  # DataFrame index
            }

        # Apply to all rows at once
        results = df.apply(process_compound, axis=1)

        # Build compound mapping and counts from results
        for result in results:
            compound_name = result['compound_name']
            categorization_results['compound_mapping'][compound_name] = {
                'base_prefix': result['base_prefix'],
                'category': result['category'],
                'modifications': result['modifications'],
                'index': result['index']
            }

            # Update counts
            category_counts[result['category']] += 1
            base_prefix_counts[result['base_prefix']] += 1
            for mod in result['modifications']:
                modification_counts[mod] += 1

        # Organize by categories
        for category in category_counts:
            if category in self.ganglioside_categories:
                categorization_results['categories'][category] = {
                    'info': self.ganglioside_categories[category],
                    'count': category_counts[category],
                    'compounds': []
                }
            else:
                categorization_results['categories'][category] = {
                    'info': {
                        'name': f'{category} Gangliosides',
                        'description': f'Gangliosides with {category} prefix',
                        'color': '#888888',
                        'subcategories': []
                    },
                    'count': category_counts[category],
                    'compounds': []
                }

        # Add compounds to their categories
        for compound_name, info in categorization_results['compound_mapping'].items():
            category = info['category']
            if category in categorization_results['categories']:
                categorization_results['categories'][category]['compounds'].append(compound_name)

        # Store base prefix counts
        categorization_results['base_prefixes'] = dict(base_prefix_counts)
        categorization_results['modifications'] = dict(modification_counts)

        # Generate statistics
        categorization_results['statistics'] = {
            'total_compounds': len(df),
            'total_categories': len(category_counts),
            'total_base_prefixes': len(base_prefix_counts),
            'total_modifications': len(modification_counts),
            'most_common_category': max(category_counts, key=category_counts.get) if category_counts else None,
            'most_common_base_prefix': (max(base_prefix_counts, key=base_prefix_counts.get)
                                        if base_prefix_counts else None)
        }

        return categorization_results

    def create_category_grouped_data(self, df: pd.DataFrame, name_column: str = 'Name') -> Dict[str, pd.DataFrame]:
        """
        Create separate DataFrames for each category

        Args:
            df: Original DataFrame
            name_column: Column name containing compound names

        Returns:
            Dictionary mapping category names to their DataFrames
        """
        categorization = self.categorize_compounds(df, name_column)
        grouped_data = {}

        for category, info in categorization['categories'].items():
            # Get indices of compounds in this category
            compound_names = info['compounds']
            mask = df[name_column].isin(compound_names)
            grouped_data[category] = df[mask].copy()

            # Add categorization info to the DataFrame
            grouped_data[category]['Category'] = category
            grouped_data[category]['Base_Prefix'] = grouped_data[category][name_column].apply(
                lambda x: categorization['compound_mapping'][x]['base_prefix']
            )
            grouped_data[category]['Modifications'] = grouped_data[category][name_column].apply(
                lambda x: ', '.join(categorization['compound_mapping'][x]['modifications']) or 'None'
            )

        return grouped_data

    def get_category_colors(self) -> Dict[str, str]:
        """Return color mapping for categories"""
        return {cat: info['color'] for cat, info in self.ganglioside_categories.items()}

    def generate_categorization_summary(self, df: pd.DataFrame, name_column: str = 'Name') -> str:
        """
        Generate a human-readable summary of the categorization

        Args:
            df: DataFrame with compound data
            name_column: Column name containing compound names

        Returns:
            Formatted summary string
        """
        categorization = self.categorize_compounds(df, name_column)
        stats = categorization['statistics']

        summary = f"""
📊 GANGLIOSIDE CATEGORIZATION SUMMARY
====================================

📈 Overall Statistics:
- Total Compounds: {stats['total_compounds']}
- Categories Found: {stats['total_categories']}
- Base Prefixes: {stats['total_base_prefixes']}
- Modifications: {stats['total_modifications']}

🏆 Most Common:
- Category: {stats['most_common_category']}
- Base Prefix: {stats['most_common_base_prefix']}

📋 Category Breakdown:"""

        for category, info in categorization['categories'].items():
            category_info = info['info']
            summary += f"\n- {category}: {info['count']} compounds ({category_info['name']})"

        summary += "\n\n🔧 Base Prefix Distribution:"
        for base_prefix, count in sorted(categorization['base_prefixes'].items(), key=lambda x: x[1], reverse=True):
            summary += f"\n- {base_prefix}: {count} compounds"

        if categorization['modifications']:
            summary += "\n\n⚗️ Modifications Found:"
            for mod, count in sorted(categorization['modifications'].items(), key=lambda x: x[1], reverse=True):
                mod_desc = self.modification_patterns.get(mod, 'Unknown modification')
                summary += f"\n- {mod}: {count} compounds ({mod_desc})"

        return summary


def test_categorizer():
    """Test function for the categorizer"""
    import pandas as pd

    # Sample data
    test_data = {
        'Name': [
            'GD1(34:1;O2)',
            'GD1+dHex(36:1;O2)',
            'GM3+OAc(18:1;O2)',
            'GT1(40:1;O2)',
            'GQ1+2OAc(38:1;O2)',
            'GM1(36:1;O2)'
        ],
        'RT': [7.5, 9.5, 5.2, 12.1, 14.8, 8.3],
        'Log P': [0.44, 0.43, 2.1, 3.15, 4.2, 1.53]
    }

    df = pd.DataFrame(test_data)
    categorizer = GangliosideCategorizer()

    # Test categorization
    categorizer.categorize_compounds(df)
    print(categorizer.generate_categorization_summary(df))

    # Test grouped data
    grouped = categorizer.create_category_grouped_data(df)
    print(f"\n📊 Created {len(grouped)} category groups:")
    for category, group_df in grouped.items():
        print(f"- {category}: {len(group_df)} compounds")


if __name__ == "__main__":
    test_categorizer()
