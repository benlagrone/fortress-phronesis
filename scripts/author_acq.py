#!/usr/bin/env python3
"""Dry-run author acquisition tracker tools.

Phase 0 intentionally reads and reports only. It does not mutate ledgers,
download sources, build indexes, or touch production state.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PUBLIC_VERIFIED_STATUS = (
    "texts downloaded; prod corpus synced; index built; runtime wired; "
    "public verification passed"
)

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
    return _repo_root().parent / "AugustineService" / "metadata" / "author_acquisition.json"


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


def _recommendations(entries: list[dict[str, Any]]) -> list[str]:
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

    if not recommendations:
        recommendations.append("No tracker backlog recommendations generated.")
    return recommendations


def build_tracker_audit(fortress_ledger: Path, service_ledger: Path) -> dict[str, Any]:
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
        "recommendations": _recommendations(source_entries),
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit-tracker", help="Build tracker audit packet")
    audit_parser.add_argument("--dry-run", action="store_true", help="Accepted for contract clarity")
    audit_parser.add_argument("--format", choices=["text", "json"], default="text")

    validate_parser = subparsers.add_parser("validate-ledgers", help="Validate ledger sync")
    validate_parser.add_argument("--format", choices=["text", "json"], default="text")

    status_parser = subparsers.add_parser("status-report", help="Print status counts")
    status_parser.add_argument("--format", choices=["text", "json"], default="text")

    args = parser.parse_args(argv)
    fortress_ledger, service_ledger = _paths_from_args(args)
    report = build_tracker_audit(fortress_ledger, service_ledger)

    if args.command == "audit-tracker":
        if args.format == "json":
            _print_json(report)
        else:
            _print_audit_text(report)
        return 1 if _has_errors(report) else 0

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
