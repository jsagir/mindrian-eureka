"""Loopback-only local web bridge for the OMM room-review page."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .algorithm import analyze_sequence
from ..contracts import ResultContractError, validate_request, validate_result


class OMMHandler(SimpleHTTPRequestHandler):
    server_version = "MindrianOMM/0.1"

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if urlparse(self.path).path != "/api/omm/analyze":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            self.send_error(413, "JSON body must be between 1 byte and 1 MB")
            return
        try:
            body = json.loads(self.rfile.read(length))
            validate_request("decision.compare_sequence_patterns", body)
            result = analyze_sequence(body)
            validate_result("decision.compare_sequence_patterns", result)
            payload = json.dumps(result, ensure_ascii=False).encode("utf-8")
        except ResultContractError as exc:
            payload = json.dumps({"error": "Output contract violation", "detail": str(exc)}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            payload = json.dumps({"error": str(exc)}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local Oliver–JHTV OMM review page and HMM API.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback only by default")
    parser.add_argument("--port", type=int, default=4173)
    parser.add_argument(
        "--directory",
        type=Path,
        default=Path(__file__).resolve().parents[3] / "evaluations" / "room-runs",
        help="Static room-review directory",
    )
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("This room server is local-only; bind to 127.0.0.1, localhost, or ::1")
    handler = lambda *a, **kw: OMMHandler(*a, directory=str(args.directory.resolve()), **kw)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"OMM room review: http://{args.host}:{args.port}/jhtv-theo-larry-review.html")
    print("Local-only API: POST /api/omm/analyze")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
