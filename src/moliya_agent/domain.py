from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class DomainValidationError(ValueError):
    """Raised when model or user data violates the finance contract."""


class EntryKind(StrEnum):
    INCOME = "income"
    EXPENSE = "expense"
    REFUND = "refund"
    COST_OF_GOODS = "cost_of_goods"
    RECEIVABLE = "receivable"
    PAYABLE = "payable"
    CUSTOMER_PAYMENT = "customer_payment"
    SUPPLIER_PAYMENT = "supplier_payment"


class PaymentMethod(StrEnum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class DraftStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


def _required(data: dict[str, Any], field: str) -> Any:
    if field not in data:
        raise DomainValidationError(f"Majburiy maydon yo'q: {field}")
    return data[field]


def _nullable_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DomainValidationError(f"{field} matn yoki null bo'lishi kerak")
    cleaned = value.strip()
    return cleaned or None


def _money(value: Any, field: str, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DomainValidationError(f"{field} butun UZS summasi bo'lishi kerak")
    minimum = 1 if positive else 0
    if value < minimum:
        comparator = "musbat" if positive else "manfiy bo'lmagan"
        raise DomainValidationError(f"{field} {comparator} bo'lishi kerak")
    return value


@dataclass(frozen=True, slots=True)
class PaymentBreakdown:
    cash_uzs: int
    card_uzs: int
    transfer_uzs: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaymentBreakdown:
        if not isinstance(data, dict):
            raise DomainValidationError("payment_breakdown obyekt bo'lishi kerak")
        return cls(
            cash_uzs=_money(_required(data, "cash_uzs"), "cash_uzs"),
            card_uzs=_money(_required(data, "card_uzs"), "card_uzs"),
            transfer_uzs=_money(_required(data, "transfer_uzs"), "transfer_uzs"),
        )

    @property
    def total_uzs(self) -> int:
        return self.cash_uzs + self.card_uzs + self.transfer_uzs

    def to_dict(self) -> dict[str, int]:
        return {
            "cash_uzs": self.cash_uzs,
            "card_uzs": self.card_uzs,
            "transfer_uzs": self.transfer_uzs,
        }


@dataclass(frozen=True, slots=True)
class FinancialEntry:
    kind: EntryKind
    amount_uzs: int
    payment_method: PaymentMethod
    payment_breakdown: PaymentBreakdown
    cost_uzs: int
    category: str | None
    counterparty: str | None
    note: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FinancialEntry:
        if not isinstance(data, dict):
            raise DomainValidationError("Har bir entry obyekt bo'lishi kerak")
        try:
            kind = EntryKind(_required(data, "kind"))
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("Noto'g'ri entry kind") from exc
        try:
            payment_method = PaymentMethod(_required(data, "payment_method"))
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("Noto'g'ri payment_method") from exc

        entry = cls(
            kind=kind,
            amount_uzs=_money(_required(data, "amount_uzs"), "amount_uzs", positive=True),
            payment_method=payment_method,
            payment_breakdown=PaymentBreakdown.from_dict(
                _required(data, "payment_breakdown")
            ),
            cost_uzs=_money(_required(data, "cost_uzs"), "cost_uzs"),
            category=_nullable_string(_required(data, "category"), "category"),
            counterparty=_nullable_string(_required(data, "counterparty"), "counterparty"),
            note=_nullable_string(_required(data, "note"), "note"),
        )
        entry.validate_business_rules()
        return entry

    def validate_business_rules(self) -> None:
        split_total = self.payment_breakdown.total_uzs
        if self.cost_uzs and self.kind != EntryKind.INCOME:
            raise DomainValidationError(
                "cost_uzs faqat tegishli income entry ichida beriladi"
            )
        if self.payment_method == PaymentMethod.UNKNOWN and split_total != 0:
            raise DomainValidationError(
                "To'lov turi unknown bo'lsa payment breakdown 0 bo'lishi kerak"
            )
        if self.payment_method != PaymentMethod.UNKNOWN and split_total != self.amount_uzs:
            raise DomainValidationError(
                "Ma'lum to'lov turida cash+card+transfer entry summasiga teng bo'lishi kerak"
            )
        if self.payment_method == PaymentMethod.CASH and (
            self.payment_breakdown.cash_uzs != self.amount_uzs
            or self.payment_breakdown.card_uzs
            or self.payment_breakdown.transfer_uzs
        ):
            raise DomainValidationError("cash entry faqat cash ustuniga tushishi kerak")
        if self.payment_method == PaymentMethod.CARD and (
            self.payment_breakdown.card_uzs != self.amount_uzs
            or self.payment_breakdown.cash_uzs
            or self.payment_breakdown.transfer_uzs
        ):
            raise DomainValidationError("card entry faqat card ustuniga tushishi kerak")
        if self.payment_method == PaymentMethod.TRANSFER and (
            self.payment_breakdown.transfer_uzs != self.amount_uzs
            or self.payment_breakdown.cash_uzs
            or self.payment_breakdown.card_uzs
        ):
            raise DomainValidationError("transfer entry faqat transfer ustuniga tushishi kerak")

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "amount_uzs": self.amount_uzs,
            "payment_method": self.payment_method.value,
            "payment_breakdown": self.payment_breakdown.to_dict(),
            "cost_uzs": self.cost_uzs,
            "category": self.category,
            "counterparty": self.counterparty,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class ParsedMessage:
    transaction_date: date
    currency: str
    entries: tuple[FinancialEntry, ...]
    new_customer_count: int
    needs_clarification: bool
    clarification_question: str | None
    missing_fields: tuple[str, ...]
    confidence: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ParsedMessage:
        if not isinstance(data, dict):
            raise DomainValidationError("Parsed message obyekt bo'lishi kerak")
        try:
            transaction_date = date.fromisoformat(_required(data, "transaction_date"))
        except (TypeError, ValueError) as exc:
            raise DomainValidationError("transaction_date YYYY-MM-DD bo'lishi kerak") from exc

        raw_entries = _required(data, "entries")
        if not isinstance(raw_entries, list):
            raise DomainValidationError("entries ro'yxat bo'lishi kerak")
        entries = tuple(FinancialEntry.from_dict(item) for item in raw_entries)

        new_customer_count = _money(
            _required(data, "new_customer_count"), "new_customer_count"
        )
        needs_clarification = _required(data, "needs_clarification")
        if not isinstance(needs_clarification, bool):
            raise DomainValidationError("needs_clarification boolean bo'lishi kerak")
        clarification_question = _nullable_string(
            _required(data, "clarification_question"), "clarification_question"
        )
        raw_missing = _required(data, "missing_fields")
        if not isinstance(raw_missing, list) or not all(
            isinstance(item, str) and item.strip() for item in raw_missing
        ):
            raise DomainValidationError("missing_fields matnlar ro'yxati bo'lishi kerak")
        confidence_value = _required(data, "confidence")
        if isinstance(confidence_value, bool) or not isinstance(confidence_value, (int, float)):
            raise DomainValidationError("confidence raqam bo'lishi kerak")
        confidence = float(confidence_value)
        if not 0 <= confidence <= 1:
            raise DomainValidationError("confidence 0 va 1 oralig'ida bo'lishi kerak")

        parsed = cls(
            transaction_date=transaction_date,
            currency=str(_required(data, "currency")).upper(),
            entries=entries,
            new_customer_count=new_customer_count,
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            missing_fields=tuple(item.strip() for item in raw_missing),
            confidence=confidence,
        )
        parsed.validate_business_rules()
        return parsed

    def validate_business_rules(self) -> None:
        if self.currency != "UZS":
            raise DomainValidationError("MVP faqat UZS valyutasini qabul qiladi")
        if not self.entries and not self.needs_clarification:
            raise DomainValidationError("Moliyaviy entry topilmasa aniqlashtirish talab qilinadi")
        if self.needs_clarification and not self.clarification_question:
            raise DomainValidationError("Aniqlashtirish savoli bo'lishi kerak")

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_date": self.transaction_date.isoformat(),
            "currency": self.currency,
            "entries": [entry.to_dict() for entry in self.entries],
            "new_customer_count": self.new_customer_count,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "missing_fields": list(self.missing_fields),
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class DraftRecord:
    id: str
    actor_id: str
    source_id: str
    raw_text: str
    parsed: ParsedMessage
    status: DraftStatus
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "actor_id": self.actor_id,
            "source_id": self.source_id,
            "raw_text": self.raw_text,
            "parsed": self.parsed.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
