// Typed client for the endpoints that genuinely exist on the Moliya backend
// today. Nothing in this file is mocked — every function here maps 1:1 to a
// real route in api.py. See src/lib/mock/mockApi.ts for the endpoints that
// do not exist yet.
//
// IMPORTANT: the real backend authenticates with X-Moliya-Token, an internal
// server-to-server secret. It must never be embedded in browser code. This
// client instead calls VITE_MOLIYA_API_BASE_URL directly for local/dev use
// against a backend that has CORS + a dev token configured, but the intended
// production shape is a backend-for-frontend (BFF) that terminates the
// user's session and injects the internal token server-side. Point
// VITE_MOLIYA_API_BASE_URL at that BFF once it exists.

import type { AuditEvent, DashboardSummary, DraftRecord, DraftStatus, EntryKind, MonthlyReport, PaymentMethod, TransactionEntry } from './types'

const BASE_URL = import.meta.env.VITE_MOLIYA_API_BASE_URL ?? ''

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export interface CreateDraftInput {
  actor_id: string
  source_id: string
  text: string
  received_at?: string | null
}

export interface SessionResponse {
  username: string
  actor_id: string
}

export interface HealthResponse {
  status: string
  parser_mode: string
  sheet_mode: string
}

interface BackendTransaction extends Omit<TransactionEntry, 'confirmed_by' | 'confirmed_at' | 'reversal_of_entry_id' | 'reversed_entry_id'> {
  actor_id: string
  confirmed_at: string | null
}

interface BackendDashboard {
  summary: MonthlyReport
  payment_totals: { cash_uzs: number; card_uzs: number; transfer_uzs: number }
  pending_count: number
  transaction_count: number
  recent_transactions: BackendTransaction[]
  income_vs_expense_by_day: DashboardSummary['income_vs_expense_by_day']
  expense_by_category: DashboardSummary['expense_by_category']
}

interface BackendAuditEvent {
  id: string
  actor_id: string
  event_type: string
  entity_type: string
  entity_id: string
  details: Record<string, unknown>
  created_at: string
}

function transactionFromBackend(item: BackendTransaction): TransactionEntry {
  return {
    ...item,
    confirmed_by: item.actor_id,
    confirmed_at: item.confirmed_at ?? '',
    reversal_of_entry_id: null,
    reversed_entry_id: null,
  }
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') search.set(key, String(value))
  })
  const encoded = search.toString()
  return encoded ? `?${encoded}` : ''
}

export const moliyaApi = {
  health: () => request<HealthResponse>('/health'),

  login: (username: string, password: string) =>
    request<SessionResponse>('/v1/session', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  currentSession: () => request<SessionResponse>('/v1/session'),

  logout: () => request<{ logged_out: boolean }>('/v1/session', { method: 'DELETE' }),

  createDraft: (input: CreateDraftInput) =>
    request<{ draft: DraftRecord; preview: string }>('/v1/drafts', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  confirmDraft: (draftId: string, actorId: string) =>
    request<Record<string, unknown>>(`/v1/drafts/${draftId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ actor_id: actorId }),
    }),

  rejectDraft: (draftId: string, actorId: string) =>
    request<{ draft: DraftRecord }>(`/v1/drafts/${draftId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ actor_id: actorId }),
    }),

  listDrafts: (actorId: string, status: DraftStatus | undefined = 'pending') =>
    request<{ items: DraftRecord[]; total: number }>(
      `/v1/drafts${query({ actor_id: actorId, status, limit: 100 })}`,
    ),

  listTransactions: async (
    actorId: string,
    filters: { month?: string; kind?: EntryKind; paymentMethod?: PaymentMethod } = {},
  ) => {
    const response = await request<{ items: BackendTransaction[]; total: number }>(
      `/v1/transactions${query({
        actor_id: actorId,
        month: filters.month,
        kind: filters.kind,
        payment_method: filters.paymentMethod,
        limit: 100,
      })}`,
    )
    return { ...response, items: response.items.map(transactionFromBackend) }
  },

  dashboardSummary: async (actorId: string, month: string): Promise<DashboardSummary> => {
    const response = await request<BackendDashboard>(
      `/v1/reports/dashboard${query({ actor_id: actorId, month })}`,
    )
    const recentTransactions = response.recent_transactions.map(transactionFromBackend)
    return {
      month: response.summary.month,
      income_uzs: response.summary.income_uzs,
      expense_uzs: response.summary.expense_uzs,
      cost_of_goods_uzs: response.summary.cost_of_goods_uzs,
      gross_profit_uzs: response.summary.gross_profit_uzs,
      net_profit_uzs: response.summary.net_profit_uzs,
      cash_uzs: response.payment_totals.cash_uzs,
      card_uzs: response.payment_totals.card_uzs,
      transfer_uzs: response.payment_totals.transfer_uzs,
      income_vs_expense_by_day: response.income_vs_expense_by_day,
      expense_by_category: response.expense_by_category,
      recent_transactions: recentTransactions,
      pending_draft_count: response.pending_count,
      sync_status: 'ok',
      last_synced_at: recentTransactions[0]?.confirmed_at || null,
    }
  },

  listAuditEvents: async (actorId: string): Promise<AuditEvent[]> => {
    const response = await request<{ items: BackendAuditEvent[]; total: number }>(
      `/v1/audit-events${query({ actor_id: actorId, limit: 100 })}`,
    )
    const knownTypes = new Set<AuditEvent['event_type']>([
      'draft_created', 'draft_confirmed', 'draft_rejected',
      'sheet_write_succeeded', 'sheet_write_failed', 'reversal_created',
    ])
    return response.items.map((item) => {
      const normalized = item.event_type.replaceAll('.', '_') as AuditEvent['event_type']
      const eventType = knownTypes.has(normalized) ? normalized : 'draft_created'
      const detailText = typeof item.details.detail === 'string'
        ? item.details.detail
        : `${item.event_type} · ${item.entity_id}`
      return {
        id: item.id,
        event_type: eventType,
        actor_id: item.actor_id,
        draft_id: item.entity_type === 'draft' ? item.entity_id : null,
        entry_id: item.entity_type === 'entry' ? item.entity_id : null,
        occurred_at: item.created_at,
        detail: detailText,
      }
    })
  },

  monthlyReport: (actorId: string, month: string) =>
    request<MonthlyReport>(`/v1/reports/monthly?actor_id=${encodeURIComponent(actorId)}&month=${encodeURIComponent(month)}`),
}
