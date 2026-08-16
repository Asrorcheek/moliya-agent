// Mock implementations of the endpoints proposed in docs/API_CONTRACT.md.
// None of these exist on the real backend yet (see README "Hozir ishlaydigan
// qism" and the acceptance-criteria note that read endpoints beyond the
// monthly report are missing). Every function here is deliberately named
// and shaped exactly like its future real counterpart in src/lib/apiClient.ts
// so swapping the mock for a real call later is a one-line change per
// screen, not a rewrite.
//
// Every function simulates network latency and returns a fresh deep copy so
// screens can safely mutate what they read without corrupting the seed data.

import type {
  AuditEvent,
  Category,
  DashboardSummary,
  DraftRecord,
  Paginated,
  TransactionEntry,
} from '../types'
import {
  mockAuditEvents,
  mockCategories,
  mockDashboard,
  mockDrafts,
  mockTransactions,
  mockUsers,
} from './mockData'

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}

function delay<T>(value: T, ms = 450): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(clone(value)), ms))
}

// In-memory store so drafts confirmed/rejected during a session disappear
// from the pending list, mimicking real backend state without persistence.
let draftsStore: DraftRecord[] = clone(mockDrafts)

export interface TransactionFilters {
  dateFrom?: string
  dateTo?: string
  type?: string
  status?: string
  paymentMethod?: string
  category?: string
  counterparty?: string
  cursor?: string | null
}

export const mockApi = {
  listDrafts: (): Promise<DraftRecord[]> =>
    delay(draftsStore.filter((d) => d.status === 'pending')),

  getDraft: (draftId: string): Promise<DraftRecord | null> =>
    delay(draftsStore.find((d) => d.id === draftId) ?? null),

  confirmDraftMock: (draftId: string): Promise<DraftRecord | null> => {
    draftsStore = draftsStore.map((d) =>
      d.id === draftId
        ? { ...d, status: 'confirmed', confirmed_at: new Date().toISOString() }
        : d,
    )
    return delay(draftsStore.find((d) => d.id === draftId) ?? null)
  },

  rejectDraftMock: (draftId: string): Promise<DraftRecord | null> => {
    draftsStore = draftsStore.map((d) => (d.id === draftId ? { ...d, status: 'rejected' } : d))
    return delay(draftsStore.find((d) => d.id === draftId) ?? null)
  },

  listTransactions: (filters: TransactionFilters = {}): Promise<Paginated<TransactionEntry>> => {
    let items = clone(mockTransactions)
    if (filters.type) items = items.filter((t) => t.kind === filters.type)
    if (filters.paymentMethod) items = items.filter((t) => t.payment_method === filters.paymentMethod)
    if (filters.category) items = items.filter((t) => t.category === filters.category)
    if (filters.counterparty) {
      const needle = filters.counterparty.toLowerCase()
      items = items.filter((t) => t.counterparty?.toLowerCase().includes(needle))
    }
    if (filters.dateFrom) items = items.filter((t) => t.transaction_date >= filters.dateFrom!)
    if (filters.dateTo) items = items.filter((t) => t.transaction_date <= filters.dateTo!)
    return delay({ items, next_cursor: null, total: items.length })
  },

  getTransaction: (entryId: string): Promise<TransactionEntry | null> =>
    delay(mockTransactions.find((t) => t.entry_id === entryId) ?? null),

  listAuditEvents: (): Promise<AuditEvent[]> =>
    delay([...mockAuditEvents].sort((a, b) => (a.occurred_at < b.occurred_at ? 1 : -1))),

  dashboardSummary: (): Promise<DashboardSummary> => delay(mockDashboard),

  listCategories: (): Promise<Category[]> => delay(mockCategories),

  listUsers: () => delay(mockUsers),

  createReversal: (entryId: string): Promise<{ ok: boolean; reversalEntryId: string }> =>
    delay({ ok: true, reversalEntryId: `mock-reversal-${entryId}` }, 600),
}
