# 💀 Payment Coroner — AI autopsies for failed PayPal transactions

**PayPal AI Hackathon submission (deadline: Nov 12, 2026)** — "Build What's Next with PayPal and AI"

## The problem
Failed payments are a black hole. A card gets declined, a charge duplicates, funds are
insufficient — and the money is just... gone. Merchants eat the loss, guess at the cause,
and the same failure happens again next week.

## The solution
**Payment Coroner performs an autopsy on every failed PayPal transaction:**

1. **Interrogates the case** — why did this payment die? Root-cause classification
   (insufficient funds, card expired, duplicate capture, general decline, fraud filter).
2. **Assigns blame** — payer, merchant, issuer, or processor.
3. **Writes the incident report** — severity, autopsy finding, and a concrete
   recovery playbook (retry timing, refund, payer outreach, risk-settings changes).
4. **Learns** — a learning loop aggregates every autopsy into an evolving prevention
   playbook, so recurring failure modes get promoted to standing rules.

## Why judges can run it in 60 seconds
No credentials needed — the repo ships a **PayPal webhook simulator** that produces
synthetic failed transactions in the **official PayPal webhook event schema**
(`PAYMENT.CAPTURE.DECLINED` with `resource.status_details.reason`, capture IDs, amounts):

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# open http://localhost:8000 — click "+ Simulate failed transaction & autopsy"
```

## Going live with the PayPal sandbox
The payloads are schema-identical to real PayPal events. Add your sandbox app
credentials to `.env` (see `.env.example` and `docs/SETUP_PAYPAL.md`) and point real
sandbox webhooks at `POST /webhooks/paypal` — the autopsy engine works unchanged.

## API
| Endpoint | What it does |
|---|---|
| `GET /health` | liveness + case count |
| `POST /simulate?scenario=insufficient_funds` | generate + autopsy one synthetic failure |
| `POST /simulate/burst?n=10` | batch generate + autopsy |
| `POST /webhooks/paypal` | real PayPal webhook receiver (declines get autopsied) |
| `GET /cases` | the morgue — all incident reports |
| `GET /cases/{case_id}` | single autopsy report |
| `GET /insights` | learning-loop stats + evolving prevention playbook |
| `GET /` | dashboard (case table, severity, playbook) |

## AI usage
The autopsy engine is LLM-first when an OpenAI-compatible endpoint is configured
(`LLM_API_BASE` / `LLM_API_KEY` / `LLM_MODEL` in `.env`): the model produces the
autopsy finding, recovery steps and prevention rule. A deterministic rule engine
classifies first and serves as the always-works fallback, so the demo runs with
**zero external dependencies**.

## Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md).

## Stack
- Python 3.11 + FastAPI, httpx (LLM enrichment; no heavy SDK)
- Model-agnostic LLM via any chat-completions endpoint
- Zero-config simulator: official PayPal webhook event schema, no credentials needed

## License
MIT — see [LICENSE](LICENSE).
