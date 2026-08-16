# Moliya Agent — web API contract

Status: **implemented unless a section explicitly says proposed**. The web UI
uses secure session cookies and real backend data; it contains no mock layer.

Browser clients use the session cookie endpoints documented below. The
`X-Moliya-Token` header remains reserved for trusted server-to-server calls and
is never embedded in frontend code.

---

## GET /v1/drafts

List drafts, most recent first.

**Query params**
| param | type | notes |
|---|---|---|
| `status` | `pending \| confirmed \| rejected` | optional, defaults to all |
| `actor_id` | string | optional filter |
| `cursor` | string | opaque pagination cursor |
| `limit` | int | default 20, max 100 |

**Response 200**
```json
{ "items": [ /* DraftRecord, same shape as POST /v1/drafts response.draft */ ], "next_cursor": "string|null", "total": 42 }
```

**Auth**: any authenticated role (owner, manager, accountant).
**Empty**: `{ "items": [], "next_cursor": null, "total": 0 }` — UI shows "no drafts pending".
**Loading/Error**: standard spinner / retry banner.

## GET /v1/drafts/{draft_id}

Single draft by id, same `DraftRecord` shape. `404` if not found (existing `DraftNotFoundError` handler already returns this shape from the confirm/reject routes, so reuse it here).

## GET /v1/transactions

List confirmed ledger entries (post-confirm rows in `Operatsiyalar`).

**Query params**: `date_from`, `date_to` (YYYY-MM-DD), `type` (EntryKind), `status`, `payment_method`, `category`, `counterparty` (substring match), `cursor`, `limit`.

**Response 200**
```json
{ "items": [ /* TransactionEntry, see src/lib/types.ts */ ], "next_cursor": "string|null", "total": 128 }
```

**Auth**: owner, manager, accountant (read-only for all three until roles are finalized per `01-talablarni-tasdiqlash.md` \u00a73.1).
**Pagination**: cursor-based, since the ledger is append-only and will outgrow offset pagination quickly.

## GET /v1/transactions/{entry_id}

Single `TransactionEntry`. `404` if not found.

## GET /v1/audit-events

**Query params**: `draft_id`, `entry_id`, `actor_id`, `event_type`, `date_from`, `date_to`, `cursor`, `limit`.

**Response 200**
```json
{ "items": [ /* AuditEvent */ ], "next_cursor": "string|null", "total": 300 }
```

**Auth**: owner only, until roles are defined \u2014 audit trail access is the most sensitive read in the product.

## GET /v1/reports/dashboard

**Query params**: `actor_id`, `month` (YYYY-MM).

**Response 200**: `DashboardSummary` (see `src/lib/types.ts`) \u2014 aggregates that today have to be computed client-side from `/v1/transactions`, or precomputed server-side for performance once the ledger grows. Recommend server-side aggregation from the start; a month can have hundreds of entries and the dashboard should not require fetching all of them into the browser.

**Empty**: all-zero summary with `pending_draft_count: 0` \u2014 UI still renders normal empty-state charts, not an error.

## GET /v1/categories

**Response 200**
```json
{ "items": [ { "id": "c1", "name_uz": "Ijara", "name_ru": "\u0410\u0440\u0435\u043d\u0434\u0430", "name_en": "Rent", "is_custom": false } ] }
```

Seeded from the confirmed list in `01-talablarni-tasdiqlash.md` \u00a73.7 (Ijara,
Oylik, Kommunal, Soliq, Marketing, Yetkazib berish, Boshqa). Custom categories
support `POST`, `PUT` and `DELETE`; built-in categories cannot be changed or deleted.

## GET /v1/users

**Response 200**: `{ "items": [ { "id", "full_name", "role", "telegram_linked" } ] }`.

Team members support `POST`, `PUT` and `DELETE`. The backend always preserves
at least one owner.

**Auth**: owner only. Roles (`owner | manager | accountant`) are a frontend-proposed default, not yet confirmed by the business \u2014 see open question in \u00a73.1 of the requirements doc.

## POST /v1/transactions/{entry_id}/reversal

Creates a reversal entry for a confirmed transaction, per the product's core principle: **confirmed errors are corrected through reversal, never silent editing**.

**Request**
```json
{ "actor_id": "string", "reason": "string" }
```

**Response 201**
```json
{ "original_entry": { /* TransactionEntry, now carrying reversed_entry_id */ }, "reversal_entry": { /* TransactionEntry, carrying reversal_of_entry_id */ } }
```

**Rules the backend must enforce** (not just the frontend):
- An entry that already has a `reversed_entry_id` cannot be reversed again \u2014 return `409`.
- The reversal amount is the exact negation of the original; the frontend never computes or sends an amount.
- This action must appear in `/v1/audit-events` as `reversal_created`.

**Auth**: owner and accountant only (proposed \u2014 not confirmed).

---

## Authentication

The existing backend authenticates server-to-server calls (Hermes \u2192 backend)
with a static `X-Moliya-Token` header (see `config.Settings.internal_token`
usage in `api.py`). That token is a shared secret and **must never be sent
from a browser**.

The FastAPI backend implements browser authentication directly:

1. `POST /v1/session` validates the configured web credentials and returns a
   signed, short-lived `HttpOnly`, `Secure`, `SameSite=Strict` cookie.
2. `GET /v1/session` restores the current browser session and
   `DELETE /v1/session` logs out.
3. `src/lib/apiClient.ts` sends `credentials: 'include'` on every request.
4. `MOLIYA_INTERNAL_TOKEN` remains server-side and is only accepted for
   trusted service calls such as Hermes.
