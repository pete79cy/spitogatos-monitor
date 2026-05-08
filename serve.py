"""Tiny static-file HTTP server with HTTP Basic Auth.

Env vars:
  DASHBOARD_USER, DASHBOARD_PASSWORD — if both set, requires Basic Auth.
  WEB_DIR  — directory to serve (default: /app/data/web)
  PORT     — port to listen on (default: 8000)
"""
import base64
import http.server
import os
import socketserver

USER = os.getenv("DASHBOARD_USER", "")
PASS = os.getenv("DASHBOARD_PASSWORD", "")
ROOT = os.getenv("WEB_DIR", "/app/data/web")
PORT = int(os.getenv("PORT") or "3000")

os.makedirs(ROOT, exist_ok=True)


class AuthHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, fmt, *args):
        print(f"[serve] {self.address_string()} - {fmt % args}", flush=True)

    def _unauthorized(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Spitogatos Dashboard"')
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Authorization required".encode("utf-8"))

    def _check_auth(self) -> bool:
        if not USER:
            return True  # auth disabled
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return False
        try:
            u, _, p = base64.b64decode(h[6:]).decode("utf-8").partition(":")
        except Exception:
            return False
        return u == USER and p == PASS

    def do_GET(self):
        if not self._check_auth():
            return self._unauthorized()
        return super().do_GET()

    def do_HEAD(self):
        if not self._check_auth():
            return self._unauthorized()
        return super().do_HEAD()


if __name__ == "__main__":
    print(f"[serve] Root: {ROOT}  Port: {PORT}  Auth: {'on' if USER else 'off'}", flush=True)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), AuthHandler) as httpd:
        httpd.serve_forever()
