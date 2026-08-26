from __future__ import annotations

import uuid

from packages.db.enums import IdentifierType, MatchType
from packages.entities.stages import attributes, fuzzy, identifier, string_match
from packages.entities.types import StageOutcome, VariantView


def _variant(**overrides) -> VariantView:
    base = dict(
        id=uuid.uuid4(),
        title_raw="test title",
        title_language="ja",
        brand_raw=None,
        identifier_type=IdentifierType.NONE,
        identifier_value=None,
        model_number=None,
        dimensions_mm=None,
        weight_g=None,
        capacity=None,
        material=None,
        color=None,
        pack_quantity=None,
    )
    base.update(overrides)
    return VariantView(**base)


class TestIdentifierStage:
    def test_same_jan_is_exact(self):
        left = _variant(identifier_type=IdentifierType.JAN, identifier_value="4901165304236")
        right = _variant(identifier_type=IdentifierType.JAN, identifier_value="4901165304236")
        result = identifier.run(left, right)
        assert result.outcome == StageOutcome.DECIDED
        assert result.match_type == MatchType.EXACT
        assert result.confidence == 1.0

    def test_different_jan_same_type_is_rejected(self):
        left = _variant(identifier_type=IdentifierType.JAN, identifier_value="4901165304236")
        right = _variant(identifier_type=IdentifierType.JAN, identifier_value="4901165102597")
        result = identifier.run(left, right)
        assert result.outcome == StageOutcome.DECIDED
        assert result.match_type == MatchType.REJECTED

    def test_no_identifier_is_inconclusive(self):
        result = identifier.run(_variant(), _variant())
        assert result.outcome == StageOutcome.INCONCLUSIVE

    def test_never_produces_likely(self):
        # Stage 1 is the identifier stage; it may only ever assert EXACT or
        # REJECTED, never a softer LIKELY (ADR-0002 reserves EXACT here).
        left = _variant(identifier_type=IdentifierType.JAN, identifier_value="123")
        right = _variant(identifier_type=IdentifierType.JAN, identifier_value="123")
        result = identifier.run(left, right)
        assert result.match_type in (MatchType.EXACT, MatchType.REJECTED, None)


class TestAttributesStage:
    def test_same_model_number_is_likely_not_exact(self):
        left = _variant(model_number="JNL-450")
        right = _variant(model_number="jnl450")  # normalization should equate these
        result = attributes.run(left, right)
        assert result.outcome == StageOutcome.DECIDED
        assert result.match_type == MatchType.LIKELY  # ADR-0002: never EXACT here

    def test_different_model_number_is_rejected(self):
        left = _variant(model_number="JNL-450")
        right = _variant(model_number="JNL-481")
        result = attributes.run(left, right)
        assert result.outcome == StageOutcome.DECIDED
        assert result.match_type == MatchType.REJECTED

    def test_missing_model_number_both_sides_falls_through(self):
        result = attributes.run(_variant(), _variant())
        assert result.outcome == StageOutcome.INCONCLUSIVE

    def test_close_dimensions_and_weight_is_weaker_likely(self):
        left = _variant(dimensions_mm={"l": 165, "w": 22, "h": 12}, weight_g=35)
        right = _variant(dimensions_mm={"l": 166, "w": 22, "h": 12}, weight_g=36)
        result = attributes.run(left, right)
        assert result.outcome == StageOutcome.DECIDED
        assert result.match_type == MatchType.LIKELY
        assert result.confidence < 0.9  # weaker signal than a model_number match


class TestStringAndFuzzyStagesNeverReject:
    def test_string_stage_zero_overlap_is_inconclusive_not_rejected(self):
        left = _variant(title_raw="オルファ 別たち 43B 皮革用ナイフ")
        right = _variant(title_raw="스테인리스 주방가위")
        result = string_match.run(left, right)
        assert result.outcome == StageOutcome.INCONCLUSIVE
        assert result.match_type is None

    def test_fuzzy_stage_low_similarity_is_inconclusive_not_rejected(self):
        left = _variant(title_raw="completely different text alpha")
        right = _variant(title_raw="totally unrelated words beta")
        result = fuzzy.run(left, right)
        assert result.outcome == StageOutcome.INCONCLUSIVE
        assert result.match_type is None
