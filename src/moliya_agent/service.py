from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from .domain import DraftRecord, DraftStatus, EntryKind
from .parser import FinancialParser
from .repository import SQLiteDraftRepository
from .sheets import SheetWriter


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
        timezone_name: str = "Asia/Tashkent",
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._sheet_writer = sheet_writer
        self._allowed_actors = allowed_actors
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
        return self._repository.create(
            actor_id=actor_id,
            source_id=source_id,
            raw_text=text.strip(),
            parsed=parsed,
            now=local_now.astimezone(UTC),
        )

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
            written = self._sheet_writer.write_draft(
                draft, confirmed_by=actor_id, confirmed_at=now
            )
            confirmed = self._repository.set_status(
                draft.id, DraftStatus.CONFIRMED, now=now
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
        return self._repository.set_status(draft.id, DraftStatus.REJECTED)

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
