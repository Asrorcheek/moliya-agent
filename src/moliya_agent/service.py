from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .domain import DraftRecord, DraftStatus, EntryKind, PaymentMethod
from .parser import FinancialParser
from .repository import SQLiteDraftRepository
from .sheets import FinancialReportReader, SheetReadError, SheetWriter


class AuthorizationError(PermissionError):
    pass


class InvalidTransitionError(RuntimeError):
    pass


class ClarificationRequiredError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    draft: DraftRecord
    written_rows: int
    already_confirmed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "draft": self.draft.to_dict(),
            "written_rows": self.written_rows,
            "already_confirmed": self.already_confirmed,
        }


class MoliyaService:
    def __init__(
        self,
        *,
        repository: SQLiteDraftRepository,
        parser: FinancialParser,
        sheet_writer: SheetWriter,
        allowed_actors: frozenset[str],
        report_reader: FinancialReportReader | None = None,
        timezone_name: str = "Asia/Tashkent",
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._sheet_writer = sheet_writer
        self._allowed_actors = allowed_actors
        self._report_reader = report_reader
        self._timezone = ZoneInfo(timezone_name)
        self._confirmation_lock = threading.RLock()

    def _authorize(self, actor_id: str) -> None:
        if actor_id not in self._allowed_actors:
            raise AuthorizationError(f"Actor ruxsat etilmagan: {actor_id}")

    def create_draft(
        self,
        *,
        actor_id: str,
        source_id: str,
        text: str,
        received_at: datetime | None = None,
    ) -> DraftRecord:
        self._authorize(actor_id)
        if not source_id.strip():
            raise ValueError("source_id bo'sh bo'lmasin")
        if not text.strip():
            raise ValueError("text bo'sh bo'lmasin")
        existing = self._repository.get_by_source(actor_id, source_id)
        if existing:
            return existing

        local_now = received_at or datetime.now(self._timezone)
        if local_now.tzinfo is None:
            local_now = local_now.replace(tzinfo=self._timezone)
        parsed = self._parser.parse(text, today=local_now.astimezone(self._timezone).date())
        draft = self._repository.create(
            actor_id=actor_id,
            source_id=source_id,
            raw_text=text.strip(),
            parsed=parsed,
            now=local_now.astimezone(UTC),
        )
        self._repository.add_audit_event(
            actor_id=actor_id,
            event_type="draft.created",
            entity_type="draft",
            entity_id=draft.id,
            details={"source_id": source_id, "entry_count": len(draft.parsed.entries)},
            now=local_now.astimezone(UTC),
        )
        return draft

    def confirm(self, *, actor_id: str, draft_id: str) -> ConfirmationResult:
        self._authorize(actor_id)
        with self._confirmation_lock:
            draft = self._repository.get(draft_id)
            if draft.actor_id != actor_id:
                raise AuthorizationError("Boshqa actor draftini tasdiqlab bo'lmaydi")
            if draft.status == DraftStatus.CONFIRMED:
                # The writer is idempotent, so a retry also heals a partial DB failure.
                written = self._sheet_writer.write_draft(
                    draft,
                    confirmed_by=actor_id,
                    confirmed_at=draft.confirmed_at or datetime.now(UTC),
                )
                return ConfirmationResult(
                    draft=draft, written_rows=written, already_confirmed=True
                )
            if draft.status == DraftStatus.REJECTED:
                raise InvalidTransitionError("Rad etilgan draftni tasdiqlab bo'lmaydi")
            if draft.parsed.needs_clarification:
                raise ClarificationRequiredError(
                    draft.parsed.clarification_question
                    or "Ma'lumotni aniqlashtirish kerak"
                )

            now = datetime.now(UTC)
            try:
                written = self._sheet_writer.write_draft(
                    draft, confirmed_by=actor_id, confirmed_at=now
                )
            except Exception as exc:
                self._repository.add_audit_event(
                    actor_id=actor_id,
                    event_type="sheet.write_failed",
                    entity_type="draft",
                    entity_id=draft.id,
                    details={"error_type": type(exc).__name__},
                    now=now,
                )
                raise
            confirmed = self._repository.set_status(
                draft.id, DraftStatus.CONFIRMED, now=now
            )
            self._repository.add_audit_event(
                actor_id=actor_id,
                event_type="draft.confirmed",
                entity_type="draft",
                entity_id=draft.id,
                details={"written_rows": written},
                now=now,
            )
            return ConfirmationResult(
                draft=confirmed, written_rows=written, already_confirmed=False
            )

    def reject(self, *, actor_id: str, draft_id: str) -> DraftRecord:
        self._authorize(actor_id)
        draft = self._repository.get(draft_id)
        if draft.actor_id != actor_id:
            raise AuthorizationError("Boshqa actor draftini rad etib bo'lmaydi")
        if draft.status == DraftStatus.CONFIRMED:
            raise InvalidTransitionError(
                "Tasdiqlangan yozuvni rad etib bo'lmaydi; reversal kerak"
            )
        if draft.status == DraftStatus.REJECTED:
            return draft
        rejected = self._repository.set_status(draft.id, DraftStatus.REJECTED)
        self._repository.add_audit_event(
            actor_id=actor_id,
            event_type="draft.rejected",
            entity_type="draft",
            entity_id=draft.id,
        )
        return rejected

    def monthly_report(self, *, actor_id: str, month: str) -> dict[str, int | str]:
        self._authorize(actor_id)
        try:
            year, month_number = (int(part) for part in month.split("-", maxsplit=1))
            if not 1 <= month_number <= 12:
                raise ValueError
        except ValueError as exc:
            raise ValueError("month YYYY-MM formatida bo'lishi kerak") from exc

        income = expenses = refunds = cogs = 0
        for draft in self._repository.list_confirmed():
            if draft.actor_id != actor_id:
                continue
            transaction_date = draft.parsed.transaction_date
            if transaction_date.year != year or transaction_date.month != month_number:
                continue
            for entry in draft.parsed.entries:
                if entry.kind == EntryKind.INCOME:
                    income += entry.amount_uzs
                elif entry.kind == EntryKind.EXPENSE:
                    expenses += entry.amount_uzs
                elif entry.kind == EntryKind.REFUND:
                    refunds += entry.amount_uzs
                elif entry.kind == EntryKind.COST_OF_GOODS:
                    cogs += entry.amount_uzs
                cogs += entry.cost_uzs

        net_revenue = income - refunds
        gross_profit = net_revenue - cogs
        return {
            "month": month,
            "currency": "UZS",
            "income_uzs": income,
            "refund_uzs": refunds,
            "net_revenue_uzs": net_revenue,
            "cost_of_goods_uzs": cogs,
            "gross_profit_uzs": gross_profit,
            "expense_uzs": expenses,
            "net_profit_uzs": gross_profit - expenses,
        }

    def get_draft(self, *, actor_id: str, draft_id: str) -> DraftRecord:
        self._authorize(actor_id)
        draft = self._repository.get(draft_id)
        if draft.actor_id != actor_id:
            raise AuthorizationError("Boshqa actor draftini ko'rib bo'lmaydi")
        return draft

    def list_drafts(
        self,
        *,
        actor_id: str,
        status: DraftStatus | None,
        limit: int,
        offset: int,
    ) -> tuple[list[DraftRecord], int]:
        self._authorize(actor_id)
        return self._repository.list_drafts(
            actor_id=actor_id, status=status, limit=limit, offset=offset
        )

    def list_transactions(
        self,
        *,
        actor_id: str,
        month: str | None = None,
        kind: EntryKind | None = None,
        payment_method: PaymentMethod | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, object]], int]:
        self._authorize(actor_id)
        drafts, _ = self._repository.list_drafts(
            actor_id=actor_id, status=DraftStatus.CONFIRMED, limit=10_000, offset=0
        )
        transactions: list[dict[str, object]] = []
        for draft in drafts:
            if month and not draft.parsed.transaction_date.isoformat().startswith(month):
                continue
            for index, entry in enumerate(draft.parsed.entries):
                if kind and entry.kind != kind:
                    continue
                if payment_method and entry.payment_method != payment_method:
                    continue
                transactions.append(
                    {
                        "entry_id": f"{draft.id}:{index}",
                        "draft_id": draft.id,
                        "actor_id": draft.actor_id,
                        "source_id": draft.source_id,
                        "transaction_date": draft.parsed.transaction_date.isoformat(),
                        "confirmed_at": (
                            draft.confirmed_at.isoformat() if draft.confirmed_at else None
                        ),
                        **entry.to_dict(),
                    }
                )
        total = len(transactions)
        return transactions[offset : offset + limit], total

    def dashboard_report(self, *, actor_id: str, month: str) -> dict[str, object]:
        summary = self.monthly_report(actor_id=actor_id, month=month)
        transactions, transaction_count = self.list_transactions(
            actor_id=actor_id, month=month, limit=10_000
        )
        pending, pending_count = self.list_drafts(
            actor_id=actor_id, status=DraftStatus.PENDING, limit=5, offset=0
        )
        payment_totals = {"cash_uzs": 0, "card_uzs": 0, "transfer_uzs": 0}
        daily_totals: dict[str, dict[str, int]] = {}
        category_totals: dict[str, int] = {}
        for transaction in transactions:
            breakdown = transaction["payment_breakdown"]
            if isinstance(breakdown, dict):
                for key in payment_totals:
                    payment_totals[key] += int(breakdown.get(key, 0))
            date_label = str(transaction["transaction_date"])[5:]
            day = daily_totals.setdefault(
                date_label, {"income_uzs": 0, "expense_uzs": 0}
            )
            kind = transaction["kind"]
            amount = int(transaction["amount_uzs"])
            if kind == EntryKind.INCOME.value:
                day["income_uzs"] += amount
            elif kind in {EntryKind.EXPENSE.value, EntryKind.COST_OF_GOODS.value}:
                day["expense_uzs"] += amount
                category = str(transaction.get("category") or "Boshqa")
                category_totals[category] = category_totals.get(category, 0) + amount
        return {
            "summary": summary,
            "payment_totals": payment_totals,
            "pending_count": pending_count,
            "transaction_count": transaction_count,
            "recent_transactions": transactions[:5],
            "pending_drafts": [draft.to_dict() for draft in pending],
            "income_vs_expense_by_day": [
                {"date": date, **daily_totals[date]} for date in sorted(daily_totals)
            ],
            "expense_by_category": [
                {"category": category, "amount_uzs": amount}
                for category, amount in sorted(
                    category_totals.items(), key=lambda item: item[1], reverse=True
                )
            ],
        }

    @staticmethod
    def _months_ending_at(month: str, count: int = 6) -> list[str]:
        year, month_number = (int(part) for part in month.split("-", maxsplit=1))
        result = []
        for offset in range(count - 1, -1, -1):
            absolute = year * 12 + month_number - 1 - offset
            result.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
        return result

    def financial_overview(self, *, actor_id: str, month: str) -> dict[str, object]:
        self._authorize(actor_id)
        try:
            year, month_number = (int(part) for part in month.split("-", maxsplit=1))
            if year < 2000 or not 1 <= month_number <= 12:
                raise ValueError
        except ValueError as exc:
            raise ValueError("month YYYY-MM formatida bo'lishi kerak") from exc
        if self._report_reader is not None:
            try:
                return self._report_reader.read_financial_overview(month)
            except SheetReadError:
                pass
        months = self._months_ending_at(month)
        transactions, _ = self.list_transactions(actor_id=actor_id, limit=10_000)
        transactions = [
            item for item in transactions if str(item["transaction_date"])[:7] <= month
        ]
        trend = []
        running_cash = 0
        earlier = [
            item for item in transactions if str(item["transaction_date"])[:7] < months[0]
        ]
        for item in earlier:
            running_cash += self._cash_effect(item)
        for label in months:
            report = self.monthly_report(actor_id=actor_id, month=label)
            month_items = [
                item for item in transactions if str(item["transaction_date"])[:7] == label
            ]
            inflow = sum(
                self._paid_amount(item)
                for item in month_items
                if item["kind"] in {EntryKind.INCOME.value, EntryKind.CUSTOMER_PAYMENT.value}
            )
            outflow = sum(
                self._paid_amount(item)
                for item in month_items
                if item["kind"]
                in {
                    EntryKind.EXPENSE.value,
                    EntryKind.REFUND.value,
                    EntryKind.COST_OF_GOODS.value,
                    EntryKind.SUPPLIER_PAYMENT.value,
                }
            )
            running_cash += inflow - outflow
            trend.append(
                {
                    **report,
                    "cash_inflow_uzs": inflow,
                    "cash_outflow_uzs": outflow,
                    "net_cash_flow_uzs": inflow - outflow,
                    "ending_cash_uzs": running_cash,
                }
            )
        balance = self._ledger_balance(transactions)
        return {"source": "ledger", "month": month, "trend": trend, "balance": balance}

    @staticmethod
    def _paid_amount(item: dict[str, object]) -> int:
        breakdown = item.get("payment_breakdown")
        if not isinstance(breakdown, dict):
            return 0
        return sum(int(breakdown.get(key, 0)) for key in ("cash_uzs", "card_uzs", "transfer_uzs"))

    @classmethod
    def _cash_effect(cls, item: dict[str, object]) -> int:
        amount = cls._paid_amount(item)
        return amount if item["kind"] in {
            EntryKind.INCOME.value,
            EntryKind.CUSTOMER_PAYMENT.value,
        } else -amount

    @classmethod
    def _ledger_balance(cls, transactions: list[dict[str, object]]) -> dict[str, int]:
        cash = bank = receivables = inventory = payables = equity = 0
        for item in transactions:
            breakdown = item.get("payment_breakdown")
            if isinstance(breakdown, dict):
                sign = 1 if item["kind"] in {
                    EntryKind.INCOME.value,
                    EntryKind.CUSTOMER_PAYMENT.value,
                } else -1
                cash += sign * int(breakdown.get("cash_uzs", 0))
                bank += sign * (
                    int(breakdown.get("card_uzs", 0))
                    + int(breakdown.get("transfer_uzs", 0))
                )
            amount = int(item["amount_uzs"])
            kind = item["kind"]
            if kind == EntryKind.RECEIVABLE.value:
                receivables += amount
            elif kind == EntryKind.CUSTOMER_PAYMENT.value:
                receivables -= amount
            elif kind == EntryKind.PAYABLE.value:
                payables += amount
            elif kind == EntryKind.SUPPLIER_PAYMENT.value:
                payables -= amount
            cogs = int(item.get("cost_uzs", 0))
            if kind == EntryKind.COST_OF_GOODS.value:
                cogs += amount
            inventory -= cogs
            if kind == EntryKind.INCOME.value:
                equity += amount - cogs
            elif kind in {
                EntryKind.REFUND.value,
                EntryKind.EXPENSE.value,
                EntryKind.COST_OF_GOODS.value,
            }:
                equity -= amount
        assets = cash + bank + receivables + inventory
        liabilities_and_equity = payables + equity
        return {
            "cash_uzs": cash,
            "bank_uzs": bank,
            "receivables_uzs": receivables,
            "inventory_uzs": inventory,
            "total_assets_uzs": assets,
            "payables_uzs": payables,
            "total_liabilities_uzs": payables,
            "equity_uzs": equity,
            "liabilities_and_equity_uzs": liabilities_and_equity,
            "difference_uzs": assets - liabilities_and_equity,
        }

    def list_audit_events(
        self, *, actor_id: str, limit: int, offset: int
    ) -> tuple[list[dict[str, object]], int]:
        self._authorize(actor_id)
        return self._repository.list_audit_events(
            actor_id=actor_id, limit=limit, offset=offset
        )


