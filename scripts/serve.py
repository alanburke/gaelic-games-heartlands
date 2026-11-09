"""Local server for the site, with one extra: the club area editor can save.

Serves the repo folder like `python3 -m http.server`, and also accepts
PUT /data/clubs/<county>_areas.json from club-areas.html, writing the file in place.
Listens on 127.0.0.1 only.

Usage (from the repo root):  python3 scripts/serve.py [port]
"""
import http.server
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAVABLE = re.compile(r"^/data/clubs/[a-z_]+_areas\.json$")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_PUT(self):
        if not SAVABLE.match(self.path):
            return self.send_error(403, "Only club area files can be saved")
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            data = json.loads(body)
            assert isinstance(data.get("assignments"), dict)
        except Exception:
            return self.send_error(400, "Expected JSON with an assignments object")
        (ROOT / self.path.lstrip("/")).write_text(json.dumps(data, indent=1, ensure_ascii=False))
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    print(f"Serving {ROOT} at http://127.0.0.1:{port}/")
    http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
