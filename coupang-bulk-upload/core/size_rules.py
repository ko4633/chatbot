import json
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "size_rules.json"


def load_size_rules(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_sizes(size_rule_group: str | None, rules: dict | None = None) -> list[str]:
    rules = rules or load_size_rules()
    if size_rule_group and size_rule_group in rules["byRuleGroup"]:
        return list(rules["byRuleGroup"][size_rule_group])
    return list(rules["default"])
