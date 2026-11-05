# Payment Coroner — Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  Payment Coroner (FastAPI)                   │
│                                                              │
│  ┌──────────────────┐        ┌────────────────────────────┐  │
│  │ Dashboard (/)    │        │ API                        │  │
│  │ morgue table +   │◀──────▶│ /simulate                  │  │
│  │ evolving playbook│        │ /cases, /cases/{id}        │  │
│  └──────────────────┘        │ /insights                  │  │
│                              │ /webhooks/paypal           │  │
│                              └───────┬────────────────────┘  │
│                                      │                       │
│                       ┌──────────────┴───────────────┐       │
│                       │       Autopsy Engine         │       │
│                       │  1. rule-based classifier    │       │
│                       │     (INSUFFICIENT_FUNDS,     │       │
│                       │      CARD_EXPIRED, DUPLICATE,│       │
│                       │      GENERAL_DECLINE, ...)   │       │
│                       │  2. LLM enrichment (optional,│       │
│                       │     OpenAI-compatible)       │       │
│                       │  3. root cause → blame →     │       │
│                       │     recovery playbook        │       │
│                       │  4. learning loop: case      │       │
│                       │     stats → evolving rules   │       │
│                       └──────────────┬───────────────┘       │
└──────────────────────────────────────┼───────────────────────┘
                                       │
                     ┌─────────────────┴─────────────────┐
                     │  Webhook source (either)          │
                     │  • app/simulator.py — synthetic   │
                     │    failures, official PayPal      │
                     │    webhook event schema           │
                     │  • Real PayPal sandbox webhooks   │
                     │    (swap by adding credentials +  │
                     │    pointing PAYPAL_API_BASE)      │
                     └───────────────────────────────────┘
```

## Components

### 1. Autopsy Engine (`app/autopsy.py`)
- **Rule classifier**: deterministic first pass on the webhook payload's
  `status_details.reason` — maps to root cause + blame + recovery playbook + severity.
- **LLM enrichment**: if `LLM_API_BASE` is set (any OpenAI-compatible endpoint),
  the case is re-analyzed by the LLM for a summary, specific recovery steps and a
  one-line prevention rule. Falls back to rules on any error.
- **Learning loop** (`learning_loop()`): aggregates all autopsies → root-cause
  distribution, blame distribution, and the top-prevention rules ranked by how
  often their cause recurs (the playbook literally learns from the morgue).

### 2. PayPal Webhook Simulator (`app/simulator.py`)
- Generates failed-transaction events in the **official PayPal webhook schema**
  (`PAYMENT.CAPTURE.DECLINED`, `resource.status_details.reason`, capture IDs, amounts).
- Scenarios: `insufficient_funds`, `card_expired`, `duplicate`,
  `declined` (general), `fraud`.
- Because payloads are schema-identical to real PayPal events, moving to the
  developer sandbox is a credentials swap, not a rewrite.

### 3. Server (`app/main.py`)
- `POST /webhooks/paypal` — real webhook receiver; declined events are autopsied.
- `POST /simulate[?scenario=...]`, `POST /simulate/burst?n=10` — demo data.
- `GET /cases`, `GET /cases/{id}` — the morgue: full incident reports.
- `GET /insights` — learning-loop stats + evolving prevention playbook.
- `GET /` — dark dashboard: case table, severity chips, one-click simulate, playbook panel.
- Cases persisted to `data/cases.json` (survives restarts; last 500 kept).

## Data flow
1. A failed payment arrives — via the simulator or a real PayPal webhook.
2. Autopsy engine classifies root cause (rules → LLM if available).
3. Incident report stored: cause, blame, severity, recovery playbook.
4. Learning loop re-aggregates; recurring causes climb the prevention playbook.

## Security notes
- Credentials only in `.env`, never committed. `.env.example` documents required keys.
- No hardcoded secrets anywhere; simulator needs none at all.
- Sandbox keys only — no live-mode secrets in the repo.
