from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from .domain import DraftRecord, FinancialEntry


class SheetWriteError(RuntimeError):
    pass


class SheetReadError(RuntimeError):
    pass


class SheetWriter(Protocol):
    def write_draft(
        self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime
    ) -> int: ...


class FinancialReportReader(Protocol):
    def read_financial_overview(
        self, month: str, *, actor_id: str | None = None
    ) -> dict[str, object]: ...


class InMemorySheetWriter:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def write_draft(self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime) -> int:
        written = 0
        for index, entry in enumerate(draft.parsed.entries):
            entry_id = f"{draft.id}:{index}"
            if entry_id in self.rows:
                continue
            self.rows[entry_id] = {
                "entry_id": entry_id,
                "date": draft.parsed.transaction_date.isoformat(),
                "entry": entry.to_dict(),
                "source_id": draft.source_id,
                "confirmed_by": confirmed_by,
                "confirmed_at": confirmed_at.isoformat(),
            }
            written += 1
        return written


_HEADERS = [
    "Entry ID",
    "Sana",
    "Oy",
    "Turi",
    "Summa (UZS)",
    "Naqd (UZS)",
    "Karta (UZS)",
    "O'tkazma (UZS)",
    "Tan narx (UZS)",
    "Kategoriya",
    "Kontragent",
    "Izoh",
    "Source ID",
    "Tasdiqlagan",
    "Tasdiqlangan vaqt",
    "Valyuta",
    "Summa (valyutada)",
    "Kurs",
    "Holat",
    "Bekor qilingan Entry ID",
]

_LEDGER_TAB = "Operatsiyalar"


