"""Loads templates/brand-monthly/schema.toml once (decision 12: thresholds live in config, not code)."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_PATH = ROOT / "templates" / "brand-monthly" / "schema.toml"
_CFG = tomllib.loads(_PATH.read_text(encoding="utf-8"))

THRESHOLDS = _CFG["thresholds"]
PLATFORM_ORDER = _CFG["platforms"]["order"]
PLATFORMS = {k: v for k, v in _CFG["platforms"].items() if k != "order"}
LABELS = _CFG["labels"]
