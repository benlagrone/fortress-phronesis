#!/usr/bin/env python3
"""Dry-run author acquisition tracker tools.

Phase 0 intentionally reads and reports only. It does not mutate ledgers,
download sources, build indexes, or touch production state.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import uuid
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PUBLIC_VERIFIED_STATUS = (
    "texts downloaded; prod corpus synced; index built; runtime wired; "
    "public verification passed"
)
GUTENDEX_BASE_URL = "https://gutendex.com"

STATUS_CLASS_BY_EXACT_STATUS = {
    "pending": "pending",
    "next-up queued; pending text acquisition": "queued_pending_text_acquisition",
    "texts downloaded; pending prod corpus sync": "pending_prod_corpus_sync",
    "texts downloaded; prod corpus synced; pending index build": "pending_index_build",
    "texts downloaded; index built; pending prod corpus sync": "pending_prod_corpus_sync",
    "texts downloaded; prod corpus synced; index built; pending runtime wiring": (
        "pending_runtime_wiring"
    ),
    "texts downloaded; prod corpus synced; index built; runtime wired; "
    "pending public verification": "pending_public_verification",
    PUBLIC_VERIFIED_STATUS: "public_verification_passed",
    # Historical/local statuses currently present in the tracker.
    "texts downloaded; index built; runtime wired": "legacy_runtime_wired",
    "texts present; index volume wired": "texts_present_index_volume_wired",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_fortress_ledger_path() -> Path:
    return _repo_root() / "docs" / "author_acquisition.json"


def default_service_ledger_path() -> Path:
    workspace_root = _repo_root().parent
    nested = workspace_root / "pericopeai.com" / "AugustineService" / "metadata" / "author_acquisition.json"
    if nested.exists():
        return nested
    return workspace_root / "AugustineService" / "metadata" / "author_acquisition.json"


def default_corpus_root_path() -> Path:
    workspace_root = _repo_root().parent
    nested = workspace_root / "pericopeai.com" / "AugustineCorpus"
    if nested.exists():
        return nested
    return workspace_root / "AugustineCorpus"


def _issue(severity: str, code: str, message: str, **details: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if details:
        row["details"] = details
    return row


def _load_json(path: Path) -> tuple[Any | None, list[dict[str, Any]]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [_issue("error", "ledger_missing", f"Ledger not found: {path}")]
    except json.JSONDecodeError as exc:
        return None, [
            _issue(
                "error",
                "ledger_invalid_json",
                f"Ledger is not valid JSON: {path}",
                line=exc.lineno,
                column=exc.colno,
            )
        ]


def _read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def classify_status(status: str) -> str:
    if status in STATUS_CLASS_BY_EXACT_STATUS:
        return STATUS_CLASS_BY_EXACT_STATUS[status]
    if status.startswith("next-up queued"):
        return "queued_pending_text_acquisition"
    if "public verification passed" in status:
        return "public_verification_passed"
    if "pending public verification" in status:
        return "pending_public_verification"
    if "pending prod corpus sync" in status:
        return "pending_prod_corpus_sync"
    if "pending index build" in status:
        return "pending_index_build"
    if "pending runtime wiring" in status:
        return "pending_runtime_wiring"
    return "unknown_status"


def _entry_name(entry: dict[str, Any]) -> str:
    return str(entry.get("name") or "").strip()


def _entry_status(entry: dict[str, Any]) -> str:
    return str(entry.get("status") or "").strip()


def _normalize_author_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", ascii_text).strip().casefold()


def _slugify_author_key(value: Any) -> str:
    text = _normalize_author_key(value)
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def _extract_key_works(entry: dict[str, Any]) -> list[str]:
    note_prefixes = ("Key Works:", "Key Work:", "Key Texts:", "Key Text:")
    notes = entry.get("notes")
    if isinstance(notes, list):
        for note in notes:
            text = str(note or "").strip()
            if not text:
                continue
            for prefix in note_prefixes:
                if text.startswith(prefix):
                    return [part.strip() for part in re.split(r"[;,]", text[len(prefix):]) if part.strip()]

    works = entry.get("works")
    if isinstance(works, list):
        return [
            str(work).strip()
            for work in works
            if str(work or "").strip() and not str(work).strip().startswith(("http://", "https://"))
        ]
    return []


def _extract_inventory_works(entry: dict[str, Any]) -> list[str]:
    works = entry.get("works")
    if not isinstance(works, list):
        return []
    return [str(work).strip() for work in works if str(work or "").strip()]


def _normalize_work_title(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = text.encode("ascii", "ignore").decode("ascii").casefold()
    ascii_text = re.sub(r"\([^)]*\)", " ", ascii_text)
    ascii_text = re.sub(r"\b(the|a|an)\b", " ", ascii_text)
    ascii_text = ascii_text.replace("&", " and ")
    ascii_text = re.sub(r"[^a-z0-9]+", " ", ascii_text)
    return re.sub(r"\s+", " ", ascii_text).strip()


def _corpus_titles_from_meta(meta_data: Any, text_path: Path) -> list[str]:
    titles: list[str] = []
    if isinstance(meta_data, list):
        for item in meta_data:
            if not isinstance(item, dict):
                continue
            filename = str(item.get("filename") or "").strip()
            if not filename:
                continue
            title = str(
                item.get("title")
                or item.get("work")
                or Path(filename).stem.replace("_", " ")
            ).strip()
            if title:
                titles.append(title)
    if not titles and text_path.exists():
        titles = [path.stem.replace("_", " ") for path in sorted(text_path.glob("*.txt"))]
    return titles


def _load_corpus_work_lookup(corpus_root: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    author_index_path = corpus_root / "author_index.json"
    data, load_issues = _load_json(author_index_path)
    if data is None:
        return {}, load_issues
    if not isinstance(data, list):
        return {}, [
            _issue(
                "warning",
                "corpus_author_index_invalid",
                f"Corpus author index must contain a JSON array: {author_index_path}",
                actual_type=type(data).__name__,
            )
        ]

    lookup: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    for row in data:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        texts_dir = str(row.get("texts_dir") or "").strip()
        if not slug or not texts_dir:
            continue
        text_root = texts_dir if Path(texts_dir).is_absolute() else str(corpus_root / texts_dir)
        text_path = Path(text_root)
        meta_path = text_path / "book_metadata.json"
        count = 0
        titles: list[str] = []
        if meta_path.exists():
            meta_data, meta_issues = _load_json(meta_path)
            issues.extend(meta_issues)
            if isinstance(meta_data, list):
                titles = _corpus_titles_from_meta(meta_data, text_path)
                count = len(titles)
        if count == 0 and text_path.exists():
            titles = _corpus_titles_from_meta(None, text_path)
            count = len(titles)

        payload = {
            "slug": slug,
            "name": row.get("name"),
            "catalog_name": row.get("catalog_name"),
            "corpus_work_count": count,
            "corpus_titles": titles,
            "normalized_corpus_titles": {
                _normalize_work_title(title) for title in titles if _normalize_work_title(title)
            },
        }
        keys = {
            _normalize_author_key(row.get("name")),
            _normalize_author_key(row.get("catalog_name")),
            _normalize_author_key(slug),
            _slugify_author_key(row.get("name")),
            _slugify_author_key(row.get("catalog_name")),
        }
        for key in keys:
            if key:
                lookup[key] = payload

    return lookup, issues


def _is_progressed_status(status: str) -> bool:
    status_class = classify_status(status)
    return status_class not in {
        "pending",
        "queued_pending_text_acquisition",
        "unknown_status",
    }


def _gutendex_author_tokens(name: str) -> set[str]:
    normalized = _normalize_author_key(name)
    return {
        token
        for token in re.split(r"[^a-z0-9]+", normalized)
        if token and token not in {"of", "the", "saint", "st"}
    }


def _gutendex_author_match(target_name: str, candidate_name: str) -> bool:
    target = _normalize_author_key(target_name)
    candidate = _normalize_author_key(candidate_name)
    if not target or not candidate:
        return False
    if target == candidate:
        return True
    target_tokens = _gutendex_author_tokens(target_name)
    candidate_tokens = _gutendex_author_tokens(candidate_name)
    if not target_tokens or not candidate_tokens:
        return False
    if target_tokens == candidate_tokens:
        return True
    return len(target_tokens.intersection(candidate_tokens)) >= max(1, min(len(target_tokens), 2))


def _gutendex_book_matches_author(target_name: str, book: dict[str, Any]) -> bool:
    authors = book.get("authors")
    if not isinstance(authors, list):
        return False
    return any(
        isinstance(author, dict)
        and _gutendex_author_match(target_name, str(author.get("name") or ""))
        for author in authors
    )


def _best_gutendex_text_url(book: dict[str, Any]) -> str:
    formats = book.get("formats")
    if not isinstance(formats, dict):
        return ""
    preferred = (
        "text/plain; charset=utf-8",
        "text/plain; charset=us-ascii",
        "text/plain",
        "text/html; charset=utf-8",
        "text/html",
    )
    for key in preferred:
        value = formats.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for key, value in formats.items():
        if isinstance(key, str) and key.startswith("text/") and isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _score_openlibrary_author_match(target_name: str, candidate: dict[str, Any]) -> tuple[int, int]:
    candidate_name = str(candidate.get("name") or "").strip()
    if not candidate_name:
        return (-1, 0)
    target = _normalize_author_key(target_name)
    normalized_candidate = _normalize_author_key(candidate_name)
    target_tokens = _gutendex_author_tokens(target_name)
    candidate_tokens = _gutendex_author_tokens(candidate_name)
    score = 0
    if target and target == normalized_candidate:
        score += 100
    if target_tokens and candidate_tokens:
        overlap = len(target_tokens.intersection(candidate_tokens))
        if overlap:
            score += overlap * 20
        if target_tokens == candidate_tokens:
            score += 30
    top_work = _normalize_work_title(candidate.get("top_work") or "")
    if top_work and any(token in top_work for token in target_tokens):
        score += 5
    try:
        work_count = int(candidate.get("work_count") or 0)
    except (TypeError, ValueError):
        work_count = 0
    return (score, work_count)


def _resolve_openlibrary_author(
    author_name: str,
    *,
    timeout_seconds: float = 20.0,
) -> dict[str, Any] | None:
    query = urllib.parse.urlencode({"q": author_name, "limit": 10})
    url = f"https://openlibrary.org/search/authors.json?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "fortress-phronesis-author-acq/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        return None
    docs = payload.get("docs")
    if not isinstance(docs, list):
        return None
    candidates = [doc for doc in docs if isinstance(doc, dict)]
    if not candidates:
        return None
    best = max(candidates, key=lambda doc: _score_openlibrary_author_match(author_name, doc))
    if _score_openlibrary_author_match(author_name, best)[0] <= 0:
        return None
    return best


def _fetch_gutendex_books_for_author(
    author_name: str,
    *,
    max_pages: int = 4,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    query = urllib.parse.urlencode(
        {
            "search": author_name,
            "copyright": "false",
            "languages": "en",
        }
    )
    url = f"{GUTENDEX_BASE_URL}/books?{query}"
    pages_visited: list[str] = []
    books_by_id: dict[int, dict[str, Any]] = {}

    for _ in range(max_pages):
        pages_visited.append(url)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "fortress-phronesis-author-acq/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            break
        results = payload.get("results")
        if isinstance(results, list):
            for item in results:
                if not isinstance(item, dict):
                    continue
                if not _gutendex_book_matches_author(author_name, item):
                    continue
                try:
                    book_id = int(item.get("id"))
                except (TypeError, ValueError):
                    continue
                books_by_id[book_id] = item
        next_url = payload.get("next")
        if not isinstance(next_url, str) or not next_url.strip():
            break
        url = next_url.strip()

    return {
        "source": "gutendex",
        "author_name": author_name,
        "pages_visited": pages_visited,
        "books": list(books_by_id.values()),
    }


def _fetch_openlibrary_books_for_author(
    author_name: str,
    *,
    max_pages: int = 2,
    timeout_seconds: float = 20.0,
) -> dict[str, Any]:
    pages_visited: list[str] = []
    books_by_key: dict[str, dict[str, Any]] = {}
    resolved_author = _resolve_openlibrary_author(author_name, timeout_seconds=timeout_seconds)
    if resolved_author is None:
        raise RuntimeError(f"Open Library author resolution failed for {author_name}")
    resolved_author_key = str(resolved_author.get("key") or "").strip()
    if not resolved_author_key:
        raise RuntimeError(f"Open Library author key missing for {author_name}")

    for page in range(1, max_pages + 1):
        query = urllib.parse.urlencode(
            {
                "author_key": resolved_author_key,
                "language": "eng",
                "fields": (
                    "key,title,author_name,author_key,has_fulltext,ebook_access,ia,"
                    "public_scan_b,first_publish_year"
                ),
                "page": page,
                "limit": 100,
            }
        )
        url = f"https://openlibrary.org/search.json?{query}"
        pages_visited.append(url)
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "fortress-phronesis-author-acq/1.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            break
        docs = payload.get("docs")
        if not isinstance(docs, list):
            break
        for item in docs:
            if not isinstance(item, dict):
                continue
            author_keys = item.get("author_key")
            if not isinstance(author_keys, list):
                continue
            if resolved_author_key not in {str(value or "").strip() for value in author_keys}:
                continue
            key = str(item.get("key") or "").strip()
            if not key:
                continue
            books_by_key[key] = item
        if len(docs) < 100:
            break

    return {
        "source": "openlibrary",
        "author_name": author_name,
        "resolved_author_name": str(resolved_author.get("name") or "").strip(),
        "resolved_author_key": resolved_author_key,
        "pages_visited": pages_visited,
        "books": list(books_by_key.values()),
    }


def _fetch_coverage_source_books_for_author(
    author_name: str,
    *,
    max_pages: int = 4,
) -> dict[str, Any]:
    errors: list[str] = []
    for fetcher in (_fetch_openlibrary_books_for_author, _fetch_gutendex_books_for_author):
        try:
            payload = fetcher(author_name, max_pages=max_pages)
            payload["source_errors"] = list(errors)
            return payload
        except Exception as exc:
            errors.append(f"{fetcher.__name__}: {exc}")
    raise RuntimeError("; ".join(errors) if errors else "no coverage sources available")


def _coverage_book_identifier(source: str, book: dict[str, Any]) -> str:
    if source == "openlibrary":
        return str(book.get("key") or "").strip()
    return str(book.get("id") or "").strip()


def _coverage_book_source_url(source: str, book: dict[str, Any]) -> str:
    if source == "openlibrary":
        ia = book.get("ia")
        if isinstance(ia, list) and ia and str(ia[0]).strip():
            return f"https://archive.org/details/{str(ia[0]).strip()}"
        key = str(book.get("key") or "").strip()
        return f"https://openlibrary.org{key}" if key else "https://openlibrary.org/"
    return _best_gutendex_text_url(book) or f"{GUTENDEX_BASE_URL}/books/{book.get('id')}"


def _coverage_book_source_type(source: str, book: dict[str, Any]) -> str:
    if source == "openlibrary":
        if book.get("has_fulltext") or str(book.get("ebook_access") or "").strip().lower() == "public":
            return "full_text"
        return "catalog_record"
    return "full_text" if _best_gutendex_text_url(book) else "catalog_record"


def _coverage_book_classification(source: str, book: dict[str, Any]) -> str:
    if source == "openlibrary":
        if book.get("has_fulltext") or str(book.get("ebook_access") or "").strip().lower() == "public":
            return "missing_usable_public_domain_text"
        return "bibliographic_record_only"
    return "missing_usable_public_domain_text"


def _build_local_title_aliases(
    entry: dict[str, Any],
    corpus_row: dict[str, Any] | None,
) -> tuple[list[str], set[str]]:
    display_titles: list[str] = []
    seen_display: set[str] = set()
    normalized_titles: set[str] = set()
    for title in [
        *(_extract_inventory_works(entry)),
        *(_extract_key_works(entry)),
        *((corpus_row or {}).get("corpus_titles") or []),
    ]:
        clean = str(title or "").strip()
        if not clean:
            continue
        normalized = _normalize_work_title(clean)
        if normalized:
            normalized_titles.add(normalized)
        display_key = clean.casefold()
        if display_key not in seen_display:
            seen_display.add(display_key)
            display_titles.append(clean)
    return display_titles, normalized_titles


def _extract_entry_death_year(entry: dict[str, Any]) -> int | None:
    notes = entry.get("notes")
    if not isinstance(notes, list):
        return None
    time_note = next(
        (str(note).strip() for note in notes if str(note or "").strip().startswith("Time:")),
        "",
    )
    if not time_note:
        return None
    years = [int(value) for value in re.findall(r"(?<!\d)(\d{1,4})(?!\d)", time_note)]
    if not years:
        return None
    if "BC" in time_note and "AD" not in time_note:
        years = [-year for year in years]
    if "BC" in time_note and "AD" in time_note and len(years) >= 2:
        years = [-abs(years[0]), abs(years[1]), *years[2:]]
    return years[1] if len(years) >= 2 else years[0]


def _coverage_book_is_plausible_for_entry(entry: dict[str, Any], source: str, book: dict[str, Any]) -> bool:
    if source != "openlibrary":
        return True
    death_year = _extract_entry_death_year(entry)
    if death_year is None or death_year < 1500:
        return True
    try:
        first_publish_year = int(book.get("first_publish_year") or 0)
    except (TypeError, ValueError):
        return True
    if not first_publish_year:
        return True
    return first_publish_year <= death_year + 30


def _choose_better_coverage_book(source: str, existing: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
    if existing is None:
        return candidate
    existing_score = 1 if _coverage_book_source_type(source, existing) == "full_text" else 0
    candidate_score = 1 if _coverage_book_source_type(source, candidate) == "full_text" else 0
    if candidate_score != existing_score:
        return candidate if candidate_score > existing_score else existing
    existing_year = int(existing.get("first_publish_year") or 0) if str(existing.get("first_publish_year") or "").isdigit() else 0
    candidate_year = int(candidate.get("first_publish_year") or 0) if str(candidate.get("first_publish_year") or "").isdigit() else 0
    if existing_year and candidate_year:
        return candidate if candidate_year < existing_year else existing
    return existing


def _coverage_audit_candidates(
    entries: list[dict[str, Any]],
    author_filter: str = "",
    status_filter: str = "",
) -> list[dict[str, Any]]:
    normalized_filter = _normalize_author_key(author_filter)
    normalized_status = str(status_filter or "").strip().casefold()
    candidates: list[dict[str, Any]] = []
    for entry in entries:
        name = _entry_name(entry)
        status = _entry_status(entry)
        if not name or not _is_progressed_status(status):
            continue
        normalized_name = _normalize_author_key(name)
        if normalized_filter and normalized_filter not in {normalized_name, _slugify_author_key(name)}:
            continue
        if normalized_status and status.casefold() != normalized_status:
            continue
        candidates.append(entry)
    return candidates


def build_coverage_audit(
    fortress_ledger: Path,
    service_ledger: Path,
    *,
    corpus_root: Path | None = None,
    author_filter: str = "",
    status_filter: str = "",
    max_pages: int = 4,
    include_bibliographic_only: bool = False,
) -> dict[str, Any]:
    tracker_report = build_tracker_audit(
        fortress_ledger,
        service_ledger,
        corpus_root=corpus_root or default_corpus_root_path(),
    )
    issues = list(tracker_report["issues"])
    source_entries = _load_json(fortress_ledger)[0]
    entries = source_entries if isinstance(source_entries, list) else []
    corpus_lookup, corpus_issues = _load_corpus_work_lookup(corpus_root or default_corpus_root_path())
    issues.extend(corpus_issues)

    author_summaries: list[dict[str, Any]] = []
    author_reports: list[dict[str, Any]] = []
    source_card_candidates: list[dict[str, Any]] = []
    total_gap_count = 0

    coverage_candidates = _coverage_audit_candidates(
        entries,
        author_filter=author_filter,
        status_filter=status_filter,
    )

    for entry in coverage_candidates:
        name = _entry_name(entry)
        status = _entry_status(entry)
        corpus_row = (
            corpus_lookup.get(_normalize_author_key(name))
            or corpus_lookup.get(_slugify_author_key(name))
        )
        author_slug = str((corpus_row or {}).get("slug") or _slugify_author_key(name))
        local_titles, normalized_local_titles = _build_local_title_aliases(entry, corpus_row)
        try:
            source_payload = _fetch_coverage_source_books_for_author(name, max_pages=max_pages)
        except Exception as exc:
            issues.append(
                _issue(
                    "warning",
                    "coverage_source_error",
                    f"Coverage audit source query failed for {name}.",
                    author=name,
                    source="external_catalog",
                    error=str(exc),
                )
            )
            continue

        external_books_by_title: dict[str, dict[str, Any]] = {}
        candidate_books_by_title: dict[str, dict[str, Any]] = {}
        source_name = str(source_payload.get("source") or "external_catalog")
        for book in source_payload["books"]:
            title = str(book.get("title") or "").strip()
            normalized_title = _normalize_work_title(title)
            if (
                not title
                or not normalized_title
                or not _coverage_book_is_plausible_for_entry(entry, source_name, book)
            ):
                continue
            external_books_by_title[normalized_title] = _choose_better_coverage_book(
                source_name,
                external_books_by_title.get(normalized_title),
                book,
            )
            if normalized_title in normalized_local_titles:
                continue
            candidate_books_by_title[normalized_title] = _choose_better_coverage_book(
                source_name,
                candidate_books_by_title.get(normalized_title),
                book,
            )

        gap_packets: list[dict[str, Any]] = []
        for normalized_title, book in candidate_books_by_title.items():
            title = str(book.get("title") or "").strip()
            book_identifier = _coverage_book_identifier(source_name, book)
            if not title or not book_identifier:
                continue
            source_id = f"{source_name}:{book_identifier}"
            source_url = _coverage_book_source_url(source_name, book)
            source_type = _coverage_book_source_type(source_name, book)
            classification = _coverage_book_classification(source_name, book)
            if classification != "missing_usable_public_domain_text" and not include_bibliographic_only:
                continue
            source_card_candidates.append(
                {
                    "source_id": source_id,
                    "author_name": name,
                    "work_title": title,
                    "source_url": source_url,
                    "source_type": source_type,
                    "edition_note": (
                        f"Open Library key {book_identifier}"
                        if source_name == "openlibrary"
                        else f"Project Gutenberg ID {book_identifier}"
                    ),
                    "rights_status": "needs_review",
                    "provenance_note": (
                        (
                            f"Open Library search for '{name}' returned {book_identifier} "
                            "with English-language metadata."
                        )
                        if source_name == "openlibrary"
                        else (
                            f"Gutendex search for '{name}' returned Project Gutenberg ID "
                            f"{book_identifier} with copyright=false and English language metadata."
                        )
                    ),
                    "review_status": "pending_review",
                }
            )
            gap_packets.append(
                {
                    "gap_id": str(
                        uuid.uuid5(uuid.NAMESPACE_URL, f"{source_name}:{author_slug}:{book_identifier}")
                    ),
                    "author_slug": author_slug,
                    "author_name": name,
                    "work_title": title,
                    "local_status": "not_found",
                    "source_candidates": [source_id],
                    "classification": classification,
                    "confidence": 0.9 if classification == "missing_usable_public_domain_text" else 0.7,
                    "review_status": "pending_review",
                }
            )

        author_summary = {
            "author_name": name,
            "author_slug": author_slug,
            "status": status,
            "local_titles_count": len(local_titles),
            "corpus_work_count": int((corpus_row or {}).get("corpus_work_count") or 0),
            "external_work_count": len(external_books_by_title),
            "external_candidate_count": len(candidate_books_by_title),
            "gap_count": len(gap_packets),
            "local_titles_sample": local_titles[:8],
            "source": source_payload["source"],
            "pages_visited": source_payload["pages_visited"],
        }
        author_summaries.append(author_summary)

        if gap_packets:
            total_gap_count += len(gap_packets)
            author_reports.append(
                {
                    **author_summary,
                    "publication_gap_packets": gap_packets,
                }
            )

    unique_source_cards = {
        card["source_id"]: card for card in source_card_candidates if card.get("source_id")
    }
    return {
        "packet_type": "coverage_audit_report",
        "dry_run": True,
        "source": "openlibrary_then_gutendex",
        "authors_scanned": len(coverage_candidates),
        "authors_with_gaps": len(author_reports),
        "publication_gap_count": total_gap_count,
        "author_summaries": author_summaries,
        "author_reports": author_reports,
        "source_card_candidates": list(unique_source_cards.values()),
        "issues": issues,
    }


def _validate_entries(label: str, data: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    if not isinstance(data, list):
        return [], [
            _issue(
                "error",
                "ledger_not_list",
                f"{label} ledger must contain a JSON array.",
                actual_type=type(data).__name__,
            )
        ]

    entries: list[dict[str, Any]] = []
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            issues.append(
                _issue(
                    "error",
                    "ledger_entry_not_object",
                    f"{label} entry {index} is not an object.",
                    index=index,
                    actual_type=type(item).__name__,
                )
            )
            continue
        entries.append(item)
        if not _entry_name(item):
            issues.append(
                _issue("warning", "entry_missing_name", f"{label} entry {index} has no name.")
            )
        if not _entry_status(item):
            issues.append(
                _issue("warning", "entry_missing_status", f"{label} entry {index} has no status.")
            )
    return entries, issues


def _duplicate_names(entries: list[dict[str, Any]]) -> dict[str, list[str]]:
    by_key: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        name = _entry_name(entry)
        if name:
            by_key[name.casefold()].append(name)
    return {key: names for key, names in by_key.items() if len(names) > 1}


def _status_counts(entries: list[dict[str, Any]]) -> Counter[str]:
    return Counter(_entry_status(entry) or "<missing>" for entry in entries)


def _status_class_counts(entries: list[dict[str, Any]]) -> Counter[str]:
    return Counter(classify_status(_entry_status(entry)) for entry in entries)


def _unknown_statuses(entries: list[dict[str, Any]]) -> list[str]:
    statuses = {_entry_status(entry) for entry in entries if _entry_status(entry)}
    return sorted(status for status in statuses if classify_status(status) == "unknown_status")


def _recommendations(entries: list[dict[str, Any]], issues: list[dict[str, Any]]) -> list[str]:
    class_counts = _status_class_counts(entries)
    recommendations: list[str] = []

    legacy_count = class_counts.get("legacy_runtime_wired", 0)
    if legacy_count:
        recommendations.append(
            f"Review {legacy_count} legacy runtime-wired entries for prod corpus sync "
            "and public verification evidence."
        )

    present_count = class_counts.get("texts_present_index_volume_wired", 0)
    if present_count:
        recommendations.append(
            f"Review {present_count} texts-present/index-volume entries for explicit "
            "index, runtime, production, and public-verification status."
        )

    pending_count = class_counts.get("pending", 0)
    if pending_count:
        recommendations.append(
            f"Prioritize candidate/source-card packets for {pending_count} pending entries."
        )

    missing_inventory_count = sum(
        1 for row in issues if row["code"] == "entry_missing_works_inventory"
    )
    if missing_inventory_count:
        recommendations.append(
            f"Backfill ledger works inventory for {missing_inventory_count} progressed entries "
            "so key works are not mistaken for full acquisition coverage."
        )

    corpus_gap_count = sum(
        1 for row in issues if row["code"] == "entry_inventory_corpus_mismatch"
    )
    if corpus_gap_count:
        recommendations.append(
            f"Repair {corpus_gap_count} ledger entries whose works inventory is smaller than the "
            "corpus already mounted in AugustineCorpus."
        )

    if not recommendations:
        recommendations.append("No tracker backlog recommendations generated.")
    return recommendations


def build_tracker_audit(
    fortress_ledger: Path,
    service_ledger: Path,
    corpus_root: Path | None = None,
) -> dict[str, Any]:
    fortress_data, fortress_load_issues = _load_json(fortress_ledger)
    service_data, service_load_issues = _load_json(service_ledger)
    issues = [*fortress_load_issues, *service_load_issues]

    fortress_entries: list[dict[str, Any]] = []
    service_entries: list[dict[str, Any]] = []
    if fortress_data is not None:
        fortress_entries, fortress_issues = _validate_entries("fortress", fortress_data)
        issues.extend(fortress_issues)
    if service_data is not None:
        service_entries, service_issues = _validate_entries("service", service_data)
        issues.extend(service_issues)

    fortress_bytes = _read_bytes(fortress_ledger)
    service_bytes = _read_bytes(service_ledger)
    byte_equal = (
        fortress_bytes is not None and service_bytes is not None and fortress_bytes == service_bytes
    )
    semantic_equal = (
        fortress_data is not None and service_data is not None and fortress_data == service_data
    )

    if fortress_data is not None and service_data is not None:
        if not semantic_equal:
            issues.append(
                _issue(
                    "error",
                    "ledger_semantic_drift",
                    "The two acquisition ledgers are not semantically equal.",
                )
            )
        elif not byte_equal:
            issues.append(
                _issue(
                    "warning",
                    "ledger_byte_drift",
                    "The two acquisition ledgers parse equally but are not byte-identical.",
                )
            )

    source_entries = fortress_entries if fortress_entries else service_entries
    corpus_lookup, corpus_issues = _load_corpus_work_lookup(corpus_root or default_corpus_root_path())
    issues.extend(corpus_issues)

    duplicate_names = _duplicate_names(source_entries)
    for names in duplicate_names.values():
        issues.append(
            _issue(
                "warning",
                "duplicate_author_name",
                f"Duplicate author name detected: {names[0]}",
                names=names,
            )
        )

    for status in _unknown_statuses(source_entries):
        issues.append(
            _issue(
                "warning",
                "unknown_status",
                f"Unknown acquisition status: {status}",
                status=status,
            )
        )

    for entry in source_entries:
        name = _entry_name(entry)
        if not name:
            continue
        status = _entry_status(entry)
        status_class = classify_status(status)
        if status_class in {"pending", "queued_pending_text_acquisition", "unknown_status"}:
            continue

        key_works = _extract_key_works(entry)
        inventory = _extract_inventory_works(entry)
        corpus_row = (
            corpus_lookup.get(_normalize_author_key(name))
            or corpus_lookup.get(_slugify_author_key(name))
        )
        corpus_work_count = int((corpus_row or {}).get("corpus_work_count") or 0)

        if not inventory:
            issues.append(
                _issue(
                    "warning",
                    "entry_missing_works_inventory",
                    f"{name} has progressed status but no works inventory recorded in the ledger.",
                    author=name,
                    status=status,
                    key_works_count=len(key_works),
                    corpus_work_count=corpus_work_count,
                )
            )
            continue

        if corpus_work_count and len(inventory) < corpus_work_count:
            issues.append(
                _issue(
                    "warning",
                    "entry_inventory_corpus_mismatch",
                    f"{name} ledger inventory records {len(inventory)} works but corpus holds {corpus_work_count}.",
                    author=name,
                    status=status,
                    ledger_inventory_count=len(inventory),
                    corpus_work_count=corpus_work_count,
                )
            )

    error_codes = [row["code"] for row in issues if row["severity"] == "error"]
    write_blockers: list[str] = []
    if error_codes:
        write_blockers.append("audit_errors_present")
    if not semantic_equal:
        write_blockers.append("semantic_ledger_drift")
    if not byte_equal:
        write_blockers.append("byte_ledger_drift")

    status_counts = _status_counts(source_entries)
    class_counts = _status_class_counts(source_entries)

    return {
        "packet_type": "tracker_audit_report",
        "dry_run": True,
        "ledger_sync": {
            "fortress_ledger": str(fortress_ledger),
            "service_ledger": str(service_ledger),
            "byte_equal": byte_equal,
            "semantic_equal": semantic_equal,
            "fortress_count": len(fortress_entries),
            "service_count": len(service_entries),
        },
        "ledger_write_guard": {
            "status": "allowed" if not write_blockers else "blocked",
            "blockers": write_blockers,
        },
        "status_counts": dict(sorted(status_counts.items())),
        "status_class_counts": dict(sorted(class_counts.items())),
        "issues": issues,
        "recommendations": _recommendations(source_entries, issues),
    }


def _print_json(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def _print_audit_text(report: dict[str, Any]) -> None:
    sync = report["ledger_sync"]
    guard = report["ledger_write_guard"]
    print("Author Acquisition Tracker Audit")
    print(f"dry_run: {str(report['dry_run']).lower()}")
    print(f"fortress_ledger: {sync['fortress_ledger']}")
    print(f"service_ledger: {sync['service_ledger']}")
    print(
        "ledger_sync:",
        f"byte_equal={sync['byte_equal']}",
        f"semantic_equal={sync['semantic_equal']}",
        f"counts={sync['fortress_count']}/{sync['service_count']}",
    )
    print(f"ledger_write_guard: {guard['status']}")
    if guard["blockers"]:
        print("write_blockers:")
        for blocker in guard["blockers"]:
            print(f"- {blocker}")

    print("\nstatus_counts:")
    for status, count in report["status_counts"].items():
        print(f"- {count:3} {status}")

    print("\nstatus_class_counts:")
    for status_class, count in report["status_class_counts"].items():
        print(f"- {count:3} {status_class}")

    print("\nissues:")
    if report["issues"]:
        for row in report["issues"]:
            print(f"- [{row['severity']}] {row['code']}: {row['message']}")
    else:
        print("- none")

    print("\nrecommendations:")
    for item in report["recommendations"]:
        print(f"- {item}")


def _print_status_report(report: dict[str, Any]) -> None:
    print("Author Acquisition Status Report")
    for status, count in sorted(
        report["status_counts"].items(), key=lambda item: (-item[1], item[0])
    ):
        print(f"{count:3} {status}")


def _print_coverage_text(report: dict[str, Any]) -> None:
    print("Author Acquisition Coverage Audit")
    print(f"dry_run: {str(report['dry_run']).lower()}")
    print(f"source: {report.get('source')}")
    print(f"authors_scanned: {report.get('authors_scanned', 0)}")
    print(f"authors_with_gaps: {report.get('authors_with_gaps', 0)}")
    print(f"publication_gap_count: {report.get('publication_gap_count', 0)}")
    print("\nauthor_reports:")
    if not report.get("author_reports"):
        print("- none")
    else:
        for author in report["author_reports"]:
            print(
                f"- {author['author_name']} ({author['author_slug']}): "
                f"{author['gap_count']} missing work candidate(s) from {author['source']}"
            )
            for gap in author.get("publication_gap_packets", [])[:10]:
                print(f"  - {gap['work_title']} [{gap['classification']}]")

    print("\nissues:")
    if report.get("issues"):
        for row in report["issues"]:
            print(f"- [{row['severity']}] {row['code']}: {row['message']}")
    else:
        print("- none")


def _paths_from_args(args: argparse.Namespace) -> tuple[Path, Path]:
    fortress_ledger = (
        Path(args.fortress_ledger)
        if args.fortress_ledger
        else default_fortress_ledger_path()
    )
    service_ledger = (
        Path(args.service_ledger) if args.service_ledger else default_service_ledger_path()
    )
    return fortress_ledger, service_ledger


def _has_errors(report: dict[str, Any]) -> bool:
    return any(row["severity"] == "error" for row in report["issues"])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="author-acq",
        description="Dry-run author acquisition tracker and audit tools.",
    )
    parser.add_argument("--fortress-ledger", default="", help="Path to Fortress ledger JSON")
    parser.add_argument("--service-ledger", default="", help="Path to AugustineService ledger JSON")
    parser.add_argument("--corpus-root", default="", help="Path to AugustineCorpus checkout root")

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit-tracker", help="Build tracker audit packet")
    audit_parser.add_argument("--dry-run", action="store_true", help="Accepted for contract clarity")
    audit_parser.add_argument("--format", choices=["text", "json"], default="text")

    coverage_parser = subparsers.add_parser(
        "audit-coverage",
        help="Query acquired authors against a bibliographic source to find missing works",
    )
    coverage_parser.add_argument("--dry-run", action="store_true", help="Accepted for contract clarity")
    coverage_parser.add_argument("--format", choices=["text", "json"], default="text")
    coverage_parser.add_argument("--author", default="", help="Optional exact author name/slug filter")
    coverage_parser.add_argument("--status", default="", help="Optional exact status-string filter")
    coverage_parser.add_argument("--max-pages", type=int, default=4)
    coverage_parser.add_argument(
        "--include-bibliographic-only",
        action="store_true",
        help="Include non-fulltext bibliographic candidates in the gap report",
    )

    validate_parser = subparsers.add_parser("validate-ledgers", help="Validate ledger sync")
    validate_parser.add_argument("--format", choices=["text", "json"], default="text")

    status_parser = subparsers.add_parser("status-report", help="Print status counts")
    status_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    fortress_ledger, service_ledger = _paths_from_args(args)
    corpus_root = Path(args.corpus_root) if args.corpus_root else default_corpus_root_path()
    report = build_tracker_audit(fortress_ledger, service_ledger, corpus_root=corpus_root)

    if args.command == "audit-tracker":
        if args.format == "json":
            _print_json(report)
        else:
            _print_audit_text(report)
        return 1 if _has_errors(report) else 0

    if args.command == "audit-coverage":
        coverage = build_coverage_audit(
            fortress_ledger,
            service_ledger,
            corpus_root=corpus_root,
            author_filter=args.author,
            status_filter=args.status,
            max_pages=max(1, args.max_pages),
            include_bibliographic_only=bool(args.include_bibliographic_only),
        )
        if args.format == "json":
            _print_json(coverage)
        else:
            _print_coverage_text(coverage)
        return 1 if _has_errors(coverage) else 0

    if args.command == "validate-ledgers":
        if args.format == "json":
            _print_json(report)
        else:
            guard = report["ledger_write_guard"]
            if guard["status"] == "allowed":
                print("Ledger validation passed: ledgers are byte-identical and writable.")
            else:
                print("Ledger validation failed: write guard is blocked.")
                for blocker in guard["blockers"]:
                    print(f"- {blocker}")
        return 0 if report["ledger_write_guard"]["status"] == "allowed" else 1

    if args.command == "status-report":
        if args.format == "json":
            _print_json(report)
        else:
            _print_status_report(report)
        return 1 if _has_errors(report) else 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
