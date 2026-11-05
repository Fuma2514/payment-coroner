# Payment Coroner — Build Plan (deadline: Nov 12, 2026)

## Done (Nov 5)
- [x] Pivot from BillBot → Payment Coroner (README/ARCHITECTURE rewritten)
- [x] Autopsy engine (`app/autopsy.py`): rule classifier → LLM enrichment → learning loop
- [x] PayPal webhook simulator (`app/simulator.py`) — official PayPal webhook event schema,
      scenarios: insufficient_funds, card_expired, duplicate, declined, fraud; zero credentials needed
- [x] FastAPI server (`app/main.py`): /simulate, /simulate/burst, /webhooks/paypal,
      /cases, /cases/{id}, /insights, dashboard — all endpoints tested live
- [x] Dashboard (dark morgue table + severity chips + one-click simulate + evolving playbook)
- [x] Public GitHub repo Fuma2514/payment-coroner, MIT license visible, .env.example (no hardcoded creds)

## Next (Nov 6-11)
- [ ] Demo video <3 min (YouTube) — script: problem (15s) → simulate+autopsy live (60s) → learning loop (30s) → sandbox swap path (15s)
- [ ] Devpost submission form (tools used, description, screenshots)
- [ ] Optional: wire real PayPal sandbox when user provides Client ID/Secret (.env ready)
- [ ] Optional: hosted demo URL

## Prize tracks
- Overall podium, "Best Use of PayPal + AI", "Best Use of Agentic Commerce" (autonomous forensic agent on payment events)
