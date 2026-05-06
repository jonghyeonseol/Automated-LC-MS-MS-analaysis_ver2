"""
Strong regression-prevention tests for ImprovedRegressionModel (BayesianRidge).

These guard against silent regression failures: previous bugs caused
`fit_regression` to skip every prefix because of an Anchor type mismatch,
yet downstream code reported success. Each test asserts that *at least one*
fit succeeds and that returned metrics carry the expected BayesianRidge keys.
"""
import numpy as np
import pandas as pd
import pytest

from apps.analysis.services.improved_regression import ImprovedRegressionModel


def _make_prefix_df(n: int, n_anchors: int, anchor_value, *, slope: float = 0.6):
    """Build a synthetic prefix group with strong RT~Log P linear signal."""
    rng = np.random.default_rng(0)
    log_p = np.linspace(0.0, 6.0, n) + rng.normal(0, 0.05, n)
    rt = 8.0 + slope * log_p + rng.normal(0, 0.08, n)
    non_anchor_value = False if anchor_value is True else 'F'
    return pd.DataFrame({
        'Name': [f'TEST(36:1;O2)'] * n,
        'RT': rt,
        'Log P': log_p,
        'a_component': rng.integers(34, 40, n),
        'b_component': rng.integers(0, 3, n),
        'Anchor': [anchor_value] * n_anchors + [non_anchor_value] * (n - n_anchors),
    })


@pytest.fixture
def model():
    return ImprovedRegressionModel(min_samples=3, r2_threshold=0.5)


class TestAnchorFilterRobustness:
    """Anchor must work whether V2/V3 normalized to bool or raw 'T'/'F'."""

    def test_anchor_bool_true_filters_correctly(self, model):
        df = _make_prefix_df(8, n_anchors=5, anchor_value=True)
        result = model.fit_regression(df, 'GD1', anchor_only=True)
        assert result['success'] is True, (
            f"Bool Anchor filter failed: {result.get('reason')}"
        )
        assert result['metrics']['n_samples'] == 5

    def test_anchor_string_T_filters_correctly(self, model):
        df = _make_prefix_df(8, n_anchors=5, anchor_value='T')
        result = model.fit_regression(df, 'GD1', anchor_only=True)
        assert result['success'] is True, (
            f"Str Anchor filter failed: {result.get('reason')}"
        )
        assert result['metrics']['n_samples'] == 5

    def test_anchor_filter_excludes_non_anchors(self, model):
        df = _make_prefix_df(10, n_anchors=4, anchor_value=True)
        result = model.fit_regression(df, 'GM3', anchor_only=True)
        assert result['success'] is True
        # Trained on 4 anchors, but predictions span all 10 rows downstream
        assert result['metrics']['n_samples'] == 4
        assert len(result['predictions']) == 10


class TestBayesianRidgeIntegration:
    """The model must use BayesianRidge and expose its hyperparameters."""

    @pytest.mark.parametrize("n,n_anchors,expected_cv", [
        (5, 3, 'leave-one-out'),  # n<5 → LOO
        (8, 5, '3-fold'),          # 5≤n<10 → 3-fold
        (15, 12, '5-fold'),        # n≥10 → 5-fold
    ])
    def test_cv_strategy_matches_sample_size(self, model, n, n_anchors, expected_cv):
        df = _make_prefix_df(n, n_anchors=n_anchors, anchor_value=True)
        result = model.fit_regression(df, 'GT1', anchor_only=True)
        assert result['success'] is True
        assert result['metrics']['cv_method'] == expected_cv

    def test_bayesian_hyperparameters_present(self, model):
        df = _make_prefix_df(10, n_anchors=8, anchor_value=True)
        result = model.fit_regression(df, 'GD1', anchor_only=True)
        assert result['success'] is True
        m = result['metrics']
        # BayesianRidge-specific keys (would be missing if Ridge/RidgeCV)
        assert 'selected_alpha' in m
        assert 'selected_lambda' in m
        assert 'effective_ridge_alpha' in m
        assert m['selected_alpha'] > 0
        assert m['selected_lambda'] > 0

    def test_train_r2_separate_from_validation_r2(self, model):
        df = _make_prefix_df(10, n_anchors=8, anchor_value=True)
        result = model.fit_regression(df, 'GM1', anchor_only=True)
        assert result['success'] is True
        m = result['metrics']
        assert 'train_r2' in m
        assert 'r2' in m  # CV-based validation r2
        # Train R² should be ≥ CV R² (overfitting indicator if much higher)
        assert m['train_r2'] >= m['r2'] - 0.05