class GoogleSheetsWriter:
    """Idempotent writer for the template's normalized Operatsiyalar ledger."""

    def __init__(
        self,
        *,
        spreadsheet_id: str,
        service_account_file: Path | None = None,
        service_account_json: str | None = None,
        credentials: Any | None = None,
    ) -> None:
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise SheetWriteError("Google Sheets dependencylari o'rnatilmagan") from exc

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if credentials is not None:
            resolved_credentials = credentials
        elif service_account_json:
            from google.oauth2.service_account import Credentials

            try:
                info = json.loads(service_account_json)
            except json.JSONDecodeError as exc:
                raise SheetWriteError("GOOGLE_SERVICE_ACCOUNT_JSON noto'g'ri") from exc
            resolved_credentials = Credentials.from_service_account_info(info, scopes=scopes)
        elif service_account_file:
            from google.oauth2.service_account import Credentials

            resolved_credentials = Credentials.from_service_account_file(
                str(service_account_file), scopes=scopes
            )
        else:
            raise SheetWriteError("Service account credential berilmagan")

        self._spreadsheet_id = spreadsheet_id
        self._service = build(
            "sheets", "v4", credentials=resolved_credentials, cache_discovery=False
        )
        self._report_cache: dict[str, tuple[float, dict[str, object]]] = {}
        self._cache_lock = threading.RLock()

    @staticmethod
    def _quote_tab(title: str) -> str:
        return "'" + title.replace("'", "''") + "'"

    def _ensure_tab(self, title: str) -> None:
        metadata = (
            self._service.spreadsheets()
            .get(spreadsheetId=self._spreadsheet_id, fields="sheets.properties.title")
            .execute()
        )
        titles = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}
        if title in titles:
            return
        self._service.spreadsheets().batchUpdate(
            spreadsheetId=self._spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
        ).execute()
        quoted = self._quote_tab(title)
        self._service.spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id,
            range=f"{quoted}!A1:T1",
            valueInputOption="RAW",
            body={"values": [_HEADERS]},
        ).execute()

    @staticmethod
    def _row(
        *,
        entry_id: str,
        draft: DraftRecord,
        entry: FinancialEntry,
        confirmed_by: str,
        confirmed_at: datetime,
    ) -> list[object]:
        return [
            entry_id,
            draft.parsed.transaction_date.isoformat(),
            draft.parsed.transaction_date.strftime("%Y-%m"),
            entry.kind.value,
            entry.amount_uzs,
            entry.payment_breakdown.cash_uzs,
            entry.payment_breakdown.card_uzs,
            entry.payment_breakdown.transfer_uzs,
            entry.cost_uzs,
            entry.category or "",
            entry.counterparty or "",
            entry.note or "",
            draft.source_id,
            confirmed_by,
            confirmed_at.isoformat(),
            "UZS",
            entry.amount_uzs,
            1,
            "confirmed",
            "",
        ]

    def write_draft(self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime) -> int:
        title = _LEDGER_TAB
        try:
            self._ensure_tab(title)
            quoted = self._quote_tab(title)
            existing_response = (
                self._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=self._spreadsheet_id,
                    range=f"{quoted}!A:A",
                    majorDimension="COLUMNS",
                )
                .execute()
            )
            values = existing_response.get("values", [])
            existing_ids = set(values[0][1:]) if values and values[0] else set()
            rows = []
            for index, entry in enumerate(draft.parsed.entries):
                entry_id = f"{draft.id}:{index}"
                if entry_id in existing_ids:
                    continue
                rows.append(
                    self._row(
                        entry_id=entry_id,
                        draft=draft,
                        entry=entry,
                        confirmed_by=confirmed_by,
                        confirmed_at=confirmed_at,
                    )
                )
            if not rows:
                return 0
            self._service.spreadsheets().values().append(
                spreadsheetId=self._spreadsheet_id,
                range=f"{quoted}!A:T",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"majorDimension": "ROWS", "values": rows},
            ).execute()
            with self._cache_lock:
                self._report_cache.clear()
        except Exception as exc:
            raise SheetWriteError(f"Google Sheets yozuvi bajarilmadi: {exc}") from exc
        return len(rows)

    @staticmethod
    def _number(value: object) -> int:
        if isinstance(value, bool):
            return 0
        if isinstance(value, int | float):
            return round(value)
        if isinstance(value, str):
            try:
                return round(float(value.replace(",", "")))
            except ValueError:
                return 0
        return 0

    @staticmethod
    def _months_ending_at(month: str, count: int = 6) -> list[str]:
        year, month_number = (int(part) for part in month.split("-", maxsplit=1))
        result = []
        for offset in range(count - 1, -1, -1):
            absolute = year * 12 + month_number - 1 - offset
            result.append(f"{absolute // 12:04d}-{absolute % 12 + 1:02d}")
        return result

    def read_financial_overview(
        self, month: str, *, actor_id: str | None = None
    ) -> dict[str, object]:
        with self._cache_lock:
            cached = self._report_cache.get(month)
            if cached and time.monotonic() - cached[0] < 60:
                return cached[1]
        try:
            response = (
                self._service.spreadsheets()
                .values()
                .batchGet(
                    spreadsheetId=self._spreadsheet_id,
                    ranges=["'P&L'!A5:H64", "'Cash Flow'!A5:I64", "'Balance'!A4:B18"],
                    # Month cells are formatted as YYYY-MM dates in Google Sheets.
                    # UNFORMATTED_VALUE turns them into serials (for example 46235),
                    # which cannot match the API's YYYY-MM month key.
                    valueRenderOption="FORMATTED_VALUE",
                )
                .execute()
            )
            ranges = response.get("valueRanges", [])
            if len(ranges) != 3:
                raise SheetReadError("Moliyaviy hisobot tablari topilmadi")
            pnl_by_month = {
                str(row[0]): row
                for row in ranges[0].get("values", [])
                if row and str(row[0]).strip()
            }
            cash_by_month = {
                str(row[0]): row
                for row in ranges[1].get("values", [])
                if row and str(row[0]).strip()
            }
            trend = []
            for label in self._months_ending_at(month):
                pnl = [*pnl_by_month.get(label, []), *([0] * 8)][:8]
                cash = [*cash_by_month.get(label, []), *([0] * 9)][:9]
                trend.append(
                    {
                        "month": label,
                        "income_uzs": self._number(pnl[1]),
                        "net_revenue_uzs": self._number(pnl[3]),
                        "cost_of_goods_uzs": self._number(pnl[4]),
                        "gross_profit_uzs": self._number(pnl[5]),
                        "expense_uzs": self._number(pnl[6]),
                        "net_profit_uzs": self._number(pnl[7]),
                        "cash_inflow_uzs": self._number(cash[1]),
                        "cash_outflow_uzs": self._number(cash[2]),
                        "net_cash_flow_uzs": self._number(cash[3]),
                        "ending_cash_uzs": self._number(cash[8]),
                    }
                )
            balance_values = {
                str(row[0]): self._number(row[1] if len(row) > 1 else 0)
                for row in ranges[2].get("values", [])
                if row and str(row[0]).strip()
            }
            result: dict[str, object] = {
                "source": "google_sheets",
                "month": month,
                "trend": trend,
                "balance": {
                    "cash_uzs": balance_values.get("Naqd", 0),
                    "bank_uzs": balance_values.get("Karta/bank", 0),
                    "receivables_uzs": balance_values.get("Debitor", 0),
                    "inventory_uzs": balance_values.get("Tovar qoldig'i", 0),
                    "total_assets_uzs": balance_values.get("Jami aktivlar", 0),
                    "payables_uzs": balance_values.get("Kreditor", 0),
                    "total_liabilities_uzs": balance_values.get("Jami majburiyatlar", 0),
                    "equity_uzs": balance_values.get("Boshlang'ich kapital + jamlangan foyda", 0),
                    "liabilities_and_equity_uzs": balance_values.get("Majburiyatlar + kapital", 0),
                    "difference_uzs": balance_values.get("Balans tekshiruvi", 0),
                },
            }
        except SheetReadError:
            raise
        except Exception as exc:
            raise SheetReadError(f"Google Sheets hisobotini o'qib bo'lmadi: {exc}") from exc
        with self._cache_lock:
            self._report_cache[month] = (time.monotonic(), result)
        return result


class DynamicSheetGateway:
    """Resolve the active writer per actor without restarting the service."""

    def __init__(
        self,
        resolver: Callable[[str], SheetWriter],
        *,
        default_actor_id: str,
    ) -> None:
        self._resolver = resolver
        self._default_actor_id = default_actor_id

    def write_draft(self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime) -> int:
        return self._resolver(draft.actor_id).write_draft(
            draft, confirmed_by=confirmed_by, confirmed_at=confirmed_at
        )

    def read_financial_overview(
        self, month: str, *, actor_id: str | None = None
    ) -> dict[str, object]:
        writer = self._resolver(actor_id or self._default_actor_id)
        if not isinstance(writer, GoogleSheetsWriter):
            raise SheetReadError("Google Sheets report reader ulanmagan")
        return writer.read_financial_overview(month, actor_id=actor_id)
