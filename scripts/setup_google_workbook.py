#!/usr/bin/env python3
"""Create the managed-report tabs used by Moliya Agent."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from moliya_agent.sheets import _HEADERS


REPORT_TABS = (
    "Dashboard",
    "Sozlamalar",
    "P&L",
    "Cash Flow",
    "Balance",
    "Debitor",
    "Kreditor",
)


def months(start_year: int = 2026, count: int = 60) -> list[str]:
    values = []
    year, month = start_year, 1
    for _ in range(count):
        values.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return values


def sum_kind(column: str, kind: str, month_cell: str | None = None) -> str:
    criteria = (
        f',Operatsiyalar!$C:$C,{month_cell}' if month_cell else ""
    )
    return (
        f'SUMIFS(Operatsiyalar!${column}:${column},'
        f'Operatsiyalar!$D:$D,"{kind}",'
        f'Operatsiyalar!$S:$S,"confirmed"{criteria})'
    )


def pnl_rows() -> list[list[object]]:
    rows: list[list[object]] = [
        ["P&L — foyda va zarar hisoboti"],
        ["Faqat tasdiqlangan Operatsiyalar ledgeridan avtomatik hisoblanadi."],
        [],
        ["Oy", "Tushum", "Vazvrat", "Sof tushum", "Tannarx", "Yalpi foyda", "Xarajat", "Sof foyda"],
    ]
    for row_number, month in enumerate(months(), start=5):
        month_cell = f"$A{row_number}"
        income = f"={sum_kind('E', 'income', month_cell)}"
        refund = f"={sum_kind('E', 'refund', month_cell)}"
        cogs = (
            f"={sum_kind('E', 'cost_of_goods', month_cell)}+"
            f'SUMIFS(Operatsiyalar!$I:$I,Operatsiyalar!$C:$C,{month_cell},'
            'Operatsiyalar!$S:$S,"confirmed")'
        )
        expense = f"={sum_kind('E', 'expense', month_cell)}"
        rows.append(
            [
                month,
                income,
                refund,
                f"=B{row_number}-C{row_number}",
                cogs,
                f"=D{row_number}-E{row_number}",
                expense,
                f"=F{row_number}-G{row_number}",
            ]
        )
    return rows


def cash_flow_rows() -> list[list[object]]:
    rows: list[list[object]] = [
        ["Cash Flow — pul oqimi"],
        ["Naqd, karta va o'tkazma bo'yicha tasdiqlangan real pul harakati."],
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
    for row_number, month in enumerate(months(), start=5):
        month_cell = f"$A{row_number}"
        cash_in = "+".join(sum_kind("F", kind, month_cell) for kind in incoming)
        cash_out = "+".join(sum_kind("F", kind, month_cell) for kind in outgoing)
        bank_in = "+".join(
            f"({sum_kind('G', kind, month_cell)}+{sum_kind('H', kind, month_cell)})"
            for kind in incoming
        )
        bank_out = "+".join(
            f"({sum_kind('G', kind, month_cell)}+{sum_kind('H', kind, month_cell)})"
            for kind in outgoing
        )
        opening = "Sozlamalar!$B$7+Sozlamalar!$B$8" if row_number == 5 else f"I{row_number-1}"
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


def settings_rows() -> list[list[object]]:
    return [
        ["Moliya assistent sozlamalari", "Qiymat", "Izoh"],
        ["Asosiy valyuta", "UZS", "MVP hisobot valyutasi"],
        ["Vaqt zonasi", "Asia/Tashkent", "Sana va avtomatik hisobotlar"],
        ["Hisobot boshlanish sanasi", date.today().replace(day=1).isoformat(), "Kerak bo'lsa o'zgartiring"],
        [],
        ["Boshlang'ich qoldiqlar", "", "Bir marta buxgalter bilan kiriting"],
        ["Naqd", 0, "UZS"],
        ["Karta/bank", 0, "UZS"],
        ["Debitor", 0, "UZS"],
        ["Tovar qoldig'i", 0, "UZS"],
        ["Kreditor", 0, "UZS"],
        ["Kapital", 0, "UZS"],
        [],
        ["USD kursi", 0, "Keyingi bosqichda Markaziy bankdan avtomatik olinadi"],
        ["Oy yopilgan", "", "YYYY-MM; bo'sh bo'lsa oy ochiq"],
    ]


def balance_rows() -> list[list[object]]:
    total_income = sum_kind("E", "income")
    total_refund = sum_kind("E", "refund")
    total_expense = sum_kind("E", "expense")
    total_cogs = f"{sum_kind('E', 'cost_of_goods')}+SUMIFS(Operatsiyalar!$I:$I,Operatsiyalar!$S:$S,\"confirmed\")"
    cash_in = "+".join(sum_kind("F", kind) for kind in ("income", "customer_payment"))
    cash_out = "+".join(sum_kind("F", kind) for kind in ("expense", "refund", "cost_of_goods", "supplier_payment"))
    bank_in = "+".join(f"({sum_kind('G', k)}+{sum_kind('H', k)})" for k in ("income", "customer_payment"))
    bank_out = "+".join(f"({sum_kind('G', k)}+{sum_kind('H', k)})" for k in ("expense", "refund", "cost_of_goods", "supplier_payment"))
    return [
        ["Balance — boshqaruv balansi"],
        ["Boshlang'ich qoldiq + tasdiqlangan operatsiyalar asosida."],
        [],
        ["AKTIVLAR", "Summa (UZS)"],
        ["Naqd", f"=Sozlamalar!B7+{cash_in}-{cash_out}"],
        ["Karta/bank", f"=Sozlamalar!B8+{bank_in}-{bank_out}"],
        ["Debitor", f"=Sozlamalar!B9+{sum_kind('E', 'receivable')}-{sum_kind('E', 'customer_payment')}"],
        ["Tovar qoldig'i", f"=Sozlamalar!B10-({total_cogs})"],
        ["Jami aktivlar", "=SUM(B5:B8)"],
        [],
        ["MAJBURIYATLAR", "Summa (UZS)"],
        ["Kreditor", f"=Sozlamalar!B11+{sum_kind('E', 'payable')}-{sum_kind('E', 'supplier_payment')}"],
        ["Jami majburiyatlar", "=B12"],
        [],
        ["KAPITAL", "Summa (UZS)"],
        ["Boshlang'ich kapital + jamlangan foyda", f"=Sozlamalar!B12+({total_income})-({total_refund})-({total_cogs})-({total_expense})"],
        ["Majburiyatlar + kapital", "=B13+B16"],
        ["Balans tekshiruvi", "=B9-B17"],
        ["Izoh", "0 bo'lsa balans teng. Boshlang'ich qoldiqlarni buxgalter tasdiqlashi kerak."],
    ]


def dashboard_rows() -> list[list[object]]:
    current_month = date.today().strftime("%Y-%m")
    return [
        ["Moliya Assistant — Dashboard"],
        ["Joriy oy", current_month],
        [],
        ["Ko'rsatkich", "Summa (UZS)"],
        ["Tushum", '=IFERROR(INDEX(\'P&L\'!B:B,MATCH(B2,\'P&L\'!A:A,0)),0)'],
        ["Sof tushum", '=IFERROR(INDEX(\'P&L\'!D:D,MATCH(B2,\'P&L\'!A:A,0)),0)'],
        ["Yalpi foyda", '=IFERROR(INDEX(\'P&L\'!F:F,MATCH(B2,\'P&L\'!A:A,0)),0)'],
        ["Xarajat", '=IFERROR(INDEX(\'P&L\'!G:G,MATCH(B2,\'P&L\'!A:A,0)),0)'],
        ["Sof foyda", '=IFERROR(INDEX(\'P&L\'!H:H,MATCH(B2,\'P&L\'!A:A,0)),0)'],
        ["Sof pul oqimi", '=IFERROR(INDEX(\'Cash Flow\'!D:D,MATCH(B2,\'Cash Flow\'!A:A,0)),0)'],
        ["Jami aktivlar", "=Balance!B9"],
        ["Kreditor", "=Balance!B12"],
        ["Debitor", "=Balance!B7"],
        ["Balans farqi", "=Balance!B18"],
    ]


def debt_rows(kind: str) -> list[list[object]]:
    if kind == "debtor":
        formula = (
            '=QUERY({Operatsiyalar!K2:K,ARRAYFORMULA(IF(Operatsiyalar!D2:D="receivable",'
            'Operatsiyalar!E2:E,IF(Operatsiyalar!D2:D="customer_payment",-Operatsiyalar!E2:E,0))),'
            'Operatsiyalar!S2:S},"select Col1,sum(Col2) where Col1 is not null and Col3=\'confirmed\' '
            'group by Col1 label Col1 \'Kontragent\',sum(Col2) \'Qoldiq (UZS)\'",0)'
        )
        title = "Debitor qarzdorlik"
    else:
        formula = (
            '=QUERY({Operatsiyalar!K2:K,ARRAYFORMULA(IF(Operatsiyalar!D2:D="payable",'
            'Operatsiyalar!E2:E,IF(Operatsiyalar!D2:D="supplier_payment",-Operatsiyalar!E2:E,0))),'
            'Operatsiyalar!S2:S},"select Col1,sum(Col2) where Col1 is not null and Col3=\'confirmed\' '
            'group by Col1 label Col1 \'Kontragent\',sum(Col2) \'Qoldiq (UZS)\'",0)'
        )
        title = "Kreditor qarzdorlik"
    return [[title], ["Tasdiqlangan ledgerdan kontragent bo'yicha avtomatik qoldiq."], [], [formula]]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spreadsheet-id", required=True)
    parser.add_argument("--service-account-file", type=Path, required=True)
    args = parser.parse_args()

    credentials = Credentials.from_service_account_file(
        str(args.service_account_file),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    spreadsheet_id = args.spreadsheet_id
    metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties"
    ).execute()
    titles = {item["properties"]["title"] for item in metadata.get("sheets", [])}
    requests = [
        {
            "updateSpreadsheetProperties": {
                "properties": {"locale": "en_US", "timeZone": "Asia/Tashkent"},
                "fields": "locale,timeZone",
            }
        }
    ]
    for title in ("Operatsiyalar", *REPORT_TABS):
        if title not in titles:
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
        "Dashboard": dashboard_rows(),
        "Sozlamalar": settings_rows(),
        "P&L": pnl_rows(),
        "Cash Flow": cash_flow_rows(),
        "Balance": balance_rows(),
        "Debitor": debt_rows("debtor"),
        "Kreditor": debt_rows("creditor"),
    }
    for title, rows in values.items():
        if title != "Operatsiyalar":
            service.spreadsheets().values().clear(
                spreadsheetId=spreadsheet_id, range=f"'{title}'!A:Z", body={}
            ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"'{title}'!A1",
            valueInputOption="USER_ENTERED",
            body={"values": rows},
        ).execute()

    metadata = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, fields="sheets.properties"
    ).execute()
    sheet_ids = {
        item["properties"]["title"]: item["properties"]["sheetId"]
        for item in metadata["sheets"]
    }
    format_requests = []
    for title in ("Operatsiyalar", *REPORT_TABS):
        format_requests.extend(
            [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": sheet_ids[title],
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "backgroundColor": {"red": 0.10, "green": 0.25, "blue": 0.45},
                                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                            }
                        },
                        "fields": "userEnteredFormat",
                    }
                },
                {
                    "autoResizeDimensions": {
                        "dimensions": {
                            "sheetId": sheet_ids[title],
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": 20,
                        }
                    }
                },
            ]
        )
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": format_requests}
    ).execute()
    print(json.dumps({"status": "ok", "tabs": ["Operatsiyalar", *REPORT_TABS]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
