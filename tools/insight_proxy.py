"""Local CORS helper so Samyama Insight (https://graph.samyama.cloud) can reach a local engine.

    python tools/insight_proxy.py                       # 127.0.0.1:8091 -> http://127.0.0.1:8090
    python tools/insight_proxy.py --listen 8091 --upstream http://127.0.0.1:8090

Why: the engine answers CORS preflights with `Access-Control-Allow-Headers: *`, and
browsers do not let that wildcard cover the `Authorization` header Insight sends when
you are signed in (docs/ENGINE-NOTES.md, note 2). This proxy forwards every request to
the engine and answers CORS for the Insight origin only. It binds to the loopback
address and is for a development machine, not for exposing an engine.
"""
from __future__ import annotations

import argparse
import http.server
import urllib.error
import urllib.request

ALLOWED_ORIGINS = {"https://graph.samyama.cloud"}
HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade",
       "proxy-authorization", "proxy-authenticate", "host", "content-length"}


def make_handler(upstream: str):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _cors(self):
            origin = self.headers.get("Origin")
            if origin in ALLOWED_ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers",
                                 self.headers.get("Access-Control-Request-Headers") or "authorization, content-type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Vary", "Origin")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _forward(self):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP | {"origin"}}
            req = urllib.request.Request(upstream + self.path, data=body, headers=headers, method=self.command)
            try:
                resp = urllib.request.urlopen(req, timeout=600)
            except urllib.error.HTTPError as e:
                resp = e
            except Exception as e:
                msg = f"engine not reachable at {upstream}: {e}".encode()
                self.send_response(502)
                self._cors()
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
                return
            data = resp.read()
            self.send_response(resp.status)
            for k, v in resp.headers.items():
                if k.lower() not in HOP and not k.lower().startswith("access-control-") and k.lower() != "vary":
                    self.send_header(k, v)
            self._cors()
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = _forward

        def log_message(self, fmt, *args):
            print(f"{self.command} {self.path} -> {args[1] if len(args) > 1 else ''}", flush=True)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--listen", type=int, default=8091, help="loopback port to listen on")
    parser.add_argument("--upstream", default="http://127.0.0.1:8090", help="engine URL")
    args = parser.parse_args()
    print(f"Insight proxy on http://127.0.0.1:{args.listen} -> {args.upstream}", flush=True)
    http.server.ThreadingHTTPServer(("127.0.0.1", args.listen), make_handler(args.upstream)).serve_forever()


if __name__ == "__main__":
    main()
