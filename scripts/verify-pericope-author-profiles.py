#!/usr/bin/env python3
"""Verify the production-visible author profile contract for Pericope deploys."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Iterable


def _request(url: str, *, method: str = "GET", timeout: int = 30) -> tuple[int | None, bytes, str | None]:
    request = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), None
    except urllib.error.HTTPError as exc:
        body = exc.read() if hasattr(exc, "read") else b""
        return exc.code, body, f"HTTPError {exc.code}"
    except Exception as exc:  # pragma: no cover
        return None, b"", repr(exc)


def _request_json(url: str, *, timeout: int = 30) -> tuple[int | None, dict[str, Any] | list[Any] | None, str | None]:
    status, body, error = _request(url, timeout=timeout)
    if error or status != 200:
        return status, None, error or f"HTTP {status}"
    try:
        return status, json.loads(body.decode("utf-8")), None
    except Exception as exc:
        return status, None, f"JSON parse error: {exc}"


def _csv_set(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _check_asset(url: str, *, timeout: int) -> str | None:
    status, _body, error = _request(url, method="HEAD", timeout=timeout)
    if status == 405:
        status, _body, error = _request(url, method="GET", timeout=timeout)
    if error or status != 200:
        return error or f"HTTP {status}"
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = str(response.headers.get("content-type") or "").split(";", 1)[0].strip().lower()
    except Exception as exc:  # pragma: no cover
        return f"content-type check failed: {exc!r}"
    if not content_type.startswith("image/"):
        return f"unexpected content-type {content_type or '<missing>'}"
    return None


def _iter_author_slugs(authors: Iterable[dict[str, Any]]) -> list[str]:
    slugs: list[str] = []
    for author in authors:
        slug = str(author.get("slug") or "").strip()
        if slug:
            slugs.append(slug)
    return slugs


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Pericope author profiles.")
    parser.add_argument("--base-url", required=True, help="Base root URL, e.g. https://pericopeai.com")
    parser.add_argument("--assets-base-url", default="", help="Optional base URL for portrait asset checks")
    parser.add_argument("--required-slugs", default="", help="Comma-separated slugs that must be visible")
    parser.add_argument("--require-books-for", default="", help="Comma-separated slugs that must have at least one book")
    parser.add_argument("--only-slugs", default="", help="Optional comma-separated visible slugs to check in detail")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    assets_base = (args.assets_base_url or base_url).rstrip("/")
    required_slugs = _csv_set(args.required_slugs)
    require_books_for = _csv_set(args.require_books_for)
    only_slugs = _csv_set(args.only_slugs)

    status, authors_payload, error = _request_json(f"{base_url}/api/v1/authors", timeout=args.timeout)
    if status != 200 or error or not isinstance(authors_payload, list):
        sys.stderr.write(f"authors list failed: status={status} error={error}\n")
        return 1

    authors = [item for item in authors_payload if isinstance(item, dict)]
    visible_slugs = set(_iter_author_slugs(authors))
    missing_required = sorted(required_slugs - visible_slugs)
    if missing_required:
        print("Author profile verification failed:")
        for slug in missing_required:
            print(f"- {slug}: missing from /api/v1/authors")
        return 1

    failures: list[str] = []

    slugs_to_check = visible_slugs & only_slugs if only_slugs else visible_slugs

    for slug in sorted(slugs_to_check):
        status, profile_payload, error = _request_json(
            f"{base_url}/api/v1/authors/{slug}/profile",
            timeout=args.timeout,
        )
        if status != 200 or error or not isinstance(profile_payload, dict):
            failures.append(f"{slug}: profile request failed ({error or f'HTTP {status}'})")
            continue

        catalog_name = profile_payload.get("catalog_name")
        wikidata_id = profile_payload.get("wikidata_id")
        portrait = profile_payload.get("portrait")
        media_path = portrait.get("media_path") if isinstance(portrait, dict) else None
        books = profile_payload.get("books")

        if not catalog_name:
            failures.append(f"{slug}: missing catalog_name")
        if not wikidata_id:
            failures.append(f"{slug}: missing wikidata_id")
        if not media_path:
            failures.append(f"{slug}: missing portrait.media_path")
        if not isinstance(books, list):
            failures.append(f"{slug}: books is not a list")
        elif slug in require_books_for and not books:
            failures.append(f"{slug}: expected non-empty books")

        if media_path:
            asset_url = urllib.parse.urljoin(f"{assets_base}/", str(media_path).lstrip("/"))
            asset_error = _check_asset(asset_url, timeout=args.timeout)
            if asset_error:
                failures.append(f"{slug}: portrait asset failed ({asset_error})")

    if failures:
        print("Author profile verification failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print(
        "Author profile verification passed:",
        f"visible_authors={len(visible_slugs)}",
        f"required={len(required_slugs)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
