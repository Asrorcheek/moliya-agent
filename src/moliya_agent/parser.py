from __future__ import annotations

import json
import re
from datetime import date, timedelta
from typing import Any, Protocol

from .domain import ParsedMessage


class ParseError(RuntimeError):
    """Raised when a parser cannot safely create a financial draft."""


class FinancialParser(Protocol):
    def parse(self, text: str, *, today: date) -> ParsedMessage: ...


FINANCIAL_MESSAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "transaction_date": {"type": "string", "format": "date"},
        "currency": {"type": "string", "enum": ["UZS"]},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": [
                            "income",
                            "expense",
                            "refund",
                            "cost_of_goods",
                            "receivable",
                            "payable",
                            "customer_payment",
                            "supplier_payment",
                        ],
                    },
                    "amount_uzs": {"type": "integer", "minimum": 1},
                    "payment_method": {
                        "type": "string",
                        "enum": ["cash", "card", "transfer", "mixed", "unknown"],
                    },
                    "payment_breakdown": {
                        "type": "object",
                        "properties": {
                            "cash_uzs": {"type": "integer", "minimum": 0},
                            "card_uzs": {"type": "integer", "minimum": 0},
                            "transfer_uzs": {"type": "integer", "minimum": 0},
                        },
                        "required": ["cash_uzs", "card_uzs", "transfer_uzs"],
                        "additionalProperties": False,
                    },
                    "cost_uzs": {"type": "integer", "minimum": 0},
                    "category": {"type": ["string", "null"]},
                    "counterparty": {"type": ["string", "null"]},
                    "note": {"type": ["string", "null"]},
                },
                "required": [
                    "kind",
                    "amount_uzs",
                    "payment_method",
                    "payment_breakdown",
                    "cost_uzs",
                    "category",
                    "counterparty",
                    "note",
                ],
                "additionalProperties": False,
            },
        },
        "new_customer_count": {"type": "integer", "minimum": 0},
        "needs_clarification": {"type": "boolean"},
        "clarification_question": {"type": ["string", "null"]},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "transaction_date",
        "currency",
        "entries",
        "new_customer_count",
        "needs_clarification",
        "clarification_question",
        "missing_fields",
        "confidence",
    ],
    "additionalProperties": False,
}


SYSTEM_PROMPT = """\
Role: Extract financial events from short Uzbek, Russian, or mixed-language messages.

Goal: Convert only explicitly stated facts into the supplied JSON schema.

Rules:
- Use UZS integer amounts. "mln" means 1,000,000 and "ming" means 1,000.
- Create one entry per distinct financial event.
- Never invent a payment method, category, counterparty, cost, or amount.
- If payment method is unknown, set payment_method=unknown and every breakdown value to 0.
- For cash/card/transfer, put the full amount in the matching breakdown field.
- For mixed payment, breakdown fields must add up exactly to amount_uzs.
- cost_uzs is nonzero only when a cost/tan narx is explicitly tied to an income entry.
- For a standalone kind=cost_of_goods entry, amount_uzs is the cost and cost_uzs must be 0.
- If a required fact is ambiguous, set needs_clarification=true, list missing_fields,
  and ask one short clarification_question. Preserve any unambiguous entries.
- Do not calculate profit, balances, or unstated values.

Success: The output matches the schema and preserves every explicit financial fact.
"""


class OpenAIParser:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6-luna",
        reasoning_effort: str = "none",
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ParseError(
                "OpenAI parser uchun loyiha dependencylarini o'rnating"
            ) from exc
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._reasoning_effort = reasoning_effort

    def parse(self, text: str, *, today: date) -> ParsedMessage:
        if not text.strip():
            raise ParseError("Bo'sh xabarni parse qilib bo'lmaydi")
        try:
            response = self._client.responses.create(
                model=self._model,
                reasoning={"effort": self._reasoning_effort},
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Current business date (Asia/Tashkent): {today.isoformat()}\n"
                            f"Message:\n{text.strip()}"
                        ),
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "financial_message",
                        "strict": True,
                        "schema": FINANCIAL_MESSAGE_SCHEMA,
                    }
                },
                max_output_tokens=2500,
                store=False,
            )
        except Exception as exc:
            raise ParseError(f"OpenAI so'rovi bajarilmadi: {exc}") from exc

        if response.status != "completed" or not response.output_text:
            reason = getattr(response, "incomplete_details", None)
            raise ParseError(f"OpenAI to'liq javob bermadi: {reason}")
        try:
            payload = json.loads(response.output_text)
            return ParsedMessage.from_dict(payload)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ParseError(f"OpenAI javobi moliyaviy sxemadan o'tmadi: {exc}") from exc


_AMOUNT_RE = re.compile(
    r"(?P<number>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>mln|million|миллион|ming|тыс(?:яч[аи])?)?\b",
    re.IGNORECASE,
)
_DATE_ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_DATE_LOCAL_RE = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](20\d{2})\b")
_NEW_CUSTOMERS_RE = re.compile(
    r"\b(\d+)\s*(?:ta\s*)?(?:yangi\s*)?(?:mijoz|klient|клиент)",
    re.IGNORECASE,
)


