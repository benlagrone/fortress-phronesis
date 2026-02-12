#!/usr/bin/env python3
"""Preflight check for author text inputs and optional failed test selection."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _load_author_slugs(author_index_path: Path) -> List[str]:
    data = json.loads(author_index_path.read_text(encoding="utf-8"))
    slugs = []
    for item in data:
        slug = item.get("slug")
        if slug:
            slugs.append(str(slug))
    return slugs


def _load_failed_slugs(results_path: Path) -> List[str]:
    slugs: List[str] = []
    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if row.get("pass") is False or row.get("error"):
                slug = row.get("author")
                if slug:
                    slugs.append(str(slug))
    return slugs


def _scan_text_dir(texts_root: Path, slug: str) -> Dict[str, Any]:
    base = texts_root / f"{slug}_texts"
    row: Dict[str, Any] = {
        "author": slug,
        "dir_exists": base.exists(),
        "txt_count": 0,
        "txt_empty": 0,
        "txt_bytes": 0,
        "html_count": 0,
        "pdf_count": 0,
        "djvu_count": 0,
        "other_count": 0,
    }
    if not base.exists():
        return row

    for path in base.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        size = path.stat().st_size
        if ext == ".txt":
            row["txt_count"] += 1
            row["txt_bytes"] += size
            if size == 0:
                row["txt_empty"] += 1
        elif ext == ".html":
            row["html_count"] += 1
        elif ext == ".pdf":
            row["pdf_count"] += 1
        elif ext in (".djvu", ".djv"):
            row["djvu_count"] += 1
        else:
            row["other_count"] += 1
    return row


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    header = (
        f"{'author':28} {'txt':>4} {'empty':>5} {'bytes':>10} "
        f"{'html':>4} {'pdf':>3} {'djvu':>4} {'other':>5} {'dir'}"
    )
    print(header)
    for row in rows:
        print(
            f"{row['author']:28} {row['txt_count']:4} {row['txt_empty']:5} "
            f"{row['txt_bytes']:10} {row['html_count']:4} {row['pdf_count']:3} "
            f"{row['djvu_count']:4} {row['other_count']:5} "
            f"{'Y' if row['dir_exists'] else 'N'}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight author text inputs.")
    parser.add_argument(
        "--author-index",
        default="AugustineCorpus/author_index.json",
        help="Path to author_index.json",
    )
    parser.add_argument(
        "--texts-root",
        default="AugustineCorpus/texts",
        help="Root texts directory",
    )
    parser.add_argument(
        "--authors",
        default="",
        help="Comma-separated author slugs (overrides results/author_index)",
    )
    parser.add_argument(
        "--results",
        default="",
        help="Path to author-chat-test.jsonl to restrict to failing authors",
    )
    parser.add_argument(
        "--format",
        choices=["table", "jsonl", "csv"],
        default="table",
        help="Output format",
    )
    parser.add_argument(
        "--out",
        default="",
        help="Output file path (required for jsonl/csv)",
    )
    args = parser.parse_args()

    slugs: List[str]
    if args.authors:
        slugs = [s.strip() for s in args.authors.split(",") if s.strip()]
    elif args.results:
        slugs = _load_failed_slugs(Path(args.results))
    else:
        slugs = _load_author_slugs(Path(args.author_index))

    if not slugs:
        sys.stderr.write("No authors selected.\n")
        return 1

    texts_root = Path(args.texts_root)
    rows = [_scan_text_dir(texts_root, slug) for slug in slugs]

    if args.format == "table":
        _print_table(rows)
        return 0

    if not args.out:
        sys.stderr.write("--out is required for jsonl/csv output.\n")
        return 1

    out_path = Path(args.out)
    if args.format == "jsonl":
        _write_jsonl(out_path, rows)
    else:
        _write_csv(out_path, rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
