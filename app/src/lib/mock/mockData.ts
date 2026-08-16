import type {
  AppUser,
  AuditEvent,
  Category,
  DashboardSummary,
  DraftRecord,
  TransactionEntry,
} from '../types'

export const mockUsers: AppUser[] = [
  { id: 'u1', full_name: 'Aziz Karimov', role: 'owner', telegram_linked: true },
  { id: 'u2', full_name: 'Dilnoza Yusupova', role: 'manager', telegram_linked: true },
  { id: 'u3', full_name: 'Botir Rahimov', role: 'accountant', telegram_linked: false },
]

export const mockCategories: Category[] = [
  { id: 'c1', name_uz: 'Ijara', name_ru: 'Аренда', name_en: 'Rent', is_custom: false },
  { id: 'c2', name_uz: 'Oylik', name_ru: 'Зарплата', name_en: 'Payroll', is_custom: false },
  { id: 'c3', name_uz: 'Kommunal', name_ru: 'Коммунальные', name_en: 'Utilities', is_custom: false },
  { id: 'c4', name_uz: 'Soliq', name_ru: 'Налоги', name_en: 'Tax', is_custom: false },
  { id: 'c5', name_uz: 'Marketing', name_ru: 'Маркетинг', name_en: 'Marketing', is_custom: false },
  { id: 'c6', name_uz: 'Yetkazib berish', name_ru: 'Доставка', name_en: 'Delivery', is_custom: false },
  { id: 'c7', name_uz: 'Boshqa', name_ru: 'Прочее', name_en: 'Other', is_custom: false },
]

function entry(overrides: Partial<TransactionEntry> = {}): TransactionEntry {
  return {
    entry_id: 'e-0000',
    draft_id: 'd-0000',
    transaction_date: '2026-08-10',
    kind: 'income',
    amount_uzs: 0,
    payment_method: 'cash',
    payment_breakdown: { cash_uzs: 0, card_uzs: 0, transfer_uzs: 0 },
    cost_uzs: 0,
    category: null,
    counterparty: null,
    note: null,
    source_id: 'telegram-mock',
    confirmed_by: 'hermes',
    confirmed_at: '2026-08-10T09:00:00+05:00',
    reversed_entry_id: null,
    reversal_of_entry_id: null,
    ...overrides,
  }
}

export const mockTransactions: TransactionEntry[] = [
  entry({
    entry_id: 'e-1001', draft_id: 'd-1001', transaction_date: '2026-08-15',
    kind: 'income', amount_uzs: 2_000_000, payment_method: 'cash',
    payment_breakdown: { cash_uzs: 2_000_000, card_uzs: 0, transfer_uzs: 0 },
    counterparty: 'Do\u2019kon mijozi', confirmed_at: '2026-08-15T10:12:00+05:00',
  }),
  entry({
    entry_id: 'e-1002', draft_id: 'd-1002', transaction_date: '2026-08-15',
    kind: 'expense', amount_uzs: 500_000, payment_method: 'card',
    payment_breakdown: { cash_uzs: 0, card_uzs: 500_000, transfer_uzs: 0 },
    category: 'Marketing', confirmed_at: '2026-08-15T10:12:30+05:00',
  }),
  entry({
    entry_id: 'e-1003', draft_id: 'd-1003', transaction_date: '2026-08-14',
    kind: 'cost_of_goods', amount_uzs: 800_000, payment_method: 'transfer',
    payment_breakdown: { cash_uzs: 0, card_uzs: 0, transfer_uzs: 800_000 },
    counterparty: 'Ta\u2019minotchi MCHJ', confirmed_at: '2026-08-14T16:40:00+05:00',
  }),
  entry({
    entry_id: 'e-1004', draft_id: 'd-1004', transaction_date: '2026-08-13',
    kind: 'refund', amount_uzs: 150_000, payment_method: 'cash',
    payment_breakdown: { cash_uzs: 150_000, card_uzs: 0, transfer_uzs: 0 },
    counterparty: 'Mijoz \u2014 Nodira', confirmed_at: '2026-08-13T12:05:00+05:00',
  }),
  entry({
    entry_id: 'e-1005', draft_id: 'd-1005', transaction_date: '2026-08-12',
    kind: 'payable', amount_uzs: 1_200_000, payment_method: 'unknown',
    payment_breakdown: { cash_uzs: 0, card_uzs: 0, transfer_uzs: 0 },
    counterparty: 'Yetkazib beruvchi \u2014 Optom baza', confirmed_at: '2026-08-12T09:30:00+05:00',
  }),
  entry({
    entry_id: 'e-1006', draft_id: 'd-1002', transaction_date: '2026-08-11',
    kind: 'expense', amount_uzs: 500_000, payment_method: 'card',
    payment_breakdown: { cash_uzs: 0, card_uzs: 500_000, transfer_uzs: 0 },
    category: 'Marketing', confirmed_at: '2026-08-11T09:00:00+05:00',
    note: 'Dublikat kiritilgani uchun bekor qilindi', reversed_entry_id: 'e-1007',
  }),
  entry({
    entry_id: 'e-1007', draft_id: 'd-1006', transaction_date: '2026-08-11',
    kind: 'expense', amount_uzs: -500_000, payment_method: 'card',
    payment_breakdown: { cash_uzs: 0, card_uzs: -500_000, transfer_uzs: 0 },
    category: 'Marketing', confirmed_at: '2026-08-11T09:05:00+05:00',
    note: 'e-1006 uchun reversal', reversal_of_entry_id: 'e-1006',
  }),
]

