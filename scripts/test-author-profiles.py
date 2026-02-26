#!/usr/bin/env python3
"""Contract smoke test for DB-backed author profile endpoint (v1.1.2)."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def _request_json(url: str, timeout: int = 30) -> tuple[int | None, bytes, dict[str, str], str | None]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), dict(resp.headers.items()), None
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        headers = dict(getattr(e, "headers", {}).items()) if getattr(e, "headers", None) else {}
        return e.code, body, headers, f"HTTPError {e.code}"
    except Exception as e:
        return None, b"", {}, repr(e)


def _load_json(data: bytes) -> Any:
    return json.loads(data.decode("utf-8"))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _is_non_decreasing(values: list[int]) -> bool:
    return all(values[idx] <= values[idx + 1] for idx in range(len(values) - 1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Test /api/v1/authors/{slug}/profile contract.")
    parser.add_argument("--base-url", default="http://localhost:18000")
    parser.add_argument("--authors", default="", help="Comma-separated author slugs to test (default: all)")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--exclude-local-only", action="store_true", help="Exclude local_only authors")
    parser.add_argument("--out", default="tests/author-profile-contract.jsonl")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    status, body, _headers, err = _request_json(f"{base}/api/v1/authors", timeout=args.timeout)
    if status != 200:
        sys.stderr.write(f"Failed to fetch authors: status={status} err={err} body={body[:200]!r}\n")
        return 1

    authors = _load_json(body)
    if not isinstance(authors, list):
        sys.stderr.write("Authors response is not a list\n")
        return 1

    if args.exclude_local_only:
        authors = [a for a in authors if not a.get("local_only")]

    if args.authors:
        allow = {s.strip().lower() for s in args.authors.split(",") if s.strip()}
        authors = [a for a in authors if str(a.get("slug", "")).lower() in allow]

    total = len(authors)
    if total == 0:
        sys.stderr.write("No authors selected.\n")
        return 1

    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    for idx, author in enumerate(authors, start=1):
        slug = str(author.get("slug") or "").strip().lower()
        if not slug:
            continue
        sys.stderr.write(f"[{idx}/{total}] {slug}\n")
        start = time.monotonic()
        status, body, headers, err = _request_json(
            f"{base}/api/v1/authors/{slug}/profile",
            timeout=args.timeout,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        headers_lc = {str(k).lower(): v for k, v in headers.items()}
        cache_control_header = str(headers_lc.get("cache-control") or "")

        row: dict[str, Any] = {
            "author": slug,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "books": 0,
            "cache_control": cache_control_header,
            "pass": False,
            "fail_reasons": [],
        }

        if status != 200 or err:
            row["fail_reasons"].append(err or f"HTTP {status}")
            rows.append(row)
            failures.append(f"{slug}: {row['fail_reasons'][0]}")
            continue

        try:
            payload = _load_json(body)
        except Exception as e:
            row["fail_reasons"].append(f"JSON parse error: {e}")
            rows.append(row)
            failures.append(f"{slug}: {row['fail_reasons'][0]}")
            continue

        books = payload.get("books") if isinstance(payload, dict) else None
        if not isinstance(books, list):
            row["fail_reasons"].append("books not list")
            books = []

        row["books"] = len(books)
        if row["books"] < 1:
            row["fail_reasons"].append("books<1")

        sort_orders: list[int] = []
        for item in books:
            if not isinstance(item, dict):
                continue
            try:
                sort_orders.append(int(item.get("sort_order", 0)))
            except (TypeError, ValueError):
                sort_orders.append(0)
        if sort_orders and not _is_non_decreasing(sort_orders):
            row["fail_reasons"].append("sort_order not stable")

        cache_control = str(row.get("cache_control") or "").lower()
        if "max-age" not in cache_control:
            row["fail_reasons"].append("cache-control missing max-age")

        row["pass"] = not row["fail_reasons"]
        if not row["pass"]:
            failures.append(f"{slug}: {', '.join(row['fail_reasons'])}")
        rows.append(row)

    _write_jsonl(out_path, rows)

    ok = sum(1 for row in rows if row.get("pass"))
    errors = len(rows) - ok
    print(
        f"Done. total={len(rows)} ok={ok} errors={errors} "
        f"avg_ms={int(sum(r.get('elapsed_ms', 0) for r in rows)/max(1,len(rows)))}"
    )
    print(f"Output: {out_path}")
    if failures:
        print("Failures:")
        for item in failures:
            print(f"- {item}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
