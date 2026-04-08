#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from app.services.screener_client import ScreenerClient


def main() -> None:
    parser = argparse.ArgumentParser(description='Prewarm Screener sector/screen pages into cache')
    parser.add_argument('--sector', action='append', dest='sectors', default=[], help='Sector slug (repeatable)')
    parser.add_argument('--screen', action='append', dest='screens', default=[], help='screen_id:slug (repeatable)')
    parser.add_argument('--pages-per-target', type=int, default=1)
    parser.add_argument('--proxy-url', default=None)
    args = parser.parse_args()

    screen_refs = []
    for raw in args.screens:
        if ':' not in raw:
            continue
        sid, slug = raw.split(':', 1)
        try:
            screen_refs.append({'screen_id': int(sid), 'slug': slug})
        except ValueError:
            continue

    client = ScreenerClient()
    out = client.prewarm_pages(
        sector_slugs=args.sectors,
        screen_refs=screen_refs,
        pages_per_target=max(1, args.pages_per_target),
        proxy_url=args.proxy_url,
    )
    print(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
