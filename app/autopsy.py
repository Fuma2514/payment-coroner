"""Payment Coroner — autopsy engine for failed PayPal transactions.

Per failed transaction:
  1. classify root cause
  2. assign blame (who's responsible)
  3. produce a recovery playbook
  4. feed the learning loop (playbooks improve as more cases arrive)
"""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Rule-based classifier (always runs; LLM enriches when configured)
# ---------------------------------------------------------------------------

ROOT_CAUSES = {
    "INSUFFICIENT_FUNDS": {
        "blame": "payer",
        "recovery": [
            "Retry capture in 3 days (payday) with a smaller amount split offer",
            "Send payment link with installment option",
            "Enable PayPal Pay Later messaging on checkout",
        ],
        "severity": "medium",
    },
    "CARD_EXPIRED": {
        "blame": "payer",
        "recovery": [
            "Notify payer their card expired; prompt to update funding source",
            "Retry with vaulted payment method once updated",
            "Offer PayPal wallet as fallback funding source",
        ],
        "severity": "low",
    },
    "DUPLICATE": {
        "blame": "merchant",
        "recovery": [
            "Auto-refund the duplicate capture immediately",
            "Add idempotency key to order creation to prevent recurrence",
            "Alert merchant that duplicate checkout requests are not deduped",
        ],
        "severity": "high",
    },
    "GENERAL_DECLINE": {
        "blame": "issuer",
        "recovery": [
            "Retry once after 24h (many declines are transient issuer flags)",
            "Prompt payer to try a different funding source",
            "Check fraud-filter false-positive rate for this payer segment",
        ],
        "severity": "medium",
    },
    "INSTRUMENT_DECLINED": {
        "blame": "payer",
        "recovery": [
            "Ask payer to add another card or PayPal balance",
            "Do not hard-retry same instrument more than once",
        ],
        "severity": "medium",
    },
    "FRAUD_FILTER": {
        "blame": "merchant",
        "recovery": [
            "Review risk settings for this payer/geo segment",
            "Allowlist repeat customer if legitimate",
            "Contact payer to confirm transaction",
        ],
        "severity": "high",
    },
    "UNKNOWN": {
        "blame": "unknown",
        "recovery": [
            "Escalate to PayPal merchant support with case ID",
            "Log raw response for pattern matching",
        ],
        "severity": "low",
    },
}


def classify(payload: dict[str, Any]) -> dict[str, Any]:
    """Classify a synthetic/real failed-transaction payload.

    Payload shape mirrors official PayPal webhook events:
    PAYMENT.CAPTURE.DECLINED / CHECKOUT.ORDER.APPROVAL_DENIED etc.
    """
    event = payload.get("event_type", "")
    resource = payload.get("resource", {}) or {}
    details = resource.get("status_details", {}) or {}
    reason = (details.get("reason") or "").upper()
    raw = (resource.get("reason_code") or "").upper()

    cause = "UNKNOWN"
    if "INSUFFICIENT" in reason or "NSF" in reason:
        cause = "INSUFFICIENT_FUNDS"
    elif "EXPIRED" in reason or "CARD_EXPIRED" in raw:
        cause = "CARD_EXPIRED"
    elif "DUPLICATE" in reason or "DUPLICATE_INVOCATION" in reason:
        cause = "DUPLICATE"
    elif "INSTRUMENT" in reason:
        cause = "INSTRUMENT_DECLINED"
    elif "FRAUD" in reason or "RISK" in reason or "SUSPECTED" in reason:
        cause = "FRAUD_FILTER"
    elif reason:
        cause = "GENERAL_DECLINE"

    meta = ROOT_CAUSES[cause]
    return {
        "event_type": event,
        "root_cause": cause,
        "blame": meta["blame"],
        "recovery_playbook": meta["recovery"],
        "severity": meta["severity"],
        "reason_detail": reason or "no reason provided",
        "method": "rules",
    }


# ---------------------------------------------------------------------------
# LLM enrichment (optional; works with any OpenAI-compatible endpoint)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Payment Coroner: a forensic analyst for failed payments.
Given a failed PayPal transaction (JSON), respond with ONLY a JSON object:
{
  "root_cause": one of INSUFFICIENT_FUNDS, CARD_EXPIRED, DUPLICATE,
                GENERAL_DECLINE, INSTRUMENT_DECLINED, FRAUD_FILTER, UNKNOWN,
  "blame": "payer" | "merchant" | "issuer" | "processor" | "unknown",
  "severity": "low" | "medium" | "high",
  "summary": one-sentence autopsy finding,
  "recovery_playbook": ["step 1", "step 2", "step 3"],
  "prevention": one-sentence prevention rule for the playbook library
}
Be specific and practical. No prose outside the JSON."""


async def llm_enrich(payload: dict[str, Any], rule_result: dict[str, Any]) -> dict[str, Any] | None:
    api_base = os.getenv("LLM_API_BASE", "").rstrip("/")
    if not api_base:
        return None
    url = f"{api_base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    key = os.getenv("LLM_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    body = {
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Failed transaction:\n{payload}\n\nRule-based guess:\n{rule_result}",
            },
        ],
        "temperature": 0.2,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=body, headers=headers)
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"]
    except Exception:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        import json

        out = json.loads(m.group(0))
    except Exception:
        return None
    out["method"] = "llm"
    return out


# ---------------------------------------------------------------------------
# Learning loop: pattern stats across all autopsies
# ---------------------------------------------------------------------------


def learning_loop(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate stats across autopsied cases to produce an evolving playbook."""
    causes = Counter(c.get("root_cause", "UNKNOWN") for c in cases)
    blames = Counter(c.get("blame", "unknown") for c in cases)
    total = len(cases)
    top_prevention = {}
    for c in cases:
        p = c.get("prevention") or (c.get("recovery_playbook") or [""])[0]
        if p:
            top_prevention.setdefault((c.get("root_cause"), p), 0)
            top_prevention[(c.get("root_cause"), p)] += 1
    best = sorted(top_prevention.items(), key=lambda kv: -kv[1])[:5]
    return {
        "total_autopsies": total,
        "root_causes": dict(causes.most_common()),
        "blame_distribution": dict(blames.most_common()),
        "evolving_playbook": [
            {"root_cause": k, "rule": v, "seen_n": n} for (k, v), n in best
        ],
    }
