"""Command line: python3 -m fibermap build | serve | resolve-zip."""
from __future__ import annotations

import argparse
import functools
import http.server
import json
import logging
import os
import sys

from . import build as build_mod
from . import config
from .zcta import resolve_zip


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="fibermap", description="Fiber buildout map for one ZIP code")
    ap.add_argument("-c", "--config", default="config.json", help="path to config.json (default: ./config.json)")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="fetch permits, news and tiles; write site/data.json")
    b.add_argument("--no-tiles", action="store_true", help="skip the map tile cache")
    b.add_argument("--no-news", action="store_true", help="skip the news feeds")

    s = sub.add_parser("serve", help="serve the site/ directory locally for a look")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--bind", default="127.0.0.1")

    z = sub.add_parser("resolve-zip", help="print the centre and suggested radius for a ZIP")
    z.add_argument("zip")

    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    if args.cmd == "build":
        build_mod.build(args.config, no_tiles=args.no_tiles, no_news=args.no_news)
        return 0
    if args.cmd == "serve":
        cfg = config.load(args.config)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=cfg["site_dir"])
        httpd = http.server.ThreadingHTTPServer((args.bind, args.port), handler)
        print(f"serving {cfg['site_dir']} at http://{args.bind}:{args.port}/", file=sys.stderr)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0
    if args.cmd == "resolve-zip":
        cache = os.path.join(os.path.dirname(os.path.abspath(args.config)), "data")
        os.makedirs(cache, exist_ok=True)
        print(json.dumps(resolve_zip(args.zip, cache), indent=1))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