export const mockDrafts: DraftRecord[] = [
  {
    id: 'd-2001',
    actor_id: 'hermes',
    source_id: 'telegram-msg-9001',
    raw_text: 'Bugun 3.5 mln tushum karta, 900 ming ijara xarajati naqd',
    status: 'pending',
    created_at: '2026-08-16T08:02:00+05:00',
    updated_at: '2026-08-16T08:02:00+05:00',
    confirmed_at: null,
    parsed: {
      transaction_date: '2026-08-16',
      currency: 'UZS',
      new_customer_count: 0,
      needs_clarification: false,
      clarification_question: null,
      missing_fields: [],
      confidence: 0.94,
      entries: [
        {
          kind: 'income', amount_uzs: 3_500_000, payment_method: 'card',
          payment_breakdown: { cash_uzs: 0, card_uzs: 3_500_000, transfer_uzs: 0 },
          cost_uzs: 0, category: null, counterparty: null, note: null,
        },
        {
          kind: 'expense', amount_uzs: 900_000, payment_method: 'cash',
          payment_breakdown: { cash_uzs: 900_000, card_uzs: 0, transfer_uzs: 0 },
          cost_uzs: 0, category: 'Ijara', counterparty: null, note: null,
        },
      ],
    },
  },
  {
    id: 'd-2002',
    actor_id: 'hermes',
    source_id: 'telegram-msg-9004',
    raw_text: 'Optom bazadan tovar oldik, 2 mln, to\u2019lov keyinroq',
    status: 'pending',
    created_at: '2026-08-16T09:15:00+05:00',
    updated_at: '2026-08-16T09:15:00+05:00',
    confirmed_at: null,
    parsed: {
      transaction_date: '2026-08-16',
      currency: 'UZS',
      new_customer_count: 0,
      needs_clarification: false,
      clarification_question: null,
      missing_fields: ['counterparty'],
      confidence: 0.71,
      entries: [
        {
          kind: 'payable', amount_uzs: 2_000_000, payment_method: 'unknown',
          payment_breakdown: { cash_uzs: 0, card_uzs: 0, transfer_uzs: 0 },
          cost_uzs: 0, category: null, counterparty: 'Optom baza', note: null,
        },
      ],
    },
  },
  {
    id: 'd-2003',
    actor_id: 'hermes',
    source_id: 'telegram-msg-9007',
    raw_text: 'Bugun sotuv bo\u2019ldi, summasi keyin aniq bo\u2019ladi',
    status: 'pending',
    created_at: '2026-08-16T10:41:00+05:00',
    updated_at: '2026-08-16T10:41:00+05:00',
    confirmed_at: null,
    parsed: {
      transaction_date: '2026-08-16',
      currency: 'UZS',
      new_customer_count: 0,
      needs_clarification: true,
      clarification_question: 'Sotuv summasi qancha bo\u2019ldi?',
      missing_fields: ['amount_uzs'],
      confidence: 0.32,
      entries: [],
    },
  },
]

