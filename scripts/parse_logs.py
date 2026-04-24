#!/usr/bin/env python3
"""
Pretty-print structured JSON log payloads emitted by server.py.

Usage:
  python scripts/parse_logs.py /path/to/server.log
  python server.py 2>&1 | python scripts/parse_logs.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, TextIO


def _iter_lines(fp: TextIO) -> Iterable[str]:
    for line in fp:
        yield line.rstrip("\n")


def _extract_json_payload(line: str):
    """
    Our logging formatter emits: "<ts> <level> <logger> <message>"
    where <message> is a JSON string. This extracts the JSON part robustly.
    """
    start = line.find("{")
    end = line.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = line[start : end + 1]
    try:
        return json.loads(candidate)
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pretty-print JSON payload logs from voice_chat server.")
    parser.add_argument("file", nargs="?", help="Log file path. If omitted, reads stdin.")
    parser.add_argument("--raw", action="store_true", help="Print the extracted JSON (compact) instead of pretty format.")
    args = parser.parse_args(argv)

    if args.file:
        fp: TextIO
        fp = open(args.file, "r", encoding="utf-8", errors="replace")
        close_fp = True
    else:
        fp = sys.stdin
        close_fp = False

    try:
        for line in _iter_lines(fp):
            payload = _extract_json_payload(line)
            if payload is None:
                # Preserve non-JSON lines (stack traces, etc.)
                print(line)
                continue

            if args.raw:
                print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str))
            else:
                print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    finally:
        if close_fp:
            fp.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

