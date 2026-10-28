import base64
import hashlib
import io
import tarfile
import unittest

from install_release import new_vhost_text, validate_payload


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


if __name__ == "__main__":
    unittest.main()
