from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


@lru_cache
def load_margin_assumptions() -> dict:
    with (CONFIG_DIR / "margin_assumptions.yaml").open() as f:
        return yaml.safe_load(f)


@lru_cache
def load_opportunity_weights() -> dict:
    with (CONFIG_DIR / "opportunity_weights.yaml").open() as f:
        config = yaml.safe_load(f)
    total = sum(config["weights"].values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"opportunity_weights.yaml weights must sum to 1.0, got {total}")
    return config
