// Domain types mirrored from the backend's domain.py. Keep field names and
// enum values identical to the Python source so the typed API client never
// silently drifts from the real contract.

export type EntryKind =
  | 'income'
  | 'expense'
  | 'refund'
  | 'cost_of_goods'
  | 'receivable'
  | 'payable'
  | 'customer_payment'
  | 'supplier_payment'

export type PaymentMethod = 'cash' | 'card' | 'transfer' | 'mixed' | 'unknown'

export type DraftStatus = 'pending' | 'confirmed' | 'rejected'

export interface PaymentBreakdown {
  cash_uzs: number
  card_uzs: number
  transfer_uzs: number
}

export interface FinancialEntry {
  kind: EntryKind
  amount_uzs: number
  payment_method: PaymentMethod
  payment_breakdown: PaymentBreakdown
  cost_uzs: number
  category: string | null
  counterparty: string | null
  note: string | null
}

export interface ParsedMessage {
  transaction_date: string // YYYY-MM-DD
  currency: string
  entries: FinancialEntry[]
  new_customer_count: number
  needs_clarification: boolean
  clarification_question: string | null
  missing_fields: string[]
  confidence: number
}

export interface DraftRecord {
  id: string
  actor_id: string
  source_id: string
  raw_text: string
  parsed: ParsedMessage
  status: DraftStatus
  created_at: string
  updated_at: string
  confirmed_at: string | null
}

export interface MonthlyReport {
  month: string
  income_uzs: number
  refund_uzs: number
  cost_of_goods_uzs: number
  expense_uzs: number
  gross_profit_uzs: number
  net_profit_uzs: number
  [key: string]: unknown
}

// --- Types for endpoints that do not exist on the backend yet. ---
// These mirror the proposed contract in docs/API_CONTRACT.md and are only
// ever populated by the mock layer (src/lib/mock) until the real endpoints
// ship.

export type UserRole = 'owner' | 'manager' | 'accountant'

export interface AppUser {
  id: string
  full_name: string
  role: UserRole
  telegram_linked: boolean
}

export interface TransactionEntry {
  entry_id: string
  draft_id: string
  transaction_date: string
  kind: EntryKind
  amount_uzs: number
  payment_method: PaymentMethod
  payment_breakdown: PaymentBreakdown
  cost_uzs: number
  category: string | null
  counterparty: string | null
  note: string | null
  source_id: string
  confirmed_by: string
  confirmed_at: string
  reversed_entry_id: string | null
  reversal_of_entry_id: string | null
}

export interface Category {
  id: string
  name_uz: string
  name_ru: string
  name_en: string
  is_custom: boolean
}

export type AuditEventType =
  | 'draft_created'
  | 'draft_confirmed'
  | 'draft_rejected'
  | 'sheet_write_succeeded'
  | 'sheet_write_failed'
  | 'reversal_created'

export interface AuditEvent {
  id: string
  event_type: AuditEventType
  actor_id: string
  draft_id: string | null
  entry_id: string | null
  occurred_at: string
  detail: string
}

export interface DashboardSummary {
  month: string
  income_uzs: number
  expense_uzs: number
  cost_of_goods_uzs: number
  gross_profit_uzs: number
  net_profit_uzs: number
  cash_uzs: number
  card_uzs: number
  transfer_uzs: number
  income_vs_expense_by_day: { date: string; income_uzs: number; expense_uzs: number }[]
  expense_by_category: { category: string; amount_uzs: number }[]
  recent_transactions: TransactionEntry[]
  pending_draft_count: number
  sync_status: 'ok' | 'degraded' | 'failed'
  last_synced_at: string | null
}

export interface Paginated<T> {
  items: T[]
  next_cursor: string | null
  total: number | null
}
