# Moliya Agent \u2014 web app

A responsive React + TypeScript dashboard that complements the existing
Telegram/Hermes workflow for **Moliya Agent**: review pending drafts,
confirm or reject transactions, browse the ledger, and check monthly
performance.

## What's real vs. mocked

The core financial workflow is connected to the real backend:

| Endpoint | Used by |
|---|---|
| `POST/GET/DELETE /v1/session` | Login and logout |
| `POST /v1/drafts` | Add transaction |
| `POST /v1/drafts/{id}/confirm` | Pending drafts, Add transaction |
| `POST /v1/drafts/{id}/reject` | Pending drafts |
| `GET /v1/drafts` | Pending drafts |
| `GET /v1/transactions` | Transactions |
| `GET /v1/reports/monthly` | Monthly reports |
| `GET /v1/reports/dashboard` | Dashboard |
| `GET /v1/audit-events` | Audit log |
| `GET /health` | Backend, parser and Sheets status |

Business profile, categories and user management still have no backend
endpoint. Only those settings sections use the in-memory mock layer and show
a visible sample-data notice.

## Setup

```bash
npm install
cp .env.example .env
# `/api` is proxied to http://127.0.0.1:8088 by Vite in local development
npm run dev
```

Requires Node 18+. Uses only `react` and `react-dom` as runtime
dependencies \u2014 routing, charts, and the mock API are hand-rolled in
`src/router.tsx`, `src/components/charts/`, and `src/lib/mock/` to keep the
project light and easy to audit.

```bash
npm run typecheck   # tsc -b --noEmit
npm run build        # production build to dist/
npm run preview      # serve the production build locally
```

## Authentication

Login uses the backend's HttpOnly cookie session. Credentials come from
`MOLIYA_WEB_USERNAME` and `MOLIYA_WEB_PASSWORD` in the backend `.env` file.
The internal `X-Moliya-Token` remains server-only and is never exposed to the
browser.

## Project structure

```
src/
  components/
    layout/     AppShell, Sidebar, TopBar, MobileNav
    ui/         Button, Card, Badge, ConfirmDialog, States, MockNotice, CurrencyAmount
    charts/     hand-rolled SVG bar charts (no charting library dependency)
  i18n/         uz / ru / en dictionaries + provider (uz is the source of truth)
  lib/
    types.ts      domain types mirrored from domain.py
    apiClient.ts  typed client for the 4 real endpoints
    mock/         mock data for settings sections without backend endpoints
    authContext.tsx  real cookie-session integration
    format.ts     centralized currency/date formatting
  pages/        one file per required screen
  router.tsx    minimal history-API router (no external routing library)
```

## Design tokens

`src/styles/tokens.css` holds the full color/spacing/type system. Palette:
warm stone background, deep teal-ink primary, green for confirmed/positive,
red only for destructive actions and negative amounts, amber only for
"needs clarification" \u2014 color is never the only signal. See that file's
header comment for the rationale.

## Known gaps / next steps

- Reversal creation (`POST /v1/transactions/{id}/reversal`) has no backend
  implementation yet, even though the UI's data model already accounts for
  it (`reversed_entry_id` / `reversal_of_entry_id` fields)
- USD is mentioned as a confirmed currency in the requirements doc but
  rejected by `domain.py` at the domain layer \u2014 flagged for the business
  owner to resolve, not silently guessed at here (UI is UZS-only for now)
- See `docs/QA_CHECKLIST.md` before any release
