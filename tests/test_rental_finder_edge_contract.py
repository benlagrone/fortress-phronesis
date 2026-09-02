from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RentalFinderEdgeContractTests(unittest.TestCase):
    def test_compose_is_loopback_only_and_workspace_restricted(self) -> None:
        compose = (ROOT / "docker-compose.rental-finder.yml").read_text(encoding="utf-8")

        self.assertIn("127.0.0.1:18044:4180", compose)
        self.assertIn("OAUTH2_PROXY_PROVIDER: google", compose)
        self.assertIn("OAUTH2_PROXY_EMAIL_DOMAINS: lecrownproperties.com", compose)
        self.assertIn("https://rentalfinder.lecrownproperties.com/oauth2/callback", compose)
        self.assertIn("OAUTH2_PROXY_PASS_ACCESS_TOKEN: \"false\"", compose)
        self.assertIn("OAUTH2_PROXY_PASS_AUTHORIZATION_HEADER: \"false\"", compose)
        self.assertIn("OAUTH2_PROXY_COOKIE_NAME: __Host-rental_finder_session", compose)
        self.assertRegex(compose, r"oauth2-proxy:v7\.15\.3@sha256:[0-9a-f]{64}")

    def test_remote_script_protects_ui_and_api_paths(self) -> None:
        script = (ROOT / "scripts" / "deploy-rental-finder-remote.sh").read_text(encoding="utf-8")

        self.assertIn(
            'BACKEND_ORIGIN="${RENTAL_FINDER_BACKEND_ORIGIN:-http://100.121.75.0:8134}"',
            script,
        )
        self.assertIn("auth_request /_oauth2_auth;", script)
        self.assertIn("location ^~ /rental-finder/api/", script)
        self.assertIn("location / {", script)
        self.assertIn("proxy_pass ${BACKEND_ORIGIN}/rental-finder/;", script)
        self.assertIn("proxy_set_header Authorization \"\";", script)
        self.assertIn("X-Authenticated-Email", script)
        self.assertIn("Expected unauthenticated UI request to return 302", script)
        self.assertIn("Expected unauthenticated API request to return 302", script)

    def test_bootstrap_mode_is_tls_enabled_and_fail_closed(self) -> None:
        script = (ROOT / "scripts" / "deploy-rental-finder-remote.sh").read_text(encoding="utf-8")

        self.assertIn('BOOTSTRAP_ONLY="${RENTAL_FINDER_BOOTSTRAP_ONLY:-false}"', script)
        self.assertIn("write_https_unavailable_site", script)
        self.assertIn('return 503 "Rental Finder is temporarily unavailable', script)
        self.assertIn('Expected fail-closed site to return 503', script)
        self.assertIn('ssl_certificate /etc/letsencrypt/live/${PUBLIC_HOST}/fullchain.pem;', script)

    def test_workflow_does_not_embed_oauth_secrets(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "deploy-rental-finder.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("secrets.RENTAL_FINDER_GOOGLE_CLIENT_ID", workflow)
        self.assertIn("secrets.RENTAL_FINDER_GOOGLE_CLIENT_SECRET", workflow)
        self.assertIn("secrets.RENTAL_FINDER_OAUTH_COOKIE_SECRET", workflow)
        self.assertIn("${REMOTE_STAGE}/scripts/deploy-rental-finder-remote.sh", workflow)
        self.assertNotRegex(workflow, re.compile(r"client_secret\s*[:=]\s*[A-Za-z0-9_-]{20,}", re.IGNORECASE))
        self.assertIn("rm -f \"${LOCAL_OAUTH_ENV:-}\"", workflow)


if __name__ == "__main__":
    unittest.main()
