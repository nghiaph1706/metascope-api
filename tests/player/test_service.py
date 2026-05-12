"""Tests for player service — unit tests for helper functions."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.player import service


class TestStatsCacheKey:
    """Tests for _stats_cache_key."""

    def test_cache_key_format(self) -> None:
        """Cache key uses puuid in format."""
        key = service._stats_cache_key("abc123")
        assert "abc123" in key
        assert "player_stats" in key


class TestAnalysisCacheKey:
    """Tests for _analysis_cache_key."""

    def test_cache_key_format(self) -> None:
        """Cache key uses puuid in format."""
        key = service._analysis_cache_key("xyz789")
        assert "xyz789" in key
        assert "player_analysis" in key


class TestIsFresh:
    """Tests for _is_fresh helper."""

    def test_returns_false_when_no_last_fetched(self) -> None:
        """Returns False when last_fetched_at is None."""
        player = MagicMock()
        player.last_fetched_at = None
        assert service._is_fresh(player) is False

    def test_returns_true_when_recent(self) -> None:
        """Returns True when age is under threshold."""
        player = MagicMock()
        player.last_fetched_at = datetime.now(UTC)
        assert service._is_fresh(player) is True

    def test_returns_false_when_old(self) -> None:
        """Returns False when age exceeds threshold."""
        player = MagicMock()
        player.last_fetched_at = datetime(2020, 1, 1, tzinfo=UTC)
        assert service._is_fresh(player, max_age_seconds=1800) is False

    def test_default_max_age_is_30_minutes(self) -> None:
        """Default max age is 1800 seconds (30 minutes)."""
        player = MagicMock()
        # 25 minutes ago — should be fresh with default
        player.last_fetched_at = datetime.now(UTC)
        assert service._is_fresh(player) is True


class TestComputeTrend:
    """Tests for _compute_trend helper."""

    def test_returns_stable_with_fewer_than_5_matches(self) -> None:
        """Returns 'stable' when less than 5 matches."""
        mock_participants = [MagicMock(placement=1)] * 4
        assert service._compute_trend(mock_participants) == "stable"

    def test_returns_stable_when_exactly_5_matches(self) -> None:
        """Returns 'stable' when exactly 5 matches (minimum for trend)."""
        mock_participants = [MagicMock(placement=1)] * 5
        assert service._compute_trend(mock_participants) == "stable"

    def test_returns_improving_when_second_half_wins_more(self) -> None:
        """Returns 'improving' when recent half outperforms older by >= 10%."""
        # Older half (indices 5-9): placement 5 = 0 wins
        older = [MagicMock(placement=5)] * 5
        # Recent half (indices 0-4): placement 1 = 2 wins (40%)
        recent = [MagicMock(placement=1), MagicMock(placement=1)] + [MagicMock(placement=5)] * 3
        participants = recent + older

        result = service._compute_trend(participants)
        assert result == "improving"

    def test_returns_declining_when_first_half_wins_more(self) -> None:
        """Returns 'declining' when older half outperforms recent by >= 10%."""
        # Older half: 2 wins
        older = [MagicMock(placement=1), MagicMock(placement=1)] + [MagicMock(placement=5)] * 3
        # Recent half: 0 wins
        recent = [MagicMock(placement=5)] * 5
        participants = recent + older

        result = service._compute_trend(participants)
        assert result == "declining"


class TestCompDisplayName:
    """Tests for _comp_display_name helper."""

    def test_trait_based_name(self) -> None:
        """Trait-based comps get clean display name."""
        name = service._comp_display_name("trait:['Set13_Void', 'Set13_Sorcerer']")
        assert " / " in name
        assert "Void" in name

    def test_unit_fallback_name(self) -> None:
        """Unit-based comps show 'Units:' prefix."""
        name = service._comp_display_name("unit:frozenset({'a', 'b', 'c'})")
        assert name.startswith("Units:")

    def test_empty_trait_list(self) -> None:
        """Returns 'Unknown Comp' when trait list is empty."""
        name = service._comp_display_name("trait:[]")
        assert name == "Unknown Comp"


class TestDetectStrengthsWeaknesses:
    """Tests for _detect_strengths_weaknesses helper."""

    def test_empty_participants(self) -> None:
        """Handles empty participant list — returns empty strengths/weaknesses."""
        strengths, weaknesses = service._detect_strengths_weaknesses([], [], [])
        assert strengths == []
        assert weaknesses == []

    def test_high_win_rate_creates_strength(self) -> None:
        """Win rate >= 12% adds a strength."""
        participants = [MagicMock(placement=1, level=8, gold_left=10)] * 20
        strengths, weaknesses = service._detect_strengths_weaknesses(participants, [], [])
        assert any("win rate" in s.lower() for s in strengths)

    def test_low_win_rate_creates_weakness(self) -> None:
        """Win rate < 6% adds a weakness."""
        participants = [MagicMock(placement=5, level=8, gold_left=10)] * 100
        strengths, weaknesses = service._detect_strengths_weaknesses(participants, [], [])
        assert any("win rate" in w.lower() for w in weaknesses)

    def test_low_top4_rate_creates_weakness(self) -> None:
        """Top 4 rate < 35% adds a weakness."""
        participants = [MagicMock(placement=5, level=8, gold_left=10)] * 50
        strengths, weaknesses = service._detect_strengths_weaknesses(participants, [], [])
        assert any("top 4" in w.lower() for w in weaknesses)

    def test_high_avg_level_creates_strength(self) -> None:
        """Avg level >= 8.5 adds a strength."""
        participants = [MagicMock(placement=3, level=9, gold_left=10)] * 10
        strengths, weaknesses = service._detect_strengths_weaknesses(participants, [], [])
        assert any("level" in s.lower() for s in strengths)

    def test_low_gold_left_creates_strength(self) -> None:
        """Avg gold left <= 10 creates a strength."""
        participants = [MagicMock(gold_left=5, level=8, placement=3)] * 10
        strengths, weaknesses = service._detect_strengths_weaknesses(participants, [], [])
        assert any("gold" in s.lower() for s in strengths)

    def test_underperforming_comp_adds_weakness(self) -> None:
        """Comp with < 8% win rate adds a weakness."""
        mock_comp = MagicMock()
        mock_comp.name = "TestComp"
        mock_comp.win_rate = 0.05
        participants = [MagicMock(level=8, placement=4, gold_left=10) for _ in range(20)]
        strengths, weaknesses = service._detect_strengths_weaknesses(participants, [mock_comp], [])
        assert any("comp" in w.lower() for w in weaknesses)


class TestAggregatePreferredTraits:
    """Tests for _aggregate_preferred_traits helper."""

    def test_empty_participants(self) -> None:
        """Returns empty list for no participants."""
        result = service._aggregate_preferred_traits([])
        assert result == []

    def test_returns_top_5_traits(self) -> None:
        """Returns at most 5 most-used traits."""
        participants = [
            MagicMock(
                traits_active=[
                    {"name": "Sorcerer", "tier_current": 3},
                    {"name": "Void", "tier_current": 2},
                ]
            )
            for _ in range(10)
        ]
        result = service._aggregate_preferred_traits(participants)
        assert len(result) <= 5

    def test_ignores_zero_tier_traits(self) -> None:
        """Ignores traits with tier_current == 0."""
        participants = [
            MagicMock(
                traits_active=[
                    {"name": "Sorcerer", "tier_current": 0},
                    {"name": "Void", "tier_current": 2},
                ]
            )
        ]
        result = service._aggregate_preferred_traits(participants)
        assert "Sorcerer" not in result
        assert "Void" in result
