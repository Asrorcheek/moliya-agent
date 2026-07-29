from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

from .domain import DraftRecord, FinancialEntry


class SheetWriteError(RuntimeError):
    pass


class SheetWriter(Protocol):
    def write_draft(
        self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime
    ) -> int: ...


class InMemorySheetWriter:
    def __init__(self) -> None:
        self.rows: dict[str, dict[str, object]] = {}

    def write_draft(
        self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime
    ) -> int:
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
    ) -> None:
        try:
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise SheetWriteError(
                "Google Sheets dependencylari o'rnatilmagan"
            ) from exc

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        if service_account_json:
            try:
                info = json.loads(service_account_json)
            except json.JSONDecodeError as exc:
                raise SheetWriteError("GOOGLE_SERVICE_ACCOUNT_JSON noto'g'ri") from exc
            credentials = Credentials.from_service_account_info(info, scopes=scopes)
        elif service_account_file:
            credentials = Credentials.from_service_account_file(
                str(service_account_file), scopes=scopes
            )
        else:
            raise SheetWriteError("Service account credential berilmagan")

        self._spreadsheet_id = spreadsheet_id
        self._service = build(
            "sheets", "v4", credentials=credentials, cache_discovery=False
        )

    @staticmethod
    def _quote_tab(title: str) -> str:
        return "'" + title.replace("'", "''") + "'"

    def _ensure_tab(self, title: str) -> None:
        metadata = (
            self._service.spreadsheets()
            .get(spreadsheetId=self._spreadsheet_id, fields="sheets.properties.title")
            .execute()
        )
        titles = {
            sheet["properties"]["title"] for sheet in metadata.get("sheets", [])
        }
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

    def write_draft(
        self, draft: DraftRecord, *, confirmed_by: str, confirmed_at: datetime
    ) -> int:
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
        except Exception as exc:
            raise SheetWriteError(f"Google Sheets yozuvi bajarilmadi: {exc}") from exc
        return len(rows)
