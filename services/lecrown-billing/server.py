#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import stripe


API_VERSION = "2026-07-29.dahlia"
PROJECT = "truevineos"
ALLOWED_LOOKUP_KEYS = {
    "truevineos_starter_monthly": "starter",
    "truevineos_pro_monthly": "pro",
    "truevineos_org_monthly": "org",
}
ACTIVE_SUBSCRIPTION_STATUSES = {"active", "trialing", "past_due", "unpaid", "paused"}
DB_LOCK = threading.Lock()


def _required_env(name: str) -> str:
    value = str(os.environ.get(name, "") or "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _truthy(name: str) -> bool:
    return str(os.environ.get(name, "") or "").strip().lower() in {"1", "true", "yes", "on"}


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _stripe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict_recursive"):
        return value.to_dict_recursive()
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return dict(value or {})


@dataclass(frozen=True)
class Settings:
    stripe_secret_key: str
    stripe_webhook_secret: str
    service_api_key: str
    fulfillment_url: str
    fulfillment_secret: str
    allowed_return_origins: tuple[str, ...]
    db_path: str
    port: int

    @property
    def stripe_mode(self) -> str:
        if self.stripe_secret_key.startswith(("sk_live_", "rk_live_", "rkcs_live_")):
            return "live"
        if self.stripe_secret_key.startswith(("sk_test_", "rk_test_", "rkcs_test_")):
            return "test"
        return "unknown"

    @classmethod
    def from_env(cls) -> "Settings":
        stripe_key = _required_env("STRIPE_SECRET_KEY")
        if not stripe_key.startswith(("sk_test_", "rk_test_", "rkcs_test_")) and not _truthy("BILLING_ALLOW_LIVE"):
            raise RuntimeError("Refusing non-test Stripe key without BILLING_ALLOW_LIVE=true.")
        origins = tuple(
            origin.strip().rstrip("/")
            for origin in str(
                os.environ.get(
                    "BILLING_ALLOWED_RETURN_ORIGINS",
                    "https://truevineos.cloud,http://127.0.0.1:8086,http://localhost:8086",
                )
            ).split(",")
            if origin.strip()
        )
        return cls(
            stripe_secret_key=stripe_key,
            stripe_webhook_secret=_required_env("STRIPE_WEBHOOK_SECRET"),
            service_api_key=_required_env("BILLING_SERVICE_API_KEY"),
            fulfillment_url=_required_env("BILLING_FULFILLMENT_URL"),
            fulfillment_secret=_required_env("BILLING_FULFILLMENT_SECRET"),
            allowed_return_origins=origins,
            db_path=str(os.environ.get("BILLING_DB_PATH", "/var/lib/lecrown-billing/billing.sqlite3")),
            port=int(os.environ.get("PORT", "8090")),
        )


class BillingService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = stripe.StripeClient(settings.stripe_secret_key, stripe_version=API_VERSION, max_network_retries=2)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        directory = os.path.dirname(self.settings.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        connection = sqlite3.connect(self.settings.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with DB_LOCK, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS customer_map (
                    project TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    customer_id TEXT NOT NULL,
                    email TEXT,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (project, user_id),
                    UNIQUE (customer_id)
                );
                CREATE TABLE IF NOT EXISTS webhook_events (
                    event_id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    delivered_at INTEGER NOT NULL
                );
                """
            )

    def _mapped_customer(self, user_id: str) -> str | None:
        with DB_LOCK, self._connect() as connection:
            row = connection.execute(
                "SELECT customer_id FROM customer_map WHERE project = ? AND user_id = ?",
                (PROJECT, user_id),
            ).fetchone()
        return str(row["customer_id"]) if row else None

    def _save_customer(self, user_id: str, customer_id: str, email: str) -> None:
        with DB_LOCK, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO customer_map(project, user_id, customer_id, email, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project, user_id) DO UPDATE SET
                  customer_id = excluded.customer_id,
                  email = excluded.email,
                  updated_at = excluded.updated_at
                """,
                (PROJECT, user_id, customer_id, email, int(time.time())),
            )

    def _event_delivered(self, event_id: str) -> bool:
        with DB_LOCK, self._connect() as connection:
            row = connection.execute("SELECT 1 FROM webhook_events WHERE event_id = ?", (event_id,)).fetchone()
        return bool(row)

    def _mark_event_delivered(self, event_id: str, event_type: str) -> None:
        with DB_LOCK, self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO webhook_events(event_id, event_type, delivered_at) VALUES (?, ?, ?)",
                (event_id, event_type, int(time.time())),
            )

    def _validate_return_url(self, value: Any, field: str) -> str:
        url = str(value or "").strip()
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
        if origin not in self.settings.allowed_return_origins:
            raise ValueError(f"{field} must use an approved return origin.")
        return url

    def _require_identity(self, payload: dict[str, Any]) -> tuple[str, str]:
        if str(payload.get("project") or "").strip() != PROJECT:
            raise ValueError("Unsupported billing project.")
        user_id = str(payload.get("user_id") or "").strip()
        email = str(payload.get("email") or "").strip().lower()
        if not user_id:
            raise ValueError("user_id is required.")
        if not email or "@" not in email:
            raise ValueError("A valid email is required.")
        return user_id, email

    def _get_or_create_customer(self, user_id: str, email: str) -> str:
        mapped = self._mapped_customer(user_id)
        if mapped:
            try:
                customer = self.client.v1.customers.retrieve(mapped)
                if not bool(getattr(customer, "deleted", False)):
                    return mapped
            except stripe.StripeError:
                pass
        customer = self.client.v1.customers.create(
            {
                "email": email,
                "metadata": {"project": PROJECT, "environment": self.settings.stripe_mode, "truevineos_user_id": user_id},
            },
            {"idempotency_key": f"{PROJECT}:customer:{hashlib.sha256(user_id.encode()).hexdigest()}"},
        )
        customer_id = str(customer.id)
        self._save_customer(user_id, customer_id, email)
        return customer_id

    def _price_for_lookup_key(self, lookup_key: str) -> dict[str, Any]:
        if lookup_key not in ALLOWED_LOOKUP_KEYS:
            raise ValueError("Unknown TrueVine plan lookup key.")
        prices = self.client.v1.prices.list(
            {"lookup_keys": [lookup_key], "active": True, "limit": 10, "expand": ["data.product"]}
        )
        candidates = [_stripe_dict(price) for price in prices.data]
        candidates = [price for price in candidates if price.get("recurring")]
        if len(candidates) != 1:
            raise RuntimeError(f"Expected exactly one active recurring Price for {lookup_key}.")
        return candidates[0]

    def catalog(self) -> dict[str, Any]:
        plans = []
        for lookup_key, plan in ALLOWED_LOOKUP_KEYS.items():
            price = self._price_for_lookup_key(lookup_key)
            product = price.get("product") if isinstance(price.get("product"), dict) else {}
            plans.append(
                {
                    "plan": plan,
                    "lookup_key": lookup_key,
                    "currency": price.get("currency"),
                    "unit_amount": price.get("unit_amount"),
                    "interval": (price.get("recurring") or {}).get("interval"),
                    "product_name": product.get("name") or "TrueVine OS",
                }
            )
        return {"project": PROJECT, "environment": self.settings.stripe_mode, "plans": plans}

    def create_checkout(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id, email = self._require_identity(payload)
        lookup_key = str(payload.get("price_lookup_key") or "").strip()
        plan = ALLOWED_LOOKUP_KEYS.get(lookup_key)
        price = self._price_for_lookup_key(lookup_key)
        success_url = self._validate_return_url(payload.get("success_url"), "success_url")
        cancel_url = self._validate_return_url(payload.get("cancel_url"), "cancel_url")
        customer_id = self._get_or_create_customer(user_id, email)
        subscriptions = self.client.v1.subscriptions.list({"customer": customer_id, "status": "all", "limit": 100})
        existing = next((sub for sub in subscriptions.data if str(getattr(sub, "status", "")) in ACTIVE_SUBSCRIPTION_STATUSES), None)
        if existing is not None:
            raise FileExistsError("This account already has a subscription; use Manage billing.")
        metadata = {
            "project": PROJECT,
            "environment": self.settings.stripe_mode,
            "plan": plan,
            "user_id": user_id,
            "price_lookup_key": lookup_key,
            "integration_identifier": "truevineos",
        }
        session = self.client.v1.checkout.sessions.create(
            {
                "mode": "subscription",
                "customer": customer_id,
                "client_reference_id": user_id,
                "line_items": [{"price": price["id"], "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata,
                "subscription_data": {"metadata": metadata},
            },
            {"idempotency_key": str(payload.get("idempotency_key") or "") or None},
        )
        return {"id": session.id, "url": session.url, "livemode": bool(session.livemode)}

    def create_portal(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id, _email = self._require_identity(payload)
        return_url = self._validate_return_url(payload.get("return_url"), "return_url")
        customer_id = self._mapped_customer(user_id)
        if not customer_id:
            raise LookupError("No Stripe customer exists for this account.")
        session = self.client.v1.billing_portal.sessions.create({"customer": customer_id, "return_url": return_url})
        return {"id": session.id, "url": session.url, "livemode": bool(session.livemode)}

    def list_invoices(self, payload: dict[str, Any]) -> dict[str, Any]:
        user_id, _email = self._require_identity(payload)
        customer_id = self._mapped_customer(user_id)
        if not customer_id:
            return {"data": [], "has_more": False}
        invoices = self.client.v1.invoices.list({"customer": customer_id, "limit": 25})
        return {
            "data": [
                {
                    "id": invoice.id,
                    "status": invoice.status,
                    "currency": invoice.currency,
                    "amount_due": invoice.amount_due,
                    "amount_paid": invoice.amount_paid,
                    "hosted_invoice_url": invoice.hosted_invoice_url,
                    "invoice_pdf": invoice.invoice_pdf,
                    "created": invoice.created,
                }
                for invoice in invoices.data
            ],
            "has_more": bool(invoices.has_more),
        }

    def _subscription_payload(self, subscription: Any) -> dict[str, Any]:
        sub = _stripe_dict(subscription)
        metadata = sub.get("metadata") or {}
        customer_id = str(sub.get("customer") or "")
        user_id = str(metadata.get("user_id") or "")
        if not user_id and customer_id:
            with DB_LOCK, self._connect() as connection:
                row = connection.execute("SELECT user_id FROM customer_map WHERE customer_id = ?", (customer_id,)).fetchone()
            user_id = str(row["user_id"]) if row else ""
        lookup_key = str(metadata.get("price_lookup_key") or "")
        plan = str(metadata.get("plan") or "")
        items = ((sub.get("items") or {}).get("data") or [])
        if items:
            price = items[0].get("price") or {}
            lookup_key = lookup_key or str(price.get("lookup_key") or "")
            plan = plan or str((price.get("metadata") or {}).get("plan") or "")
        return {
            "project": PROJECT,
            "user_id": user_id,
            "customer_id": customer_id,
            "subscription_id": str(sub.get("id") or ""),
            "status": str(sub.get("status") or ""),
            "plan": plan or ALLOWED_LOOKUP_KEYS.get(lookup_key),
            "price_lookup_key": lookup_key,
            "cancel_at_period_end": bool(sub.get("cancel_at_period_end")),
            "current_period_end": sub.get("current_period_end"),
        }

    def _normalize_event(self, event: Any) -> dict[str, Any] | None:
        event_dict = _stripe_dict(event)
        event_type = str(event_dict.get("type") or "")
        obj = ((event_dict.get("data") or {}).get("object") or {})
        normalized: dict[str, Any] | None = None
        if event_type.startswith("customer.subscription."):
            normalized = self._subscription_payload(obj)
        elif event_type == "checkout.session.completed":
            subscription_id = str(obj.get("subscription") or "")
            if subscription_id:
                normalized = self._subscription_payload(
                    self.client.v1.subscriptions.retrieve(subscription_id, {"expand": ["items.data.price"]})
                )
        elif event_type.startswith("invoice."):
            subscription_id = str(((obj.get("parent") or {}).get("subscription_details") or {}).get("subscription") or obj.get("subscription") or "")
            if subscription_id:
                normalized = self._subscription_payload(
                    self.client.v1.subscriptions.retrieve(subscription_id, {"expand": ["items.data.price"]})
                )
        if normalized is None:
            return None
        normalized.update({"event_id": event_dict.get("id"), "event_type": event_type})
        return normalized

    def _deliver_fulfillment(self, payload: dict[str, Any]) -> None:
        if not payload.get("user_id"):
            raise RuntimeError("Refusing fulfillment event without a user_id.")
        body = _json_bytes(payload)
        timestamp = str(int(time.time()))
        signature = hmac.new(
            self.settings.fulfillment_secret.encode("utf-8"),
            timestamp.encode("ascii") + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        request = Request(
            self.settings.fulfillment_url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json", "X-Billing-Signature": f"t={timestamp},v1={signature}"},
        )
        with urlopen(request, timeout=10) as response:
            if not 200 <= response.status < 300:
                raise RuntimeError(f"Fulfillment endpoint returned HTTP {response.status}.")

    def handle_webhook(self, raw_body: bytes, signature: str) -> dict[str, Any]:
        event = stripe.Webhook.construct_event(raw_body, signature, self.settings.stripe_webhook_secret)
        event_id = str(event.id)
        event_type = str(event.type)
        if self._event_delivered(event_id):
            return {"received": True, "duplicate": True}
        normalized = self._normalize_event(event)
        if normalized is not None:
            self._deliver_fulfillment(normalized)
        self._mark_event_delivered(event_id, event_type)
        return {"received": True, "delivered": normalized is not None}


class BillingRequestHandler(BaseHTTPRequestHandler):
    server_version = "LeCrownBilling/1.0"

    @property
    def service(self) -> BillingService:
        return self.server.billing_service  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"billing-service {self.address_string()} {format % args}")

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = _json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 0 or length > 1_000_000:
            raise ValueError("Invalid request body length.")
        return self.rfile.read(length)

    def _authorized(self) -> bool:
        supplied = str(self.headers.get("Authorization", "") or "")
        return hmac.compare_digest(supplied, f"Bearer {self.service.settings.service_api_key}")

    def _payload(self) -> dict[str, Any]:
        payload = json.loads(self._read_body().decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object.")
        return payload

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in {"/health", "/v1/health"}:
            self._send_json({"status": "ok", "service": "lecrown-billing", "stripe_mode": self.service.settings.stripe_mode})
            return
        if not self._authorized():
            self._send_json({"error": "Unauthorized."}, HTTPStatus.UNAUTHORIZED)
            return
        try:
            if path == "/v1/catalog":
                self._send_json(self.service.catalog())
            else:
                self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
        except (ValueError, RuntimeError, stripe.StripeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.SERVICE_UNAVAILABLE)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path == "/v1/stripe/webhook":
                result = self.service.handle_webhook(self._read_body(), str(self.headers.get("Stripe-Signature", "") or ""))
                self._send_json(result)
                return
            if not self._authorized():
                self._send_json({"error": "Unauthorized."}, HTTPStatus.UNAUTHORIZED)
                return
            payload = self._payload()
            if path == "/v1/checkout/sessions":
                result = self.service.create_checkout(payload)
            elif path == "/v1/customer-portal/sessions":
                result = self.service.create_portal(payload)
            elif path == "/v1/invoices":
                result = self.service.list_invoices(payload)
            else:
                self._send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(result, HTTPStatus.CREATED if path.endswith("/sessions") else HTTPStatus.OK)
        except FileExistsError as exc:
            self._send_json({"error": str(exc), "code": "subscription_exists"}, HTTPStatus.CONFLICT)
        except LookupError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            self._send_json({"error": "Invalid Stripe webhook signature."}, HTTPStatus.BAD_REQUEST)
        except (RuntimeError, stripe.StripeError, OSError) as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_GATEWAY)


def main() -> None:
    service = BillingService(Settings.from_env())
    server = ThreadingHTTPServer(("0.0.0.0", service.settings.port), BillingRequestHandler)
    server.billing_service = service  # type: ignore[attr-defined]
    print(f"LeCrown billing service listening on :{service.settings.port} (Stripe test mode)")
    server.serve_forever()


if __name__ == "__main__":
    main()
