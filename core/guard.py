"""Startup guard: the only URL allowed anywhere in config/templates is http://localhost:11434."""
import re
import tomllib
from pathlib import Path

URL = re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://([^/\s:?#\"']+|\[[^\]]+\])(?::(\d+))?")
OK_HOSTS = {"localhost", "127.0.0.1", "[::1]"}


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


def assert_local(root: Path, config_path: Path | None = None) -> list[str]:
    """Raise RuntimeError on any non-localhost (or non-11434) URL. Returns the files scanned."""
    files = [config_path or root / "config.toml"] + sorted((root / "templates").glob("**/*.toml"))
    for f in files:
        data = tomllib.loads(Path(f).read_text(encoding="utf-8"))
        for s in _strings(data):
            for m in URL.finditer(s):
                host, port = m.group(1).lower(), m.group(2)
                if host not in OK_HOSTS or port != "11434":
                    raise RuntimeError(f"GUARD: non-local endpoint in {f}: {m.group(0)!r} "
                                       f"(only http://localhost:11434 allowed)")
    return [str(f) for f in files]