def _normalized(text: str) -> str:
    return (
        text.lower()
        .replace("’", "'")
        .replace("‘", "'")
        .replace("ʻ", "'")
        .replace("ё", "е")
    )


def _amount_from_clause(clause: str) -> int | None:
    match = _AMOUNT_RE.search(clause)
    if not match:
        return None
    number = float(match.group("number").replace(",", "."))
    unit = (match.group("unit") or "").lower()
    multiplier = 1
    if unit in {"mln", "million", "миллион"}:
        multiplier = 1_000_000
    elif unit.startswith(("ming", "тыс")):
        multiplier = 1_000
    return round(number * multiplier)


def _transaction_date(text: str, today: date) -> date:
    normalized = _normalized(text)
    if "kecha" in normalized or "вчера" in normalized:
        return today - timedelta(days=1)
    iso_match = _DATE_ISO_RE.search(normalized)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1))
        except ValueError:
            pass
    local_match = _DATE_LOCAL_RE.search(normalized)
    if local_match:
        day, month, year = map(int, local_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            pass
    return today


def _kind(clause: str) -> str | None:
    keyword_map = (
        ("refund", ("vazvrat", "qaytar", "возврат")),
        ("cost_of_goods", ("tan narx", "tannarx", "себестоим")),
        ("customer_payment", ("qarz to'ladi", "qarzini to'ladi", "оплата долга")),
        ("receivable", ("bizga qarz", "debitor", "дебитор")),
        ("payable", ("biz qarz", "kreditor", "кредитор")),
        ("supplier_payment", ("postavchik to'lov", "supplier payment", "поставщик")),
        ("expense", ("rasxod", "xarajat", "chiqim", "расход", "трата")),
        ("income", ("tushum", "savdo", "kirim", "prixod", "выручка", "доход")),
    )
    for kind, keywords in keyword_map:
        if any(keyword in clause for keyword in keywords):
            return kind
    return None


def _payment(amount: int, clause: str) -> tuple[str, dict[str, int]]:
    cash = any(word in clause for word in ("naqd", "налич"))
    card = any(word in clause for word in ("karta", "plastik", "карта"))
    transfer = any(
        word in clause
        for word in ("o'tkazma", "otkazma", "perevod", "перевод", "bank")
    )
    count = sum((cash, card, transfer))
    if count == 0:
        return "unknown", {"cash_uzs": 0, "card_uzs": 0, "transfer_uzs": 0}
    if count > 1:
        # A rule parser cannot safely infer multiple splits from one clause.
        return "unknown", {"cash_uzs": 0, "card_uzs": 0, "transfer_uzs": 0}
    if cash:
        return "cash", {"cash_uzs": amount, "card_uzs": 0, "transfer_uzs": 0}
    if card:
        return "card", {"cash_uzs": 0, "card_uzs": amount, "transfer_uzs": 0}
    return "transfer", {"cash_uzs": 0, "card_uzs": 0, "transfer_uzs": amount}


class RuleBasedParser:
    """Small offline parser for tests and local wiring; not a production AI fallback."""

    def parse(self, text: str, *, today: date) -> ParsedMessage:
        if not text.strip():
            raise ParseError("Bo'sh xabarni parse qilib bo'lmaydi")
        normalized = _normalized(text)
        entries: list[dict[str, Any]] = []
        missing_fields: list[str] = []

        clauses = [
            clause.strip()
            for clause in re.split(r"[,;\n]+", normalized)
            if clause.strip()
        ]
        for clause in clauses:
            kind = _kind(clause)
            amount = _amount_from_clause(clause)
            if kind and amount:
                payment_method, breakdown = _payment(amount, clause)
                entries.append(
                    {
                        "kind": kind,
                        "amount_uzs": amount,
                        "payment_method": payment_method,
                        "payment_breakdown": breakdown,
                        "cost_uzs": 0,
                        "category": None,
                        "counterparty": None,
                        "note": clause,
                    }
                )
            elif kind and amount is None:
                missing_fields.append(f"{kind}.amount_uzs")

        customer_match = _NEW_CUSTOMERS_RE.search(normalized)
        new_customer_count = int(customer_match.group(1)) if customer_match else 0
        needs_clarification = not entries or bool(missing_fields)
        question = None
        if missing_fields:
            question = "Qaysi operatsiyaning summasi qancha?"
        elif not entries:
            question = "Tushum yoki xarajat summasini aniq yozib yuborasizmi?"

        return ParsedMessage.from_dict(
            {
                "transaction_date": _transaction_date(normalized, today).isoformat(),
                "currency": "UZS",
                "entries": entries,
                "new_customer_count": new_customer_count,
                "needs_clarification": needs_clarification,
                "clarification_question": question,
                "missing_fields": missing_fields,
                "confidence": 0.65 if entries else 0.2,
            }
        )
