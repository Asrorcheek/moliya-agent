from __future__ import annotations

from datetime import date
from typing import Any

from .sheets import _HEADERS


class WorkbookInitializationError(RuntimeError):
    pass


MANAGED_TABS = ("Operatsiyalar", "Dashboard", "Sozlamalar", "P&L", "Cash Flow", "Balance")


def _months(count: int = 60) -> list[str]:
    year, month = date.today().year, 1
    values = []
    for _ in range(count):
        values.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return values


def _sum_kind(column: str, kind: str, month_cell: str | None = None) -> str:
    criteria = f",Operatsiyalar!$C:$C,{month_cell}" if month_cell else ""
    return (
        f'SUMIFS(Operatsiyalar!${column}:${column},Operatsiyalar!$D:$D,"{kind}",'
        f'Operatsiyalar!$S:$S,"confirmed"{criteria})'
    )


def _pnl_rows() -> list[list[object]]:
    rows: list[list[object]] = [
        ["P&L — foyda va zarar hisoboti"],
        ["Tasdiqlangan Operatsiyalar ledgeridan avtomatik hisoblanadi."],
        [],
        ["Oy", "Tushum", "Vazvrat", "Sof tushum", "Tannarx", "Yalpi foyda", "Xarajat", "Sof foyda"],
    ]
    for row_number, month in enumerate(_months(), start=5):
        cell = f"$A{row_number}"
        rows.append(
            [
                month,
                f"={_sum_kind('E', 'income', cell)}",
                f"={_sum_kind('E', 'refund', cell)}",
                f"=B{row_number}-C{row_number}",
                (
                    f"={_sum_kind('E', 'cost_of_goods', cell)}+"
                    f"SUMIFS(Operatsiyalar!$I:$I,Operatsiyalar!$C:$C,{cell},"
                    'Operatsiyalar!$S:$S,"confirmed")'
                ),
                f"=D{row_number}-E{row_number}",
                f"={_sum_kind('E', 'expense', cell)}",
                f"=F{row_number}-G{row_number}",
            ]
        )
    return rows


def _cash_flow_rows() -> list[list[object]]:
    rows: list[list[object]] = [
        ["Cash Flow — pul oqimi"],
        ["Naqd, karta va o'tkazma bo'yicha real pul harakati."],
        [],
        [
            "Oy",
            "Kirim",
            "Chiqim",
            "Sof oqim",
            "Naqd kirim",
            "Naqd chiqim",
            "Bank kirim",
            "Bank chiqim",
            "Yakuniy qoldiq",
        ],
    ]
    incoming = ("income", "customer_payment")
    outgoing = ("expense", "refund", "cost_of_goods", "supplier_payment")
    for row_number, month in enumerate(_months(), start=5):
        cell = f"$A{row_number}"
        cash_in = "+".join(_sum_kind("F", kind, cell) for kind in incoming)
        cash_out = "+".join(_sum_kind("F", kind, cell) for kind in outgoing)
        bank_in = "+".join(
            f"({_sum_kind('G', kind, cell)}+{_sum_kind('H', kind, cell)})" for kind in incoming
        )
        bank_out = "+".join(
            f"({_sum_kind('G', kind, cell)}+{_sum_kind('H', kind, cell)})" for kind in outgoing
        )
        opening = "Sozlamalar!$B$7+Sozlamalar!$B$8" if row_number == 5 else f"I{row_number - 1}"
        rows.append(
            [
                month,
                f"=E{row_number}+G{row_number}",
                f"=F{row_number}+H{row_number}",
                f"=B{row_number}-C{row_number}",
                f"={cash_in}",
                f"={cash_out}",
                f"={bank_in}",
                f"={bank_out}",
                f"={opening}+D{row_number}",
            ]
        )
    return rows


def _settings_rows() -> list[list[object]]:
    return [
        ["Moliya assistent sozlamalari", "Qiymat", "Izoh"],
        ["Asosiy valyuta", "UZS", "MVP hisobot valyutasi"],
        ["Vaqt zonasi", "Asia/Tashkent", "Sana va hisobotlar"],
        ["Hisobot boshlanish sanasi", date.today().replace(day=1).isoformat(), ""],
        [],
        ["Boshlang'ich qoldiqlar", "", "Bir marta buxgalter bilan kiriting"],
        ["Naqd", 0, "UZS"],
        ["Karta/bank", 0, "UZS"],
        ["Debitor", 0, "UZS"],
        ["Tovar qoldig'i", 0, "UZS"],
        ["Kreditor", 0, "UZS"],
        ["Kapital", 0, "UZS"],
    ]