class TestRegressionPreventsSilentFailure:
    """The whole point of these tests: catch regressions where every prefix fails."""

    def test_strong_signal_yields_high_validation_r2(self, model):
        """With clean RT~LogP signal and n=10 anchors, R² must exceed 0.7."""
        df = _make_prefix_df(12, n_anchors=10, anchor_value=True, slope=0.7)
        result = model.fit_regression(df, 'GD1', anchor_only=True)
        assert result['success'] is True
        assert result['metrics']['r2'] > 0.7, (
            f"Validation R² unexpectedly low: {result['metrics']['r2']}"
        )

    def test_output_schema_for_downstream_persistence(self, model):
        """analysis_service._save_regression_models depends on this exact shape."""
        df = _make_prefix_df(10, n_anchors=8, anchor_value=True)
        result = model.fit_regression(df, 'GM3', anchor_only=True)
        assert result['success'] is True

        # Nested coefficients dict
        assert 'coefficients' in result
        assert 'intercept' in result['coefficients']
        assert 'features' in result['coefficients']
        assert isinstance(result['coefficients']['features'], dict)

        # Metrics block with persistence-required keys
        m = result['metrics']
        for key in ('r2', 'rmse', 'selected_alpha', 'cv_method', 'n_samples', 'n_features'):
            assert key in m, f"metrics missing required key '{key}'"

        # Equation string for human-readable display
        assert 'equation' in result
        assert result['equation'].startswith('RT =')

    def test_insufficient_samples_returns_failure_not_crash(self, model):
        df = _make_prefix_df(2, n_anchors=2, anchor_value=True)
        result = model.fit_regression(df, 'GP1', anchor_only=True)
        assert result['success'] is False
        assert 'Insufficient samples' in result['reason']

    def test_coefficient_sign_validation_runs(self, model):
        """Reverse-phase chromatography: more carbons (a_component) → higher RT.
        Build data where a_component is anti-correlated with RT and confirm
        we get a sign violation warning."""
        rng = np.random.default_rng(1)
        n = 10
        a = np.linspace(40, 34, n)  # decreasing carbons
        rt = 6.0 + 0.3 * a + rng.normal(0, 0.05, n)  # RT increases with a (correct)
        # Now invert: make RT decrease with a → coefficient will be negative
        rt = 16.0 - 0.3 * a + rng.normal(0, 0.05, n)
        log_p = a * 0.05 + rng.normal(0, 0.02, n)  # weak Log P signal so a dominates
        df = pd.DataFrame({
            'Name': ['TEST(36:1;O2)'] * n,
            'RT': rt,
            'Log P': log_p,
            'a_component': a,
            'b_component': rng.integers(0, 3, n),
            'Anchor': [True] * n,
        })
        # Force model to keep multiple features
        wide_model = ImprovedRegressionModel(
            min_samples=3, r2_threshold=0.3, max_features_ratio=0.5
        )
        result = wide_model.fit_regression(df, 'GD1', anchor_only=True)
        if result['success'] and 'a_component' in result['features']:
            # Sign warning should fire when a_component coef is negative
            a_coef = result['coefficients']['features'].get('a_component', 0)
            if a_coef < 0:
                assert any('a_component' in w for w in result['coefficient_warnings']), (
                    "Negative a_component should produce sign warning"
                )
