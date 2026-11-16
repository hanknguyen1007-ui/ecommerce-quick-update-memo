"""C4 (CHARTER v4.3): shared skip-guard for tests that need local-only fixtures (the real pinned v2/v3
samples and goldens, archive/, the brand-display translation fixture) -- none of which are committed. A
fresh clone must still run green; these tests SKIP with an explicit message instead of crashing."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def require_local(*paths: Path) -> None:
    """Raises unittest.SkipTest with an explicit message if any path is missing."""
    missing = [str(p.relative_to(ROOT)) for p in paths if not p.exists()]
    if missing:
        raise unittest.SkipTest(f"local fixture missing: {', '.join(missing)} (C4: not committed to the repo)")
