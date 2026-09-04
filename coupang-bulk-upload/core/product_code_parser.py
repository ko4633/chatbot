import json
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "product_code_rules.json"

UNKNOWN = "UNKNOWN"


@dataclass
class ParsedProductCode:
    product_code: str
    internal_category_code: str  # 예: "KA" 또는 UNKNOWN
    internal_category_name: str  # 예: "사파리" 또는 UNKNOWN
    season_code: str  # 예: "26F" 또는 UNKNOWN
    season_label: str  # 예: "2026 신상 Fall" 또는 UNKNOWN
    carryover: bool | None  # 알 수 없으면 None
    size_rule_group: str | None  # 예: "EIGHT_SIZE_WAIST", 매칭 안되면 None(=default 규칙 사용)


def load_rules(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def _find_type_code(code: str, type_codes: dict[str, str]) -> tuple[int, str] | None:
    best: tuple[int, str] | None = None
    for candidate in type_codes:
        idx = code.find(candidate)
        if idx == -1:
            continue
        if best is None or idx < best[0] or (idx == best[0] and len(candidate) > len(best[1])):
            best = (idx, candidate)
    return best


def _find_season_code(remainder: str, season_codes: dict[str, dict]) -> str | None:
    for candidate in sorted(season_codes.keys(), key=len, reverse=True):
        if remainder.startswith(candidate):
            return candidate
    return None


def _rule_group_for(type_code: str, size_rule_groups: dict[str, list[str]]) -> str | None:
    for group_name, codes in size_rule_groups.items():
        if type_code in codes:
            return group_name
    return None


def parse_product_code(product_code: str, rules: dict | None = None) -> ParsedProductCode:
    rules = rules or load_rules()
    type_codes = rules["productTypeCodes"]
    season_codes = rules["seasonCodes"]
    size_rule_groups = rules["sizeRuleGroups"]

    type_match = _find_type_code(product_code, type_codes)
    if type_match is None:
        return ParsedProductCode(
            product_code=product_code,
            internal_category_code=UNKNOWN,
            internal_category_name=UNKNOWN,
            season_code=UNKNOWN,
            season_label=UNKNOWN,
            carryover=None,
            size_rule_group=None,
        )

    idx, type_code = type_match
    internal_category_name = type_codes[type_code]
    remainder = product_code[idx + len(type_code):]

    season_code = _find_season_code(remainder, season_codes)
    if season_code is None:
        season_label = UNKNOWN
        carryover = None
        season_code_out = UNKNOWN
    else:
        info = season_codes[season_code]
        season_label = info["label"]
        carryover = info["carryover"]
        season_code_out = season_code

    return ParsedProductCode(
        product_code=product_code,
        internal_category_code=type_code,
        internal_category_name=internal_category_name,
        season_code=season_code_out,
        season_label=season_label,
        carryover=carryover,
        size_rule_group=_rule_group_for(type_code, size_rule_groups),
    )
