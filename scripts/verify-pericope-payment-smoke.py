#!/usr/bin/env python3
"""Exercise the PericopeAI payment fixture flow end to end over HTTP."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


class SmokeFailure(RuntimeError):
    """Raised when the payment smoke contract fails."""


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "fortress-phronesis-payment-smoke/1.0",
    }
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    if headers:
        request_headers.update(headers)

    request = urllib.request.Request(url, data=body, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise SmokeFailure(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise SmokeFailure(f"{method} {url} failed: {exc!r}") from exc

    try:
        return json.loads(raw)
    except Exception as exc:
        raise SmokeFailure(f"{method} {url} returned invalid JSON: {exc}") from exc


def _build_headers(*, api_key: str, user_id: str, roles: list[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    headers["X-Dev-Auth-Sub"] = user_id
    headers["X-Dev-Auth-Roles"] = ",".join(roles)
    return headers


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the PericopeAI payment fixture smoke.")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:18000/api")
    parser.add_argument("--api-key", default=os.getenv("PERICOPE_API_KEY", "").strip())
    parser.add_argument("--user-id", default="dummy-paid-reader")
    parser.add_argument("--tier", default="reader")
    parser.add_argument("--initial-roles", default="default-roles-pericope")
    parser.add_argument("--promoted-roles", default="reader")
    parser.add_argument("--success-url", default="http://127.0.0.1:13080/billing/success")
    parser.add_argument("--cancel-url", default="http://127.0.0.1:13080/pricing")
    parser.add_argument("--return-url", default="http://127.0.0.1:13080/user/profile/home")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    initial_headers = _build_headers(
        api_key=args.api_key,
        user_id=args.user_id,
        roles=_csv_list(args.initial_roles),
    )
    promoted_headers = _build_headers(
        api_key=args.api_key,
        user_id=args.user_id,
        roles=_csv_list(args.promoted_roles),
    )

    try:
        dummy_account = _request_json(
            _api_url(args.api_base_url, "/v1/billing/test/dummy-account"),
            headers=initial_headers,
            timeout=args.timeout,
        )
        _assert(dummy_account.get("user_id"), "dummy account response is missing user_id")

        checkout = _request_json(
            _api_url(args.api_base_url, "/v1/billing/checkout/session"),
            method="POST",
            payload={
                "tier": args.tier,
                "success_url": args.success_url,
                "cancel_url": args.cancel_url,
            },
            headers=initial_headers,
            timeout=args.timeout,
        )
        _assert(checkout.get("provider") == "fixture", "checkout provider is not fixture")
        _assert(checkout.get("session_id"), "checkout session_id is missing")
        _assert(checkout.get("subscription_tier") == args.tier, "checkout tier mismatch")

        pending_status = _request_json(
            _api_url(args.api_base_url, "/v1/billing/status"),
            headers=initial_headers,
            timeout=args.timeout,
        )
        _assert(
            pending_status.get("subscription_status") == "checkout_created",
            f"expected checkout_created status, got {pending_status.get('subscription_status')!r}",
        )
        _assert(
            pending_status.get("access_state") == "checkout_pending",
            f"expected checkout_pending access_state, got {pending_status.get('access_state')!r}",
        )

        completed = _request_json(
            _api_url(args.api_base_url, "/v1/billing/test/complete-checkout"),
            method="POST",
            payload={"session_id": checkout.get("session_id")},
            headers=initial_headers,
            timeout=args.timeout,
        )
        _assert(
            completed.get("subscription_status") == "active",
            f"expected active completion status, got {completed.get('subscription_status')!r}",
        )

        post_payment_status = _request_json(
            _api_url(args.api_base_url, "/v1/billing/status"),
            headers=initial_headers,
            timeout=args.timeout,
        )
        _assert(post_payment_status.get("has_active_subscription") is True, "subscription did not become active")
        _assert(
            post_payment_status.get("access_state") == "awaiting_role_sync",
            f"expected awaiting_role_sync, got {post_payment_status.get('access_state')!r}",
        )

        paid_status = _request_json(
            _api_url(args.api_base_url, "/v1/billing/status"),
            headers=promoted_headers,
            timeout=args.timeout,
        )
        _assert(paid_status.get("has_paid_access") is True, "promoted role did not unlock paid access")
        _assert(
            paid_status.get("access_state") == "paid_active",
            f"expected paid_active, got {paid_status.get('access_state')!r}",
        )

        portal = _request_json(
            _api_url(args.api_base_url, "/v1/billing/customer-portal/session"),
            method="POST",
            payload={"return_url": args.return_url},
            headers=promoted_headers,
            timeout=args.timeout,
        )
        _assert(portal.get("portal_url"), "customer portal URL is missing")

        summary = {
            "dummy_account": {
                "user_id": dummy_account.get("user_id"),
                "email": dummy_account.get("email"),
            },
            "checkout": {
                "session_id": checkout.get("session_id"),
                "customer_id": checkout.get("customer_id"),
                "subscription_tier": checkout.get("subscription_tier"),
            },
            "pending_status": {
                "subscription_status": pending_status.get("subscription_status"),
                "access_state": pending_status.get("access_state"),
            },
            "post_payment_status": {
                "subscription_status": post_payment_status.get("subscription_status"),
                "access_state": post_payment_status.get("access_state"),
            },
            "paid_status": {
                "subscription_status": paid_status.get("subscription_status"),
                "access_state": paid_status.get("access_state"),
                "has_paid_access": paid_status.get("has_paid_access"),
            },
            "portal": {
                "session_id": portal.get("session_id"),
                "customer_id": portal.get("customer_id"),
            },
        }
        print(json.dumps(summary, indent=2))
        return 0
    except SmokeFailure as exc:
        print(f"PAYMENT SMOKE FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