def _balance_rows() -> list[list[object]]:
    income = _sum_kind("E", "income")
    refund = _sum_kind("E", "refund")
    expense = _sum_kind("E", "expense")
    cogs = (
        f"{_sum_kind('E', 'cost_of_goods')}+"
        'SUMIFS(Operatsiyalar!$I:$I,Operatsiyalar!$S:$S,"confirmed")'
    )
    cash_in = "+".join(_sum_kind("F", kind) for kind in ("income", "customer_payment"))
    cash_out = "+".join(
        _sum_kind("F", kind) for kind in ("expense", "refund", "cost_of_goods", "supplier_payment")
    )
    bank_in = "+".join(
        f"({_sum_kind('G', kind)}+{_sum_kind('H', kind)})"
        for kind in ("income", "customer_payment")
    )
    bank_out = "+".join(
        f"({_sum_kind('G', kind)}+{_sum_kind('H', kind)})"
        for kind in ("expense", "refund", "cost_of_goods", "supplier_payment")
    )
    return [
        ["Balance — boshqaruv balansi"],
        ["Boshlang'ich qoldiq + tasdiqlangan operatsiyalar asosida."],
        [],
        ["AKTIVLAR", "Summa (UZS)"],
        ["Naqd", f"=Sozlamalar!B7+{cash_in}-{cash_out}"],
        ["Karta/bank", f"=Sozlamalar!B8+{bank_in}-{bank_out}"],
        [
            "Debitor",
            f"=Sozlamalar!B9+{_sum_kind('E', 'receivable')}-{_sum_kind('E', 'customer_payment')}",
        ],
        ["Tovar qoldig'i", f"=Sozlamalar!B10-({cogs})"],
        ["Jami aktivlar", "=SUM(B5:B8)"],
        [],
        ["MAJBURIYATLAR", "Summa (UZS)"],
        [
            "Kreditor",
            f"=Sozlamalar!B11+{_sum_kind('E', 'payable')}-{_sum_kind('E', 'supplier_payment')}",
        ],
        ["Jami majburiyatlar", "=B12"],
        [],
        ["KAPITAL", "Summa (UZS)"],
        [
            "Boshlang'ich kapital + jamlangan foyda",
            f"=Sozlamalar!B12+({income})-({refund})-({cogs})-({expense})",
        ],
        ["Majburiyatlar + kapital", "=B13+B16"],
        ["Balans tekshiruvi", "=B9-B17"],
    ]


def _dashboard_rows() -> list[list[object]]:
    return [
        ["Moliya Agent — Dashboard"],
        ["Joriy oy", date.today().strftime("%Y-%m")],
        [],
        ["Ko'rsatkich", "Summa (UZS)"],
        ["Tushum", "=IFERROR(INDEX('P&L'!B:B,MATCH(B2,'P&L'!A:A,0)),0)"],
        ["Sof foyda", "=IFERROR(INDEX('P&L'!H:H,MATCH(B2,'P&L'!A:A,0)),0)"],
        ["Sof pul oqimi", "=IFERROR(INDEX('Cash Flow'!D:D,MATCH(B2,'Cash Flow'!A:A,0)),0)"],
        ["Jami aktivlar", "=Balance!B9"],
    ]


def initialize_workbook(service: Any, spreadsheet_id: str) -> None:
    """Add only missing managed tabs; never clear an existing workbook."""
    metadata = (
        service.spreadsheets()
        .get(spreadsheetId=spreadsheet_id, fields="sheets.properties")
        .execute()
    )
    existing = {
        item["properties"]["title"]: item["properties"]["sheetId"]
        for item in metadata.get("sheets", [])
    }
    ledger = []
    if "Operatsiyalar" in existing:
        ledger = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range="'Operatsiyalar'!A1:T1")
            .execute()
            .get("values", [])
        )
        if ledger and ledger[0] and ledger[0][0] != _HEADERS[0]:
            raise WorkbookInitializationError(
                "Operatsiyalar tabi mavjud, lekin Moliya Agent formatida emas"
            )
    created = [title for title in MANAGED_TABS if title not in existing]
    requests: list[dict[str, object]] = [
        {
            "updateSpreadsheetProperties": {
                "properties": {"locale": "en_US", "timeZone": "Asia/Tashkent"},
                "fields": "locale,timeZone",
            }
        }
    ]
    for title in created:
        requests.append(
            {
                "addSheet": {
                    "properties": {
                        "title": title,
                        "gridProperties": {
                            "rowCount": 1000,
                            "columnCount": 20,
                            "frozenRowCount": 1,
                        },
                    }
                }
            }
        )
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

    values = {
        "Operatsiyalar": [_HEADERS],
        "Dashboard": _dashboard_rows(),
        "Sozlamalar": _settings_rows(),
        "P&L": _pnl_rows(),
        "Cash Flow": _cash_flow_rows(),
        "Balance": _balance_rows(),
    }
    for title in created:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": values[title]},
        ).execute()
    if "Operatsiyalar" not in created and not ledger:
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="'Operatsiyalar'!A1",
            valueInputOption="RAW",
            body={"values": [_HEADERS]},
        ).execute()
