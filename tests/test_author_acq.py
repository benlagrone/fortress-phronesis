from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "author_acq.py"
SPEC = importlib.util.spec_from_file_location("author_acq", MODULE_PATH)
assert SPEC is not None
author_acq = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(author_acq)


def _write_ledger(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


class AuthorAcqTrackerAuditTests(unittest.TestCase):
    def test_tracker_audit_allows_identical_ledgers(self) -> None:
        with self.subTest("identical ledgers"):
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                fortress = tmp_path / "fortress" / "author_acquisition.json"
                service = tmp_path / "service" / "author_acquisition.json"
                entries = [
                    {"name": "Author A", "status": "pending"},
                    {
                        "name": "Author B",
                        "status": "texts downloaded; index built; runtime wired",
                    },
                    {
                        "name": "Author C",
                        "status": (
                            "texts downloaded; prod corpus synced; index built; runtime wired; "
                            "public verification passed"
                        ),
                    },
                ]
                _write_ledger(fortress, entries)
                service.parent.mkdir(parents=True, exist_ok=True)
                service.write_bytes(fortress.read_bytes())

                report = author_acq.build_tracker_audit(fortress, service)

                self.assertIs(report["ledger_sync"]["byte_equal"], True)
                self.assertIs(report["ledger_sync"]["semantic_equal"], True)
                self.assertEqual(report["ledger_write_guard"]["status"], "allowed")
                self.assertEqual(report["status_counts"]["pending"], 1)
                self.assertEqual(report["status_class_counts"]["legacy_runtime_wired"], 1)
                self.assertEqual(report["status_class_counts"]["public_verification_passed"], 1)

    def test_tracker_audit_blocks_semantic_drift(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fortress = tmp_path / "fortress" / "author_acquisition.json"
            service = tmp_path / "service" / "author_acquisition.json"
            _write_ledger(fortress, [{"name": "Author A", "status": "pending"}])
            _write_ledger(
                service,
                [{"name": "Author A", "status": "texts present; index volume wired"}],
            )

            report = author_acq.build_tracker_audit(fortress, service)

            self.assertIs(report["ledger_sync"]["byte_equal"], False)
            self.assertIs(report["ledger_sync"]["semantic_equal"], False)
            self.assertEqual(report["ledger_write_guard"]["status"], "blocked")
            self.assertIn("semantic_ledger_drift", report["ledger_write_guard"]["blockers"])
            self.assertTrue(
                any(issue["code"] == "ledger_semantic_drift" for issue in report["issues"])
            )

    def test_tracker_audit_warns_on_unknown_status_and_duplicate_name(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fortress = tmp_path / "fortress" / "author_acquisition.json"
            service = tmp_path / "service" / "author_acquisition.json"
            entries = [
                {"name": "Author A", "status": "pending"},
                {"name": "author a", "status": "made up status"},
            ]
            _write_ledger(fortress, entries)
            service.parent.mkdir(parents=True, exist_ok=True)
            service.write_bytes(fortress.read_bytes())

            report = author_acq.build_tracker_audit(fortress, service)
            issue_codes = [issue["code"] for issue in report["issues"]]

            self.assertEqual(report["ledger_write_guard"]["status"], "allowed")
            self.assertIn("duplicate_author_name", issue_codes)
            self.assertIn("unknown_status", issue_codes)
            self.assertEqual(report["status_class_counts"]["unknown_status"], 1)


if __name__ == "__main__":
    unittest.main()
