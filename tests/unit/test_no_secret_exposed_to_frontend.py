"""CLAUDE.md hard rule: no NEXT_PUBLIC_* secret variables, ever. Phase 2
product brief §19 explicitly names ANTHROPIC_KEY/TELEGRAM_TOKEN as the
concrete things this must never happen to. A static grep across apps/web is
the simplest thing that can't be fooled by a refactor moving the read
somewhere else within the frontend.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB_APP_DIR = REPO_ROOT / "apps" / "web"

# Any env var starting with NEXT_PUBLIC_ is bundled into client-side JS by
# Next.js and becomes visible to every visitor — so it must never carry a
# secret-shaped name (key/token/secret/password).
SECRET_SHAPED_PUBLIC_VAR = re.compile(
    r"NEXT_PUBLIC_[A-Z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*", re.IGNORECASE
)

_SCAN_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".env", ".env.example", ".env.local")


def _frontend_source_files():
    if not WEB_APP_DIR.exists():
        return []
    return [
        p
        for p in WEB_APP_DIR.rglob("*")
        if p.is_file() and "node_modules" not in p.parts and ".next" not in p.parts
        and (p.suffix in _SCAN_SUFFIXES or p.name.startswith(".env"))
    ]


def test_no_secret_shaped_next_public_variable_in_frontend():
    offenders = []
    for path in _frontend_source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in SECRET_SHAPED_PUBLIC_VAR.finditer(text):
            offenders.append(f"{path.relative_to(REPO_ROOT)}: {match.group(0)}")
    assert offenders == [], "Secret-shaped NEXT_PUBLIC_* variable found:\n" + "\n".join(offenders)


def test_telegram_bot_token_is_never_referenced_in_frontend():
    for path in _frontend_source_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "TELEGRAM_BOT_TOKEN" not in text, f"{path} references TELEGRAM_BOT_TOKEN"
        assert "ANTHROPIC_API_KEY" not in text, f"{path} references ANTHROPIC_API_KEY"
