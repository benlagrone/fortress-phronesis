from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


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


def _json_response(payload: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    context = MagicMock()
    context.__enter__.return_value = response
    context.__exit__.return_value = False
    return context


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

    def test_tracker_audit_warns_when_progressed_entry_has_no_works_inventory(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fortress = tmp_path / "fortress" / "author_acquisition.json"
            service = tmp_path / "service" / "author_acquisition.json"
            corpus_root = tmp_path / "AugustineCorpus"
            texts_dir = corpus_root / "texts" / "author_a_texts"
            texts_dir.mkdir(parents=True, exist_ok=True)
            (corpus_root / "author_index.json").write_text(
                json.dumps(
                    [
                        {
                            "slug": "author_a",
                            "name": "Author A",
                            "catalog_name": "Author A",
                            "texts_dir": "texts/author_a_texts",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (texts_dir / "book_metadata.json").write_text(
                json.dumps(
                    [
                        {"filename": "work_one.txt", "title": "Work One"},
                        {"filename": "work_two.txt", "title": "Work Two"},
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            entries = [
                {
                    "name": "Author A",
                    "status": (
                        "texts downloaded; prod corpus synced; index built; runtime wired; "
                        "public verification passed"
                    ),
                    "notes": ["Key Works: Work One; Work Two"],
                }
            ]
            _write_ledger(fortress, entries)
            service.parent.mkdir(parents=True, exist_ok=True)
            service.write_bytes(fortress.read_bytes())

            report = author_acq.build_tracker_audit(fortress, service, corpus_root=corpus_root)
            issue_codes = [issue["code"] for issue in report["issues"]]

            self.assertIn("entry_missing_works_inventory", issue_codes)
            self.assertIn(
                "Backfill ledger works inventory",
                " ".join(report["recommendations"]),
            )

    def test_coverage_audit_emits_gap_packet_for_missing_external_work(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fortress = tmp_path / "fortress" / "author_acquisition.json"
            service = tmp_path / "service" / "author_acquisition.json"
            corpus_root = tmp_path / "AugustineCorpus"
            texts_dir = corpus_root / "texts" / "author_a_texts"
            texts_dir.mkdir(parents=True, exist_ok=True)
            (corpus_root / "author_index.json").write_text(
                json.dumps(
                    [
                        {
                            "slug": "author_a",
                            "name": "Author A",
                            "catalog_name": "Author A",
                            "texts_dir": "texts/author_a_texts",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (texts_dir / "book_metadata.json").write_text(
                json.dumps(
                    [
                        {"filename": "present_work.txt", "title": "Present Work"},
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            entries = [
                {
                    "name": "Author A",
                    "status": (
                        "texts downloaded; prod corpus synced; index built; runtime wired; "
                        "public verification passed"
                    ),
                    "works": ["Present Work"],
                    "notes": ["Key Works: Present Work"],
                }
            ]
            _write_ledger(fortress, entries)
            service.parent.mkdir(parents=True, exist_ok=True)
            service.write_bytes(fortress.read_bytes())

            with patch.object(
                author_acq,
                "_fetch_coverage_source_books_for_author",
                return_value={
                    "source": "openlibrary",
                    "author_name": "Author A",
                    "pages_visited": ["https://openlibrary.org/search.json?author=Author+A"],
                    "books": [
                        {
                            "key": "/works/OL1W",
                            "title": "Present Work",
                            "author_name": ["Author A"],
                            "has_fulltext": True,
                            "ia": ["present_work"],
                        },
                        {
                            "key": "/works/OL2W",
                            "title": "Missing Work",
                            "author_name": ["Author A"],
                            "has_fulltext": True,
                            "ia": ["missing_work"],
                        },
                    ],
                },
            ):
                report = author_acq.build_coverage_audit(
                    fortress,
                    service,
                    corpus_root=corpus_root,
                )

            self.assertEqual(report["packet_type"], "coverage_audit_report")
            self.assertEqual(report["authors_scanned"], 1)
            self.assertEqual(report["authors_with_gaps"], 1)
            self.assertEqual(report["publication_gap_count"], 1)
            self.assertEqual(report["author_summaries"][0]["external_work_count"], 2)
            self.assertEqual(report["author_summaries"][0]["external_candidate_count"], 1)
            self.assertEqual(report["author_reports"][0]["author_slug"], "author_a")
            self.assertEqual(
                report["author_reports"][0]["publication_gap_packets"][0]["work_title"],
                "Missing Work",
            )
            self.assertEqual(
                report["source_card_candidates"][0]["source_url"],
                "https://archive.org/details/missing_work",
            )

    def test_openlibrary_fetch_resolves_canonical_author_key(self) -> None:
        with patch.object(
            author_acq.urllib.request,
            "urlopen",
            side_effect=[
                _json_response(
                    {
                        "docs": [
                            {
                                "key": "OL143103A",
                                "name": "Boethius",
                                "top_work": "The Consolation of Philosophy",
                                "work_count": 364,
                            },
                            {
                                "key": "OL124018A",
                                "name": "Axel Boëthius",
                                "top_work": "Die Pythaïs",
                                "work_count": 46,
                            },
                        ]
                    }
                ),
                _json_response(
                    {
                        "docs": [
                            {
                                "key": "/works/OL1W",
                                "title": "The Consolation of Philosophy",
                                "author_name": ["Boethius"],
                                "author_key": ["OL143103A"],
                                "has_fulltext": True,
                                "ia": ["consolation_of_philosophy"],
                            },
                            {
                                "key": "/works/OL2W",
                                "title": "Etruscan and early Roman architecture",
                                "author_name": ["Axel Boëthius"],
                                "author_key": ["OL124018A"],
                                "has_fulltext": True,
                                "ia": ["etruscan_architecture"],
                            },
                        ]
                    }
                ),
            ],
        ):
            payload = author_acq._fetch_openlibrary_books_for_author("Boethius", max_pages=1)

        self.assertEqual(payload["resolved_author_key"], "OL143103A")
        self.assertIn("author_key=OL143103A", payload["pages_visited"][0])
        self.assertEqual(
            [book["title"] for book in payload["books"]],
            ["The Consolation of Philosophy"],
        )

    def test_coverage_audit_retains_summary_for_author_without_gap_packets(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fortress = tmp_path / "fortress" / "author_acquisition.json"
            service = tmp_path / "service" / "author_acquisition.json"
            corpus_root = tmp_path / "AugustineCorpus"
            texts_dir = corpus_root / "texts" / "author_a_texts"
            texts_dir.mkdir(parents=True, exist_ok=True)
            (corpus_root / "author_index.json").write_text(
                json.dumps(
                    [
                        {
                            "slug": "author_a",
                            "name": "Author A",
                            "catalog_name": "Author A",
                            "texts_dir": "texts/author_a_texts",
                        }
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (texts_dir / "book_metadata.json").write_text(
                json.dumps(
                    [
                        {"filename": "present_work.txt", "title": "Present Work"},
                    ],
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            entries = [
                {
                    "name": "Author A",
                    "status": (
                        "texts downloaded; prod corpus synced; index built; runtime wired; "
                        "public verification passed"
                    ),
                    "works": ["Present Work"],
                    "notes": ["Key Works: Present Work"],
                }
            ]
            _write_ledger(fortress, entries)
            service.parent.mkdir(parents=True, exist_ok=True)
            service.write_bytes(fortress.read_bytes())

            with patch.object(
                author_acq,
                "_fetch_coverage_source_books_for_author",
                return_value={
                    "source": "openlibrary",
                    "author_name": "Author A",
                    "pages_visited": ["https://openlibrary.org/search.json?author=Author+A"],
                    "books": [
                        {
                            "key": "/works/OL1W",
                            "title": "Present Work",
                            "author_name": ["Author A"],
                            "has_fulltext": True,
                            "ia": ["present_work"],
                        }
                    ],
                },
            ):
                report = author_acq.build_coverage_audit(
                    fortress,
                    service,
                    corpus_root=corpus_root,
                )

            self.assertEqual(report["authors_scanned"], 1)
            self.assertEqual(report["authors_with_gaps"], 0)
            self.assertEqual(report["author_reports"], [])
            self.assertEqual(len(report["author_summaries"]), 1)
            self.assertEqual(report["author_summaries"][0]["author_slug"], "author_a")
            self.assertEqual(report["author_summaries"][0]["external_work_count"], 1)
            self.assertEqual(report["author_summaries"][0]["external_candidate_count"], 0)
            self.assertEqual(report["author_summaries"][0]["gap_count"], 0)


if __name__ == "__main__":
    unittest.main()
