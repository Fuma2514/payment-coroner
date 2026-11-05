"""Payment Coroner — FastAPI server.

Endpoints:
  GET  /health
  POST /webhooks/paypal        # real PayPal webhook receiver (works with sandbox later)
  POST /simulate               # generate + autopsy one synthetic failure
  GET  /cases                  # morgue: list of autopsied cases
  GET  /cases/{case_id}        # single autopsy report
  GET  /insights               # learning-loop playbook stats
  GET  /                       # dashboard
"""

from __future__ import annotations

import json
import os
import uuid
from collections import OrderedDict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from .autopsy import classify, llm_enrich, learning_loop
from .simulator import make_tx

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "cases.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

app = FastAPI(title="Payment Coroner", version="1.0.0")

CASES: "OrderedDict[str, dict]" = OrderedDict()


def _load() -> None:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                for c in json.load(f):
                    CASES[c["case_id"]] = c
        except Exception:
            pass


def _save() -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(list(CASES.values())[-500:], f, indent=1)


_load()


async def _autopsy(payload: dict) -> dict:
    rule = classify(payload)
    enriched = await llm_enrich(payload, rule)
    result = enriched or rule
    case = {
        "case_id": f"PC-{uuid.uuid4().hex[:8].upper()}",
        "payload": payload,
        "result": result,
    }
    CASES[case["case_id"]] = case
    _save()
    return case


@app.get("/health")
async def health():
    return {"status": "ok", "service": "payment-coroner", "cases": len(CASES)}


@app.post("/webhooks/paypal")
async def paypal_webhook(request: Request):
    body = await request.json()
    # If the resource is a failure, autopsy it; otherwise just ack.
    if "DECLINED" in (body.get("event_type") or "") or body.get("resource", {}).get("status") == "DECLINED":
        case = await _autopsy(body)
        return {"received": True, "autopsied": True, "case_id": case["case_id"], "report": case["result"]}
    return {"received": True, "autopsied": False}


@app.post("/simulate")
async def simulate(scenario: str | None = None, amount: str = "49.00"):
    payload = make_tx(scenario, amount)
    case = await _autopsy(payload)
    return case


@app.post("/simulate/burst")
async def simulate_burst(n: int = 10):
    results = []
    for _ in range(min(n, 50)):
        results.append(await simulate())
    return {"created": len(results), "case_ids": [r["case_id"] for r in results]}


@app.get("/cases")
async def list_cases():
    return {"count": len(CASES), "cases": list(CASES.values())[::-1]}


@app.get("/cases/{case_id}")
async def get_case(case_id: str):
    if case_id not in CASES:
        raise HTTPException(404, "case not found")
    return CASES[case_id]


@app.get("/insights")
async def insights():
    cases = [c["result"] for c in CASES.values()]
    return learning_loop(cases)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    cases = list(CASES.values())[::-1]
    rows = ""
    for c in cases[:100]:
        r = c["result"]
        rows += f"""<tr onclick="location='/cases/{c['case_id']}'" style="cursor:pointer">
        <td><code>{c['case_id']}</code></td>
        <td>{r.get('root_cause','?')}</td>
        <td>{r.get('blame','?')}</td>
        <td><span class="sev {r.get('severity','low')}">{r.get('severity','?')}</span></td>
        <td>{r.get('summary', r.get('reason_detail',''))}</td>
        </tr>"""
    ins = learning_loop([c["result"] for c in CASES.values()])
    play = "".join(
        f"<li><b>{p['root_cause']}</b>: {p['rule']} <small>(seen {p['seen_n']}x)</small></li>"
        for p in ins["evolving_playbook"]
    ) or "<li>No cases yet — click the button to fill the morgue.</li>"
    causes = "".join(f"<span class='chip'>{k}: {v}</span>" for k, v in ins["root_causes"].items())
    return HTMLResponse(f"""<!doctype html><html><head><title>Payment Coroner</title><style>
    body{{font-family:ui-sans-serif,system-ui;background:#0d1117;color:#e6edf3;margin:0;padding:32px}}
    h1{{margin:0 0 4px}} h1 span{{color:#f85149}}
    .sub{{color:#8b949e;margin-bottom:24px}}
    table{{border-collapse:collapse;width:100%;background:#161b22;border-radius:8px;overflow:hidden}}
    th,td{{padding:10px 14px;text-align:left;border-bottom:1px solid #21262d}}
    th{{background:#1c2128;color:#8b949e;font-size:12px;text-transform:uppercase}}
    .sev{{padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600}}
    .high{{background:#f8514933;color:#f85149}} .medium{{background:#d2992233;color:#d29922}} .low{{background:#3fb95033;color:#3fb950}}
    .chip{{background:#21262d;padding:4px 10px;border-radius:999px;margin-right:8px;font-size:13px}}
    ul{{background:#161b22;padding:20px 20px 20px 40px;border-radius:8px}}
    code{{color:#79c0ff}}
    </style></head><body>
    <h1>💀 Payment <span>Coroner</span></h1>
    <div class="sub">Autopsies of failed PayPal transactions — root cause, blame, recovery playbook, learning loop.</div>
    <div style="margin-bottom:16px">{causes or '<span class="chip">no cases yet</span>'}</div>
    <button onclick="fetch('/simulate',{{method:'POST'}}).then(()=>location.reload())"
      style="background:#238636;color:#fff;border:0;padding:10px 18px;border-radius:6px;cursor:pointer;font-size:14px;margin-bottom:20px">
      + Simulate failed transaction &amp; autopsy</button>
    <table><tr><th>Case</th><th>Root cause</th><th>Blame</th><th>Severity</th><th>Finding</th></tr>{rows}</table>
    <h2 style="margin-top:32px">📚 Evolving prevention playbook</h2>
    <ul>{play}</ul>
    </body></html>""")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
