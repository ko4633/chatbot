from core.product_code_parser import parse_product_code, load_rules

RULES = load_rules()


def test_known_code_ka_new_season():
    result = parse_product_code("TCNKA26F841104", RULES)
    assert result.internal_category_code == "KA"
    assert result.internal_category_name == "사파리"
    assert result.season_code == "26F"
    assert result.season_label == "2026 신상 Fall"
    assert result.carryover is False
    assert result.size_rule_group is None  # KA는 EIGHT_SIZE_WAIST 그룹 아님


def test_known_code_fu_carryover_season():
    result = parse_product_code("TRNFU5F641609", RULES)
    assert result.internal_category_code == "FU"
    assert result.internal_category_name == "자켓"
    assert result.season_code == "5F"
    assert result.carryover is True
    assert result.size_rule_group is None


def test_dl_maps_to_eight_size_group():
    result = parse_product_code("ABCDL26F123456", RULES)
    assert result.internal_category_code == "DL"
    assert result.size_rule_group == "EIGHT_SIZE_WAIST"


def test_unknown_type_code_is_not_guessed():
    result = parse_product_code("ZZZQQ99X999999", RULES)
    assert result.internal_category_code == "UNKNOWN"
    assert result.internal_category_name == "UNKNOWN"
    assert result.season_code == "UNKNOWN"


def test_known_type_but_unknown_season_partial_success():
    result = parse_product_code("TCNKA99Z841104", RULES)
    assert result.internal_category_code == "KA"  # 상품종류는 인식됨
    assert result.season_code == "UNKNOWN"  # 시즌은 모르는 코드라 UNKNOWN
