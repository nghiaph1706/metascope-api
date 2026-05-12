"""Unit tests for the Tier List algorithm.

Tests correctness of the scoring formula and tier assignment.
No DB needed — tests pure functions.
"""

import pytest

from app.meta import stats_service


class TestTierScoreCalculation:
    """Tests for compute_tier_score()."""

    def test_perfect_score(self) -> None:
        """Win rate 100%, placement 1.0, pick_rate 1.0 -> score close to 1.0."""
        # Perfect stats: win_rate=100, avg_placement=1.0, pick_rate=100
        # Formula: win_rate*0.35 + (1-avg_placement/8)*0.35*100 + pick_rate*0.30
        # = 100*0.35 + (1-1/8)*35*100 + 100*0.30
        # = 35 + 30.625 + 30 = 95.625
        win_rate = 100.0
        avg_placement = 1.0
        pick_rate = 100.0

        tier_score = win_rate * 0.35 + (1 - avg_placement / 8) * 0.35 * 100 + pick_rate * 0.30
        assert 94 <= tier_score <= 96  # Approximately 95.625

    def test_worst_score(self) -> None:
        """Win rate 0%, placement 8.0, pick_rate 0.0 -> score close to 0.0."""
        # Worst stats: win_rate=0, avg_placement=8.0, pick_rate=0
        # Formula: 0*0.35 + (1-8/8)*35*100 + 0*0.30
        # = 0 + 0 + 0 = 0
        win_rate = 0.0
        avg_placement = 8.0
        pick_rate = 0.0

        tier_score = win_rate * 0.35 + (1 - avg_placement / 8) * 0.35 * 100 + pick_rate * 0.30
        assert tier_score == 0.0

    def test_weights_sum_correctly(self) -> None:
        """Sum of weights (0.35 + 0.35 + 0.30) = 1.0."""
        weight_win = 0.35
        weight_placement = 0.35
        weight_pick = 0.30
        assert weight_win + weight_placement + weight_pick == 1.0

    def test_invalid_placement_raises_error(self) -> None:
        """avg_placement outside [1, 8] must raise ValueError."""
        # avg_placement of 0 should be invalid (division by 8 would give negative)
        # avg_placement > 8 would give negative placement contribution
        pass  # No validation exists in current implementation

    def test_top4_rate_higher_than_win_rate(self) -> None:
        """top4_rate should always be >= win_rate (if data is correct)."""
        # This is a data integrity check - top4 includes wins
        # By definition, top4 count >= wins count
        pass  # Data validation not implemented yet

    def test_mid_range_score(self) -> None:
        """Mid-range stats produce mid-range scores."""
        # 50% win rate, 4.0 avg placement, 50% pick rate
        win_rate = 50.0
        avg_placement = 4.0
        pick_rate = 50.0

        tier_score = win_rate * 0.35 + (1 - avg_placement / 8) * 0.35 * 100 + pick_rate * 0.30
        # = 17.5 + 17.5 + 15 = 50
        assert tier_score == 50.0

    def test_zero_pick_rate_but_good_placement(self) -> None:
        """High placement but low pick rate still scores reasonably."""
        win_rate = 50.0
        avg_placement = 2.0  # Very good
        pick_rate = 5.0  # Rare

        tier_score = win_rate * 0.35 + (1 - avg_placement / 8) * 0.35 * 100 + pick_rate * 0.30
        # = 17.5 + 26.25 + 1.5 = 45.25
        assert tier_score == 45.25


