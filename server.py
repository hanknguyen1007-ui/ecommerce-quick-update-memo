"""Local report generator server. Binds 127.0.0.1 only; serves the v4 page and its static files."""
import json
import os
import sys
import tomllib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from core import guard  # noqa: E402

CFG_PATH = Path(os.environ.get("PERFLOCAL_CONFIG", ROOT / "config.toml"))


def load_cfg():
    return tomllib.loads(CFG_PATH.read_text(encoding="utf-8"))


class H(BaseHTTPRequestHandler):
    cfg = None

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _host_ok(self):
        h = (self.headers.get("Host") or "").split(":")[0].lower()
        return h in ("127.0.0.1", "localhost")

    def do_GET(self):
        if not self._host_ok():
            return self._send(403, {"error": "forbidden host"})
        # R7 (CHARTER v4.4) / CHARTER v5.1: ONE report UI at the root link -- "/" (and "/index.html")
        # serve web/index.html, which dispatches between the campaign (v4) and brand-monthly (v5)
        # engines itself (dispatch.py), never a per-engine URL the team has to remember. Everything
        # the page needs (its own .py/.toml source, synthetic samples) is served as a plain static
        # file from the project root, the same way `python -m http.server` would, with the same
        # host-allowlist guard on every request. web/v4/index.html and web/v5/index.html still exist
        # on disk (their own engine's local dev/test entry point) but are no longer the root link.
        if self.path in ("/", "/index.html"):
            self.path = "/web/index.html"
        return self._serve_static()

    _CTYPES = {".html": "text/html; charset=utf-8", ".py": "text/x-python; charset=utf-8",
               ".toml": "text/plain; charset=utf-8", ".tsv": "text/tab-separated-values; charset=utf-8",
               ".txt": "text/plain; charset=utf-8", ".md": "text/markdown; charset=utf-8",
               ".json": "application/json; charset=utf-8"}

    def _serve_static(self):
        rel = urlsplit(self.path).path.lstrip("/")
        p = (ROOT / rel).resolve()
        if ROOT not in p.parents and p != ROOT:  # no path traversal above the project root
            return self._send(403, {"error": "forbidden path"})
        if not p.is_file():
            return self._send(404, {"error": "not found"})
        ctype = self._CTYPES.get(p.suffix, "application/octet-stream")
        return self._send(200, p.read_bytes(), ctype)


def main():
    cfg = load_cfg()
    scanned = guard.assert_local(ROOT, CFG_PATH)  # raises RuntimeError on any non-localhost:11434 endpoint
    srv = cfg["server"]
    print(f"[guard] OK - {len(scanned)} toml files scanned, only localhost:11434 allowed")
    class Srv(ThreadingHTTPServer):
        allow_reuse_address = False  # on Windows reuse lets a 2nd stale server bind the same port and answer requests

    httpd = Srv((srv["host"], srv["port"]), H)
    print(f"[server] http://{srv['host']}:{srv['port']}  (127.0.0.1 only)")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
