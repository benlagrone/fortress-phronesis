#!/usr/bin/env python3
"""
Cross-reference API smoke tests for PericopeAI.

Checks:
1) /api/healthz is reachable.
2) /api/v1/crossrefs/books returns mapped items.
3) /api/v1/crossrefs/authors/{author_slug} returns books for one author.
4) /api/v1/crossrefs/books/{book_id} returns related book payload.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def _request_json(url: str, timeout: int) -> tuple[int | None, Any, str | None]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            try:
                payload = json.loads(body.decode("utf-8")) if body else None
            except Exception:
                payload = body.decode("utf-8", errors="replace")
            return resp.status, payload, None
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        text = body.decode("utf-8", errors="replace")
        try:
            payload = json.loads(text) if text else None
        except Exception:
            payload = text
        return e.code, payload, f"HTTPError {e.code}"
    except Exception as e:
        return None, None, repr(e)


def _print_check(name: str, passed: bool, detail: str = "") -> None:
    status = "PASS" if passed else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test cross-reference API endpoints.")
    parser.add_argument("--base-url", default="http://localhost:18000")
    parser.add_argument("--author", default="", help="Optional author slug to test.")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--out", default="tests/crossref-smoke-visible.json")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    safe_limit = max(1, min(int(args.limit), 1000))
    selected_author = str(args.author or "").strip().lower()

    checks: list[dict[str, Any]] = []
    failures = 0

    def record(name: str, passed: bool, detail: str = "", payload: Any | None = None) -> None:
        nonlocal failures
        if not passed:
            failures += 1
        checks.append({"name": name, "pass": passed, "detail": detail, "payload": payload})
        _print_check(name, passed, detail)

    status, payload, err = _request_json(f"{base_url}/api/healthz", timeout=args.timeout)
    record(
        "healthz",
        status == 200,
        err or f"status={status}",
        payload if status == 200 else None,
    )

    query = {"limit": safe_limit}
    if selected_author:
        query["author_slug"] = selected_author
    books_url = f"{base_url}/api/v1/crossrefs/books?{urllib.parse.urlencode(query)}"
    status, payload, err = _request_json(books_url, timeout=args.timeout)
    items = payload.get("items", []) if isinstance(payload, dict) else []
    record(
        "crossrefs/books",
        status == 200 and isinstance(items, list) and len(items) > 0,
        err or f"status={status}, items={len(items) if isinstance(items, list) else 0}",
        {"count": len(items) if isinstance(items, list) else 0},
    )

    sample_item = items[0] if isinstance(items, list) and items else {}
    if not selected_author:
        selected_author = str(sample_item.get("author_slug") or "").strip().lower()
    if selected_author:
        status, payload, err = _request_json(
            f"{base_url}/api/v1/crossrefs/authors/{urllib.parse.quote(selected_author)}",
            timeout=args.timeout,
        )
        author_books = payload.get("books", []) if isinstance(payload, dict) else []
        record(
            "crossrefs/authors/{author_slug}",
            status == 200 and isinstance(author_books, list) and len(author_books) > 0,
            err or f"status={status}, books={len(author_books) if isinstance(author_books, list) else 0}",
            {
                "author": selected_author,
                "books": len(author_books) if isinstance(author_books, list) else 0,
            },
        )
    else:
        record("crossrefs/authors/{author_slug}", False, "no author slug available from catalog")

    sample_book_id = str(sample_item.get("book_id") or "").strip().upper()
    if sample_book_id:
        status, payload, err = _request_json(
            f"{base_url}/api/v1/crossrefs/books/{urllib.parse.quote(sample_book_id)}",
            timeout=args.timeout,
        )
        related = payload.get("related_books", []) if isinstance(payload, dict) else []
        record(
            "crossrefs/books/{book_id}",
            status == 200 and isinstance(related, list),
            err or f"status={status}, related_books={len(related) if isinstance(related, list) else 0}",
            {
                "book_id": sample_book_id,
                "related_books": len(related) if isinstance(related, list) else 0,
            },
        )
    else:
        record("crossrefs/books/{book_id}", False, "no book_id available from catalog")

    result = {
        "base_url": base_url,
        "author": selected_author or None,
        "book_id": sample_book_id or None,
        "checks": checks,
        "pass": failures == 0,
        "failures": failures,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nResult: {'PASS' if failures == 0 else 'FAIL'} ({failures} failures)")
    print(f"Wrote report: {out_path}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
