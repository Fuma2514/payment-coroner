# PayPal Sandbox Setup — what the human must do

Automated signup was attempted on Nov 5, 2026. The PayPal Developer Program "Join Now" form
(https://developer.paypal.com/community/developer-program/#developerSignupForm-wrapper) requires
personal data and a logged-in PayPal account; an agent cannot and should not create accounts with
fabricated identity data. **The user must do this — it takes ~10 minutes.**

## Steps
1. **PayPal personal account** (if none): https://www.paypal.com/signup — needs name, email,
   phone verification (SMS code → human).
2. **Developer account**: go to https://developer.paypal.com/dashboard — log in with the PayPal
   account (or use the Developer Program "Join Now" form: full name, work email, company, city,
   state, country, developer-type, consent checkbox).
3. **Get sandbox credentials**: Dashboard → Apps & Credentials → toggle "Sandbox" →
   "Create App" (default app also works) → copy **Client ID** and **Client Secret**.
4. **Test accounts**: Dashboard → Sandbox → Accounts — a Business (merchant) and Personal
   (buyer) test account exist by default.
5. **Webhook** (later, once app runs): Dashboard → Sandbox → Webhooks → add
   `https://<public-url>/webhooks/paypal`, subscribe to `PAYMENT.CAPTURE.COMPLETED`.
   (For local dev, use the webhook simulator instead of a public URL.)

## Hand the credentials to the agent like this
```bash
cd ~/paypal_hackathon
cp .env.example .env
# paste Client ID + Secret into .env, or set:
export PAYPAL_CLIENT_ID=...
export PAYPAL_CLIENT_SECRET=...
```
(Secrets should go through the user's password vault / direct env, never pasted into chat.)

## Cost
Free. Sandbox requires no bank/card, no business verification. Live mode is NOT needed for
this hackathon (rules explicitly say free sandbox is fine).
