#!/usr/bin/env python3
"""Run accounting assertions against a disposable prepared workbook copy."""

from __future__ import annotations

import argparse
import os

import uno

from prepare_excel_template import SOCKET_URL, connect_desktop, property_value


def assert_amount(label: str, actual: float, expected: float) -> None:
    if abs(actual - expected) > 0.01:
        raise AssertionError(f"{label}: expected {expected}, received {actual}")
    print(f"OK {label}: {actual:,.0f}")


def write_row(sheet, row_number: int, values: list[object]) -> None:
    for column, value in enumerate(values):
        cell = sheet.getCellByPosition(column, row_number - 1)
        if isinstance(value, (int, float)):
            cell.setValue(float(value))
        else:
            cell.setString(str(value))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook")
    args = parser.parse_args()

    desktop = connect_desktop()
    document = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(os.path.abspath(args.workbook)),
        "_blank",
        0,
        (
            property_value("Hidden", True),
            property_value("ReadOnly", False),
        ),
    )
    if document is None:
        raise RuntimeError("Test workbook could not be loaded")

    try:
        sheets = document.getSheets()
        ledger = sheets.getByName("Operatsiyalar")
        pnl = sheets.getByName("P&L ")
        cash_flow = sheets.getByName("Cash Flow ")

        rows = (
            # Income with an attached cost.
            [
                "test:income",
                "2026-07-28",
                "2026-07",
                "income",
                2_000_000,
                2_000_000,
                0,
                0,
                500_000,
                "Savdo tushumi",
                "Test mijoz",
                "Test savdo",
                "test:1",
                "owner",
                "2026-07-28T12:00:00+05:00",
                "UZS",
                2_000_000,
                1,
                "confirmed",
                "",
            ],
            # Administrative expense.
            [
                "test:expense",
                "2026-07-28",
                "2026-07",
                "expense",
                300_000,
                300_000,
                0,
                0,
                0,
                "Ma'muriy",
                "",
                "Test xarajat",
                "test:2",
                "owner",
                "2026-07-28T12:01:00+05:00",
                "UZS",
                300_000,
                1,
                "confirmed",
                "",
            ],
            # Debt collection affects cash flow but not P&L revenue.
            [
                "test:customer-payment",
                "2026-07-28",
                "2026-07",
                "customer_payment",
                1_000_000,
                1_000_000,
                0,
                0,
                0,
                "",
                "Qarzdor mijoz",
                "",
                "test:3",
                "owner",
                "2026-07-28T12:02:00+05:00",
                "UZS",
                1_000_000,
                1,
                "confirmed",
                "",
            ],
            # Supplier debt payment affects cash flow but not P&L expense.
            [
                "test:supplier-payment",
                "2026-07-28",
                "2026-07",
                "supplier_payment",
                400_000,
                400_000,
                0,
                0,
                0,
                "",
                "Test yetkazib beruvchi",
                "",
                "test:4",
                "owner",
                "2026-07-28T12:03:00+05:00",
                "UZS",
                400_000,
                1,
                "confirmed",
                "",
            ],
        )
        for offset, row in enumerate(rows, start=2):
            write_row(ledger, offset, row)

        document.calculateAll()
        assert_amount("P&L revenue", pnl.getCellRangeByName("Q4").getValue(), 2_000_000)
        assert_amount("P&L cost", pnl.getCellRangeByName("Q5").getValue(), 500_000)
        assert_amount("P&L gross profit", pnl.getCellRangeByName("Q6").getValue(), 1_500_000)
        assert_amount("P&L admin expense", pnl.getCellRangeByName("Q9").getValue(), 300_000)
        assert_amount("P&L net profit", pnl.getCellRangeByName("Q14").getValue(), 1_200_000)
        assert_amount("Cash inflow", cash_flow.getCellRangeByName("G3").getValue(), 3_000_000)
        assert_amount("Cash outflow", cash_flow.getCellRangeByName("H3").getValue(), 700_000)
        print(f"UNO endpoint: {SOCKET_URL}")
    finally:
        document.setModified(False)
        document.close(True)


if __name__ == "__main__":
    main()
