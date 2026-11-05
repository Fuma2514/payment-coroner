# BillBot — Build Plan (deadline: Nov 12, 2026; today: Nov 5-6)

## Phase 0 — done (Nov 5)
- [x] Read Devpost rules/resources ($67,500 pool; sandbox OK; needs public repo + <3min video + runnable demo)
- [x] Idea locked: AI accounts-receivable agent (BillBot)
- [x] Scaffold: README, ARCHITECTURE.md, LICENSE (MIT), .env.example, FastAPI stub (runs, /health OK)

## Phase 1 — BLOCKED on human (do today)
- [ ] User: PayPal developer account signup (see docs/SETUP_PAYPAL.md, ~10 min, needs phone verification)
- [ ] User: create sandbox app → Client ID + Secret into .env

## Phase 2 — PayPal integration (1-2 days once creds exist)
- [ ] app/paypal/client.py: OAuth token cache, create_order, capture_order
- [ ] Webhook verify + PAYMENT.CAPTURE.COMPLETED handler
- [ ] Test against sandbox with default test accounts (buyer pays, merchant receives)

## Phase 3 — Agent brain (2 days)
- [ ] ReminderEngine: tone ladder prompt (friendly → firm → final notice), invoice-facts context
- [ ] Reply parser: promise_to_pay / question / dispute / payment_made
- [ ] Agent tools: get_invoice, create_payment_link, send_reminder, record_note
- [ ] Chat endpoint (human-in-the-loop approval before first send)

## Phase 4 — Dashboard (1 day)
- [ ] AG Grid invoice/payment grid with live status (bonus AG Grid track prize)
- [ ] CSV invoice import

## Phase 5 — Submission (Nov 9-11, buffer Nov 12)
- [ ] Public GitHub repo (license visible at top per rules)
- [ ] Hosted demo URL (Render credits track possible) OR complete run instructions
- [ ] Demo video <3 min on YouTube
- [ ] Devpost submission form (tools used, description)

## Prize tracks targeted
- Overall podium ($12k/$8k/$5k), "Best Use of Agentic Commerce" ($5k), "Best Use of PayPal + AI" ($5k), AG Grid track.
