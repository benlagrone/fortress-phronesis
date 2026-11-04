import base64
import hashlib
import io
import tarfile
import unittest
from pathlib import Path
from unittest.mock import patch

from install_release import new_vhost_text, pursuit_health, semantic_health, rollback, validate_payload
from deploy import validate_source


class DeploymentBoundaryTest(unittest.TestCase):
    def test_cutover_preserves_tls_and_other_configuration(self):
        text = "server { server_name app.lecrowndevelopment.com; ssl_certificate /kept/cert; location / { proxy_pass http://127.0.0.1:13084; } }"
        result = new_vhost_text("app.lecrowndevelopment.com", text)
        self.assertIn("/kept/cert", result)
        self.assertIn("127.0.0.1:13095", result)
        self.assertEqual(result, new_vhost_text("app.lecrowndevelopment.com", result))

    def test_refuses_a_shared_properties_vhost(self):
        with self.assertRaises(RuntimeError):
            new_vhost_text("app.lecrowndevelopment.com", "server_name app.lecrowndevelopment.com backoffice.lecrownproperties.com; proxy_pass http://127.0.0.1:13084;")

    def test_refuses_unexpected_upstream(self):
        with self.assertRaises(RuntimeError):
            new_vhost_text("api.lecrowndevelopment.com", "server_name api.lecrowndevelopment.com; proxy_pass http://127.0.0.1:9999;")

    def payload(self, name):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode="w:gz") as tar:
            item = tarfile.TarInfo(name)
            tar.addfile(item, io.BytesIO(b""))
        archive = stream.getvalue()
        return {"source_sha": "a" * 40, "runtime": {key: "test" for key in ["SECRET_KEY", "ADMIN_USERNAME", "ADMIN_PASSWORD", "ESPOCRM_USERNAME", "ESPOCRM_PASSWORD"]},
                "archive": base64.b64encode(archive).decode(), "archive_sha256": hashlib.sha256(archive).hexdigest()}

    def test_archive_is_bounded_to_application_source(self):
        self.assertTrue(validate_payload(self.payload("platform/backend/app/main.py")))
        for name in ("../escape", "/etc/passwd", "data/companies.csv", "platform/../../escape"):
            with self.assertRaises(ValueError):
                validate_payload(self.payload(name))

    def test_archive_requires_exact_digest_and_runtime_keys(self):
        payload = self.payload("platform/backend/app/main.py")
        payload["archive_sha256"] = "incorrect"
        with self.assertRaises(ValueError):
            validate_payload(payload)

    def test_clean_source_override_stays_in_locked_repository(self):
        with patch("deploy.git", side_effect=[b"/private/tmp/source\n", b"https://github.com/benlagrone/lecrown-platform.git\n"]):
            self.assertEqual(Path("/private/tmp/source"), validate_source(Path("/private/tmp/source")))
        with patch("deploy.git", side_effect=[b"/private/tmp/source\n", b"https://github.com/other/repository.git\n"]):
            with self.assertRaises(ValueError):
                validate_source(Path("/private/tmp/source"))

    def test_worker_health_requires_successful_pass_of_exact_revision(self):
        import json
        with patch("install_release.run", side_effect=["running healthy", json.dumps({"status": "ok", "source_sha": "a" * 40, "count": 22})]):
            self.assertEqual(22, pursuit_health("a" * 40)["count"])
        with patch("install_release.run", return_value="running unhealthy"), patch("install_release.time.sleep"):
            with self.assertRaises(RuntimeError):
                pursuit_health("a" * 40)

    def test_rollback_removes_only_development_project_orphans(self):
        import json
        with patch("pathlib.Path.read_text", return_value=json.dumps({"vhosts": {}, "previous_release": {"source_sha": "old"}})), \
             patch("install_release.shutil.copy2"), patch("install_release.run"), \
             patch("install_release.private_write"), patch("install_release.compose") as compose:
            rollback(Path("/backup"), {})
            self.assertEqual(("up", "-d", "--remove-orphans"), compose.call_args.args[1:])

    def test_semantic_health_requires_trained_exact_revision(self):
        import json
        health = {"status": "ok", "source_sha": "a" * 40, "evaluation": {"ready": True}, "training_count": 499, "checked_at": "2026-11-04T22:00:00Z"}
        inspected = [{"Config": {"Env": ["DATABASE_URL=test"]}, "HostConfig": {"ReadonlyRootfs": True}, "State": {"StartedAt": "2026-11-04T21:59:00Z"}}]
        with patch("install_release.run", side_effect=["running healthy", json.dumps(health), json.dumps(inspected)]):
            self.assertEqual(499, semantic_health("a" * 40)["training_count"])
        with patch("install_release.run", return_value="running unhealthy"), patch("install_release.time.sleep"):
            with self.assertRaises(RuntimeError):
                semantic_health("a" * 40)

    def test_semantic_worker_has_no_app_or_crm_credentials(self):
        text = (Path(__file__).parent / "compose.yaml").read_text()
        worker = text.split("  semantic-qualifier:\n", 1)[1].split("  pursuit-ranker:", 1)[0]
        for secret in ["*runtime", "ADMIN_PASSWORD", "ESPOCRM_PASSWORD", "SECRET_KEY"]:
            self.assertNotIn(secret, worker)
        self.assertIn("read_only: true", worker)
        self.assertIn("no-new-privileges:true", worker)


if __name__ == "__main__":
    unittest.main()
