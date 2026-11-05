"""PayPal webhook simulator + synthetic failed transactions.

Payloads follow the official PayPal webhook event schema so the whole app
works today with zero credentials, and swaps to the real sandbox later by
pointing PAYPAL_API_BASE at api-m.sandbox.paypal.com and adding a real
webhook receiver.
"""

from __future__ import annotations

import random
import string
import time
import uuid

SCENARIOS = [
    "insufficient_funds",
    "card_expired",
    "duplicate",
    "declined",
    "fraud",
]

def _mock_id(prefix: str) -> str:
    return prefix + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))


def make_tx(scenario: str | None = None, amount: str = "49.00") -> dict:
    """Build a failed-transaction webhook payload in official PayPal shape."""
    scenario = scenario or random.choice(SCENARIOS)
    now = int(time.time())
    base = {
        "id": _mock_id("WH-"),
        "create_time": f"{now}",
        "resource_type": "capture",
        "event_version": "1.0",
        "event_type": "PAYMENT.CAPTURE.DECLINED",
        "resource": {
            "id": _mock_id("CAP-"),
            "amount": {"currency_code": "USD", "value": amount},
            "final_capture": False,
            "seller_receivable_amount": {"currency_code": "USD", "value": "0.00"},
            "create_time": f"{now}",
            "update_time": f"{now}",
            "status": "DECLINED",
            "status_details": {"reason": ""},
        },
        "links": [],
    }
    res = base["resource"]
    if scenario == "insufficient_funds":
        res["status_details"]["reason"] = "INSUFFICIENT_FUNDS"
    elif scenario == "card_expired":
        res["status_details"]["reason"] = "CARD_EXPIRED"
    elif scenario == "duplicate":
        base["event_type"] = "PAYMENT.CAPTURE.DECLINED"
        res["status_details"]["reason"] = "DUPLICATE_INVOCATION"
        res["idempotency_error"] = True
    elif scenario == "declined":
        res["status_details"]["reason"] = "GENERAL_DECLINE"
    elif scenario == "fraud":
        res["status_details"]["reason"] = "SUSPECTED_FRAUD"
    return base


def make_live_webhook(payload: dict) -> dict:
    """Simulated live webhook envelope (matches PayPal transmission header fields)."""
    return {
        "transmission_id": str(uuid.uuid4()),
        "transmission_time": str(int(time.time())),
        "transmission_sig": "SIMULATED",
        "cert_url": "simulated://cert",
        "auth_algo": "SHA256withRSA",
        "payload": payload,
    }