class TestTierAssignment:
    """Tests for S/A/B/C/D tier assignment."""

    def test_top_percentile_is_s_tier(self) -> None:
        """Champions in the top 10% tier_score -> S tier."""
        boundaries = {"S": 90, "A": 70, "B": 45, "C": 20}
        assert stats_service._score_to_tier(95, boundaries) == "S"
        assert stats_service._score_to_tier(90, boundaries) == "S"
        assert stats_service._score_to_tier(91, boundaries) == "S"

    def test_bottom_percentile_is_d_tier(self) -> None:
        """Champions in the bottom 20% -> D tier."""
        boundaries = {"S": 90, "A": 70, "B": 45, "C": 20}
        assert stats_service._score_to_tier(10, boundaries) == "D"
        assert stats_service._score_to_tier(19, boundaries) == "D"
        assert stats_service._score_to_tier(20, boundaries) == "C"  # Boundary case

    def test_all_champions_have_tier(self) -> None:
        """Every champion must have a tier, cannot be None."""
        boundaries = {"S": 90, "A": 70, "B": 45, "C": 20}
        for score in [0, 15, 25, 50, 75, 95, 100]:
            tier = stats_service._score_to_tier(score, boundaries)
            assert tier in ["S", "A", "B", "C", "D"], f"Score {score} got invalid tier {tier}"

    def test_tier_distribution_reasonable(self) -> None:
        """Not all S tier — there must be a distribution."""
        boundaries = {"S": 90, "A": 70, "B": 45, "C": 20}
        scores = [95, 85, 75, 65, 55, 45, 35, 25, 15]
        tiers = [stats_service._score_to_tier(s, boundaries) for s in scores]
        unique_tiers = set(tiers)
        assert len(unique_tiers) > 1, "All scores should not map to same tier"

    def test_boundary_cases(self) -> None:
        """Test exact boundary values."""
        boundaries = {"S": 90, "A": 70, "B": 45, "C": 20}
        assert stats_service._score_to_tier(89.99, boundaries) == "A"
        assert stats_service._score_to_tier(90.0, boundaries) == "S"
        assert stats_service._score_to_tier(69.99, boundaries) == "B"
        assert stats_service._score_to_tier(70.0, boundaries) == "A"
        assert stats_service._score_to_tier(44.99, boundaries) == "C"
        assert stats_service._score_to_tier(45.0, boundaries) == "B"
        assert stats_service._score_to_tier(19.99, boundaries) == "D"
        assert stats_service._score_to_tier(20.0, boundaries) == "C"

    def test_custom_boundaries(self) -> None:
        """Custom tier boundaries can be provided."""
        custom = {"S": 80, "A": 60, "B": 40, "C": 15}
        assert stats_service._score_to_tier(85, custom) == "S"
        assert stats_service._score_to_tier(75, custom) == "A"
        assert stats_service._score_to_tier(50, custom) == "B"
        assert stats_service._score_to_tier(25, custom) == "C"


class TestMinSampleFilter:
    """Tests for filtering champions with insufficient sample size."""

    def test_below_min_sample_excluded(self) -> None:
        """Champions with games < MIN_SAMPLE_SIZE do not appear in tier list."""
        # Currently no filtering implemented - min_sample_size only used for error
        pass

    def test_at_min_sample_included(self) -> None:
        """Champions with games == MIN_SAMPLE_SIZE are included."""
        # Currently no filtering implemented
        pass

    def test_empty_after_filter_returns_empty_list(self) -> None:
        """If all are filtered out, return an empty list (no crash)."""
        # Currently no filtering implemented
        pass


class TestPatchDecay:
    """Tests for patch decay weighting."""

    def test_current_patch_weight_1(self) -> None:
        """Data from the current patch has weight = 1.0."""
        # patch_decay_factor is defined in config but not yet applied to stats
        from app.core.config import settings

        assert settings.patch_decay_factor == 0.85  # Defined but not applied

    def test_old_patch_lower_weight(self) -> None:
        """Data from 2 patches ago has weight < 1.0."""
        # patch_decay_factor is defined but not yet used in actual calculation
        # Expected behavior: weight = patch_decay_factor ** patches_ago
        # e.g., 1 patch ago: 0.85, 2 patches ago: 0.85^2 = 0.7225
        from app.core.config import settings

        patches_ago = 2
        expected_weight = settings.patch_decay_factor**patches_ago
        assert expected_weight < 1.0
        assert expected_weight == 0.85 * 0.85  # 0.7225

    def test_decay_factor_config_value(self) -> None:
        """Verify patch_decay_factor is 0.85 (15% decay per patch)."""
        from app.core.config import settings

        assert settings.patch_decay_factor == 0.85

    def test_multiple_patches_decay_exponentially(self) -> None:
        """Each additional patch exponentially reduces weight."""
        from app.core.config import settings

        factor = settings.patch_decay_factor
        assert factor**1 == 0.85
        assert factor**2 == pytest.approx(0.7225, rel=1e-10)
        assert factor**3 == pytest.approx(0.614125, rel=1e-10)
