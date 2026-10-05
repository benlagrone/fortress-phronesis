from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import sys
import types
import unittest


SERVICE_PATH = Path(__file__).resolve().parents[1] / "services" / "lecrown-billing" / "server.py"


def _load_server_module():
    if "stripe" not in sys.modules:
        stripe_stub = types.ModuleType("stripe")
        stripe_stub.StripeClient = object
        stripe_stub.StripeError = Exception
        sys.modules["stripe"] = stripe_stub
    spec = importlib.util.spec_from_file_location("lecrown_billing_server", SERVICE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SERVICE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


server = _load_server_module()


class _SubscriptionClient:
    data: list[object] = []

    def list(self, _payload):
        return self


class _CheckoutSessionsClient:
    def __init__(self) -> None:
        self.payload = None
        self.options = None

    def create(self, payload, options):
        self.payload = payload
        self.options = options
        return types.SimpleNamespace(id="cs_live_checkout", url="https://checkout.stripe.com/c/pay/test", livemode=True)


class LecrownBillingCheckoutTests(unittest.TestCase):
    def test_checkout_uses_top_level_stripe_integration_identifier(self) -> None:
        service = server.BillingService.__new__(server.BillingService)
        checkout_sessions = _CheckoutSessionsClient()
        service.settings = types.SimpleNamespace(stripe_mode="live", allowed_return_origins=("https://truevineos.cloud",))
        service.client = types.SimpleNamespace(
            v1=types.SimpleNamespace(
                subscriptions=_SubscriptionClient(),
                checkout=types.SimpleNamespace(sessions=checkout_sessions),
            )
        )
        service._price_for_lookup_key = lambda _lookup_key: {"id": "price_live_starter"}
        service._get_or_create_customer = lambda _user_id, _email: "cus_live_reader"

        result = service.create_checkout(
            {
                "project": "truevineos",
                "user_id": "dummy-reader",
                "email": "dummy-reader@example.com",
                "price_lookup_key": "truevineos_starter_monthly",
                "success_url": "https://truevineos.cloud/clock?billing=success",
                "cancel_url": "https://truevineos.cloud/clock?billing=cancelled",
                "idempotency_key": "truevineos:test",
            }
        )

        self.assertEqual(result["id"], "cs_live_checkout")
        self.assertNotIn("integration_identifier", checkout_sessions.payload["metadata"])
        self.assertNotIn("integration_identifier", checkout_sessions.payload["subscription_data"]["metadata"])
        self.assertRegex(
            checkout_sessions.payload["integration_identifier"],
            re.compile(r"^truevineos_[a-z]{8}$"),
        )
        self.assertEqual(checkout_sessions.payload["mode"], "subscription")
        self.assertEqual(checkout_sessions.payload["line_items"], [{"price": "price_live_starter", "quantity": 1}])


if __name__ == "__main__":
    unittest.main()