export const mockAuditEvents: AuditEvent[] = [
  { id: 'a1', event_type: 'draft_created', actor_id: 'hermes', draft_id: 'd-1001', entry_id: null, occurred_at: '2026-08-15T10:11:40+05:00', detail: 'Draft d-1001 yaratildi' },
  { id: 'a2', event_type: 'draft_confirmed', actor_id: 'Aziz Karimov', draft_id: 'd-1001', entry_id: 'e-1001', occurred_at: '2026-08-15T10:12:00+05:00', detail: 'Draft d-1001 tasdiqlandi' },
  { id: 'a3', event_type: 'sheet_write_succeeded', actor_id: 'system', draft_id: 'd-1001', entry_id: 'e-1001', occurred_at: '2026-08-15T10:12:02+05:00', detail: 'Operatsiyalar varag\u2019iga yozildi' },
  { id: 'a4', event_type: 'draft_created', actor_id: 'hermes', draft_id: 'd-1006', entry_id: null, occurred_at: '2026-08-11T09:04:00+05:00', detail: 'Draft d-1006 yaratildi' },
  { id: 'a5', event_type: 'reversal_created', actor_id: 'Botir Rahimov', draft_id: 'd-1006', entry_id: 'e-1007', occurred_at: '2026-08-11T09:05:00+05:00', detail: 'e-1006 uchun reversal e-1007 yaratildi' },
  { id: 'a6', event_type: 'draft_rejected', actor_id: 'Dilnoza Yusupova', draft_id: 'd-1998', entry_id: null, occurred_at: '2026-08-10T14:20:00+05:00', detail: 'Draft d-1998 rad etildi \u2014 noto\u2019g\u2019ri summa' },
]

export const mockDashboard: DashboardSummary = {
  month: '2026-08',
  income_uzs: 18_400_000,
  expense_uzs: 6_150_000,
  cost_of_goods_uzs: 4_900_000,
  gross_profit_uzs: 13_500_000,
  net_profit_uzs: 7_350_000,
  cash_uzs: 9_200_000,
  card_uzs: 6_800_000,
  transfer_uzs: 2_400_000,
  income_vs_expense_by_day: [
    { date: '08-10', income_uzs: 1_800_000, expense_uzs: 400_000 },
    { date: '08-11', income_uzs: 2_100_000, expense_uzs: 500_000 },
    { date: '08-12', income_uzs: 1_500_000, expense_uzs: 1_200_000 },
    { date: '08-13', income_uzs: 2_600_000, expense_uzs: 150_000 },
    { date: '08-14', income_uzs: 1_900_000, expense_uzs: 800_000 },
    { date: '08-15', income_uzs: 3_500_000, expense_uzs: 900_000 },
    { date: '08-16', income_uzs: 2_200_000, expense_uzs: 600_000 },
  ],
  expense_by_category: [
    { category: 'Ijara', amount_uzs: 1_800_000 },
    { category: 'Oylik', amount_uzs: 2_200_000 },
    { category: 'Marketing', amount_uzs: 1_000_000 },
    { category: 'Kommunal', amount_uzs: 650_000 },
    { category: 'Boshqa', amount_uzs: 500_000 },
  ],
  recent_transactions: mockTransactions.slice(0, 5),
  pending_draft_count: mockDrafts.filter((d) => d.status === 'pending').length,
  sync_status: 'ok',
  last_synced_at: '2026-08-16T10:45:00+05:00',
}