def format_draft_preview(draft: DraftRecord) -> str:
    lines = [f"Sana: {draft.parsed.transaction_date.isoformat()}"]
    labels = {
        EntryKind.INCOME: "Tushum",
        EntryKind.EXPENSE: "Xarajat",
        EntryKind.REFUND: "Vazvrat",
        EntryKind.COST_OF_GOODS: "Tan narx",
        EntryKind.RECEIVABLE: "Debitor qarz",
        EntryKind.PAYABLE: "Kreditor qarz",
        EntryKind.CUSTOMER_PAYMENT: "Mijoz to'lovi",
        EntryKind.SUPPLIER_PAYMENT: "Yetkazib beruvchiga to'lov",
    }
    for index, entry in enumerate(draft.parsed.entries, start=1):
        method = {
            "cash": "naqd",
            "card": "karta",
            "transfer": "o'tkazma",
            "mixed": "aralash",
            "unknown": "to'lov turi ko'rsatilmagan",
        }[entry.payment_method.value]
        line = f"{index}. {labels[entry.kind]}: {entry.amount_uzs:,} UZS ({method})"
        if entry.category:
            line += f", kategoriya: {entry.category}"
        if entry.counterparty:
            line += f", kontragent: {entry.counterparty}"
        lines.append(line)
    if draft.parsed.new_customer_count:
        lines.append(f"Yangi mijozlar: {draft.parsed.new_customer_count}")
    if draft.parsed.needs_clarification:
        lines.append(
            f"Aniqlashtirish kerak: {draft.parsed.clarification_question}"
        )
    else:
        lines.append(f"Draft ID: {draft.id}")
        lines.append('Yozish uchun "ha" yoki "tasdiqlayman" deb javob bering.')
    return "\n".join(lines)
