#!/usr/bin/env python3
"""
Run visible terminal smoke tests for PericopeAI.

This script:
1. Checks API health and authors endpoint.
2. Runs scripts/test-authors.py for a small critical author set.
3. Prints a visible PASS/FAIL summary table in terminal.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _log(msg: str = "") -> None:
    print(msg, flush=True)


def _request(url: str, timeout: int) -> Tuple[int | None, bytes, str | None]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), None
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        return e.code, body, f"HTTPError {e.code}"
    except Exception as e:
        return None, b"", repr(e)


def _wait_url(url: str, timeout: int, max_wait_s: int, label: str) -> None:
    _log(f"[gate] waiting for {label}: {url}")
    start = time.monotonic()
    last_err = "unknown"
    while time.monotonic() - start < max_wait_s:
        status, _body, err = _request(url, timeout=timeout)
        if status == 200:
            _log(f"[gate] {label}: PASS")
            return
        last_err = err or f"status={status}"
        _log(f"[gate] {label}: pending ({last_err})")
        time.sleep(2)
    raise RuntimeError(f"{label} did not become ready within {max_wait_s}s ({last_err})")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _print_summary(rows: List[Dict[str, Any]]) -> int:
    _log("\n=== Smoke Summary ===")
    header = (
        "author".ljust(18)
        + "pass ".ljust(7)
        + "status ".ljust(8)
        + "cit ".ljust(5)
        + "books ".ljust(7)
        + "meta ".ljust(6)
        + "pmax ".ljust(6)
        + "ms ".ljust(8)
        + "fail_reasons"
    )
    _log(header)
    _log("-" * len(header))

    failures = 0
    for row in rows:
        reasons = ",".join(row.get("fail_reasons") or [])
        if not row.get("pass"):
            failures += 1
        _log(
            str(row.get("author", "")).ljust(18)
            + str(bool(row.get("pass"))).ljust(7)
            + str(row.get("status")).ljust(8)
            + str(row.get("citations")).ljust(5)
            + str(row.get("books")).ljust(7)
            + str(row.get("metadata")).ljust(6)
            + str(row.get("position_max")).ljust(6)
            + str(row.get("elapsed_ms")).ljust(8)
            + reasons
        )

    _log(f"\nresult: {'PASS' if failures == 0 else 'FAIL'} (failures={failures}/{len(rows)})")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Visible smoke tests for PericopeAI.")
    parser.add_argument("--base-url", default="http://localhost:18000")
    parser.add_argument("--authors", default="augustine,marcus_aurelius")
    parser.add_argument(
        "--question",
        default="Summarize the main themes in 3-5 sentences and include citations.",
    )
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-wait", type=int, default=120)
    parser.add_argument("--out", default="tests/author-chat-smoke-visible.jsonl")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        _wait_url(f"{base_url}/api/healthz", timeout=args.timeout, max_wait_s=args.max_wait, label="api health")
        _wait_url(f"{base_url}/api/v1/authors", timeout=args.timeout, max_wait_s=args.max_wait, label="authors endpoint")
    except Exception as e:
        _log(f"[gate] FAIL: {e}")
        return 2

    cmd = [
        sys.executable,
        "scripts/test-authors.py",
        "--base-url",
        base_url,
        "--question",
        args.question,
        "--exclude-local-only",
        "--authors",
        args.authors,
        "--timeout",
        str(args.timeout),
        "--out",
        str(out_path),
    ]

    _log("\n=== Running Smoke Test ===")
    _log(" ".join(cmd))
    _log("")
    # Stream output directly so user can watch progress live.
    rc = subprocess.run(cmd).returncode

    if not out_path.exists():
        _log(f"ERROR: expected output file not found: {out_path}")
        return 3

    rows = _load_jsonl(out_path)
    failures = _print_summary(rows)

    if rc != 0 or failures > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
