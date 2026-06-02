#!/usr/bin/env python3
"""Check robots.txt permission for a URL with a given user agent."""

from __future__ import annotations

import argparse
import sys
import urllib.parse
import urllib.robotparser


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--user-agent", default="research-paper-crawler")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        print("invalid URL", file=sys.stderr)
        return 2
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception as exc:
        print(f"robots check failed: {exc}", file=sys.stderr)
        return 1
    allowed = rp.can_fetch(args.user_agent, args.url)
    print(json_result(args.url, robots_url, args.user_agent, allowed))
    return 0 if allowed else 3


def json_result(url: str, robots_url: str, user_agent: str, allowed: bool) -> str:
    status = "allowed" if allowed else "disallowed"
    return f"{status}: user_agent={user_agent} url={url} robots={robots_url}"


if __name__ == "__main__":
    raise SystemExit(main())
