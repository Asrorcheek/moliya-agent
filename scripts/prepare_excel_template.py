#!/usr/bin/env python3
"""Prepare the client's Excel template for safe Moliya Agent writes.

LibreOffice must already be listening on:
uno:socket,host=127.0.0.1,port=2002;urp;StarOffice.ComponentContext
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Iterable

import uno
from com.sun.star.beans import PropertyValue


SOCKET_URL = (
    "uno:socket,host=127.0.0.1,port=2002;"
    "urp;StarOffice.ComponentContext"
)

ENTRY_KINDS = (
    "income",
    "expense",
    "refund",
    "cost_of_goods",
    "receivable",
    "payable",
    "customer_payment",
    "supplier_payment",
)
STATUSES = ("pending", "confirmed", "rejected", "reversed")
CURRENCIES = ("UZS", "USD")
PAYMENT_METHODS = ("cash", "card", "transfer", "mixed", "unknown")
CATEGORIES = (
    "Savdo tushumi",
    "Boshqa daromad",
    "Tovar tan narxi",
    "Sotuvchi komissiyasi",
    "Oylik",
    "Ijara",
    "Kommunal",
    "Marketing",
    "Soliq",
    "Ma'muriy",
    "Tijoriy",
    "Xayriya",
    "Reinvestitsiya",
    "Dividend",
    "Boshqa xarajat",
)

LEDGER_HEADERS = (
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
)

NORM_ROWS = (12, 19, 22, 30, 37, 44, 52, 58, 65, 67, 72, 74, 80, 86, 91)


def property_value(name: str, value: object) -> PropertyValue:
    item = PropertyValue()
    item.Name = name
    item.Value = value
    return item


def connect_desktop():
    local_context = uno.getComponentContext()
    resolver = local_context.ServiceManager.createInstanceWithContext(
        "com.sun.star.bridge.UnoUrlResolver", local_context
    )
    context = resolver.resolve(SOCKET_URL)
    return context.ServiceManager.createInstanceWithContext(
        "com.sun.star.frame.Desktop", context
    )


def get_or_create_sheet(sheets, name: str, index: int):
    if sheets.hasByName(name):
        return sheets.getByName(name), False
    sheets.insertNewByName(name, index)
    return sheets.getByName(name), True


def write_column(sheet, column: int, start_row: int, values: Iterable[object]) -> None:
    for offset, value in enumerate(values):
        cell = sheet.getCellByPosition(column, start_row + offset)
        if isinstance(value, (int, float)):
            cell.setValue(float(value))
        else:
            cell.setString(str(value))


def style_header(cell_range, background: int = 0x1F4E78) -> None:
    cell_range.CellBackColor = background
    cell_range.CharColor = 0xFFFFFF
    cell_range.CharWeight = 150.0
    cell_range.HoriJustify = uno.Enum(
        "com.sun.star.table.CellHoriJustify", "CENTER"
    )
    cell_range.VertJustify = uno.Enum(
        "com.sun.star.table.CellVertJustify", "CENTER"
    )
    cell_range.IsTextWrapped = True


def add_list_validation(cell_range, values: tuple[str, ...], title: str) -> None:
    validation = cell_range.Validation
    validation.Type = uno.Enum("com.sun.star.sheet.ValidationType", "LIST")
    validation.Formula1 = '"' + ";".join(values) + '"'
    validation.ShowList = 1
    validation.ShowErrorMessage = True
    validation.ErrorTitle = "Noto'g'ri qiymat"
    validation.ErrorMessage = f"{title} ro'yxatdan tanlanishi kerak."
    cell_range.Validation = validation


def set_number_format(document, cell_range, code: str) -> None:
    locale = uno.createUnoStruct("com.sun.star.lang.Locale")
    locale.Language = "uz"
    locale.Country = "UZ"
    formats = document.getNumberFormats()
    key = formats.queryKey(code, locale, True)
    if key == -1:
        key = formats.addNew(code, locale)
    cell_range.NumberFormat = key


def configure_settings_sheet(document, sheet, pnl_sheet, *, created: bool) -> None:
    if created:
        sheet.getCellRangeByName("A1:N40").clearContents(1023)
    sheet.getCellRangeByName("A1:N1").merge(False)
    sheet.getCellRangeByName("A1:E1").merge(True)
    sheet.getCellRangeByName("A1").setString("Moliya AI Agent — Sozlamalar")
    style_header(sheet.getCellRangeByName("A1:N1"), 0x17365D)
    sheet.getRows().getByIndex(0).Height = 900

    settings = (
        ("Asosiy valyuta", "UZS"),
        ("USD kursi (UZS)", 0),
        ("Vaqt zonasi", "Asia/Tashkent (UTC+5)"),
        ("Hisobot yili", 2026),
        ("Hisobot oyi", 7),
        ("Foydalanuvchilar soni", 3),
    )
    write_column(sheet, 0, 2, (row[0] for row in settings))
    if created:
        write_column(sheet, 1, 2, (row[1] for row in settings))
    sheet.getCellRangeByName("A3:A8").CharWeight = 150.0
    sheet.getCellRangeByName("A3:B8").CellBackColor = 0xEAF2F8
    sheet.getCellRangeByName("A10").setString("Hisobot davri")
    sheet.getCellRangeByName("B10").setFormula(
        '=TEXT(DATE(B6;B7;1);"YYYY-MM")'
    )
    sheet.getCellRangeByName("A12").setString("Muhim qoida")
    sheet.getCellRangeByName("B12:N12").merge(True)
    sheet.getCellRangeByName("B12").setString(
        "USD kursi 0 bo'lsa agent USD operatsiyasini tasdiqlamasligi kerak. "
        "Qarz undirish daromad emas, yetkazib beruvchiga qarz to'lovi esa xarajat emas."
    )
    sheet.getCellRangeByName("A12:N12").CellBackColor = 0xFFF2CC
    sheet.getCellRangeByName("A12:N12").IsTextWrapped = True

    labels = (
        (3, "P&L kategoriyasi", "Norma"),
        (6, "Operatsiya turlari", ""),
        (8, "Valyutalar", ""),
        (10, "Holatlar", ""),
        (12, "To'lov turlari", ""),
    )
    for column, first, second in labels:
        sheet.getCellByPosition(column, 1).setString(first)
        sheet.getCellByPosition(column + 1, 1).setString(second)
        style_header(
            sheet.getCellRangeByPosition(column, 1, column + 1, 1),
            0x548235,
        )

    norm_labels = [pnl_sheet.getCellRangeByName(f"B{row}").getString() for row in NORM_ROWS]
    write_column(sheet, 3, 2, norm_labels)
    if created:
        write_column(sheet, 4, 2, (0 for _ in norm_labels))
    write_column(sheet, 6, 2, ENTRY_KINDS)
    write_column(sheet, 8, 2, CURRENCIES)
    write_column(sheet, 10, 2, STATUSES)
    write_column(sheet, 12, 2, PAYMENT_METHODS)

    sheet.getCellRangeByName("D20").setString("Kategoriyalar")
    style_header(sheet.getCellRangeByName("D20:E20"), 0x548235)
    if created:
        write_column(sheet, 3, 20, CATEGORIES)

    user_headers = ("Foydalanuvchi", "Telegram ID", "Rol")
    for column, header in enumerate(user_headers):
        sheet.getCellByPosition(column, 15).setString(header)
    style_header(sheet.getCellRangeByName("A16:C16"), 0x548235)
    for index in range(3):
        user_cell = sheet.getCellByPosition(0, 16 + index)
        if created or user_cell.getString() in {"", "Telegram ID", "Rol"}:
            user_cell.setString(f"Foydalanuvchi {index + 1}")
        role_cell = sheet.getCellByPosition(2, 16 + index)
        if created or not role_cell.getString():
            role_cell.setString("Belgilanmagan")

    widths = {
        0: 4600,
        1: 5200,
        2: 3000,
        3: 9000,
        4: 2600,
        6: 4200,
        8: 2600,
        10: 3000,
        12: 3200,
    }
    for column, width in widths.items():
        sheet.getColumns().getByIndex(column).Width = width
    sheet.TabColor = 0x548235


def configure_ledger_sheet(document, sheet) -> None:
    for column, header in enumerate(LEDGER_HEADERS):
        sheet.getCellByPosition(column, 0).setString(header)
    style_header(sheet.getCellRangeByName("A1:T1"))
    sheet.getRows().getByIndex(0).Height = 1100

    widths = (
        4300,
        2800,
        2500,
        3600,
        3300,
        3000,
        3000,
        3300,
        3300,
        4600,
        4600,
        6400,
        4600,
        3600,
        5000,
        2400,
        3600,
        2600,
        2800,
        5000,
    )
    for column, width in enumerate(widths):
        sheet.getColumns().getByIndex(column).Width = width

    set_number_format(document, sheet.getCellRangeByName("E2:I5000"), "#,##0")
    set_number_format(document, sheet.getCellRangeByName("Q2:R5000"), "#,##0.00")
    add_list_validation(sheet.getCellRangeByName("D2:D5000"), ENTRY_KINDS, "Turi")
    add_list_validation(sheet.getCellRangeByName("J2:J5000"), CATEGORIES, "Kategoriya")
    add_list_validation(sheet.getCellRangeByName("P2:P5000"), CURRENCIES, "Valyuta")
    add_list_validation(sheet.getCellRangeByName("S2:S5000"), STATUSES, "Holat")

    database_ranges = document.DatabaseRanges
    filter_name = "MoliyaOperatsiyalarFilter"
    if database_ranges.hasByName(filter_name):
        database_ranges.removeByName(filter_name)
    database_ranges.addNewByName(
        filter_name, sheet.getCellRangeByName("A1:T5000").getRangeAddress()
    )
    database_range = database_ranges.getByName(filter_name)
    database_range.AutoFilter = True
    sheet.TabColor = 0x1F4E78


def repair_template_formulas(sheets) -> None:
    settings = sheets.getByName("Sozlamalar")
    reference = sheets.getByName("Справочник")
    pnl = sheets.getByName("P&L ")
    cash_flow = sheets.getByName("Cash Flow ")
    debt = sheets.getByName("Qarzdorlik ")

    reference.getCellRangeByName("S1").setFormula("=$Sozlamalar.B4")
    reference.getCellRangeByName("S1").NumberFormat = settings.getCellRangeByName(
        "B4"
    ).NumberFormat

    last_norm_row = 2 + len(NORM_ROWS)
    for row in NORM_ROWS:
        pnl.getCellRangeByName(f"F{row}").setFormula(
            f"=IFERROR(VLOOKUP(B{row};$Sozlamalar.$D$3:$E${last_norm_row};2;0);0)"
        )

    pnl.getCellRangeByName("Q4").setFormula(
        '=SUMIFS($Operatsiyalar.$E$2:$E$5000;'
        '$Operatsiyalar.$D$2:$D$5000;"income";'
        '$Operatsiyalar.$C$2:$C$5000;$Sozlamalar.$B$10)'
    )
    pnl.getCellRangeByName("Q5").setFormula(
        '=SUMIFS($Operatsiyalar.$I$2:$I$5000;'
        '$Operatsiyalar.$D$2:$D$5000;"income";'
        '$Operatsiyalar.$C$2:$C$5000;$Sozlamalar.$B$10)'
    )
    pnl.getCellRangeByName("Q6").setFormula("=Q4-Q5")
    category_rows = {
        7: "Sotuvchi komissiyasi",
        8: "Oylik",
        9: "Ma'muriy",
        10: "Tijoriy",
    }
    for row, category in category_rows.items():
        pnl.getCellRangeByName(f"Q{row}").setFormula(
            '=SUMIFS($Operatsiyalar.$E$2:$E$5000;'
            '$Operatsiyalar.$D$2:$D$5000;"expense";'
            f'$Operatsiyalar.$J$2:$J$5000;"{category}";'
            '$Operatsiyalar.$C$2:$C$5000;$Sozlamalar.$B$10)'
        )
    pnl.getCellRangeByName("Q11").setFormula("=Q6-Q7-Q8-Q9-Q10")
    pnl.getCellRangeByName("Q12").setValue(0)
    pnl.getCellRangeByName("Q13").setValue(0)
    pnl.getCellRangeByName("Q14").setFormula("=Q11")
    pnl.getCellRangeByName("R4").setValue(1)
    pnl.getCellRangeByName("R5").setFormula("=IFERROR(R4-R6;0)")
    for row in range(6, 15):
        pnl.getCellRangeByName(f"R{row}").setFormula(
            f"=IFERROR(Q{row}/Q4;0)"
        )

    inflow_types = ("income", "customer_payment")
    outflow_types = ("expense", "refund", "cost_of_goods", "supplier_payment")
    for inflow_cell, outflow_cell, ledger_column in (
        ("G3", "H3", "F"),
        ("K3", "L3", "G"),
        ("O3", "P3", "H"),
    ):
        inflow_formula = "+".join(
            (
                f'SUMIFS($Operatsiyalar.${ledger_column}$2:${ledger_column}$5000;'
                f'$Operatsiyalar.$D$2:$D$5000;"{kind}";'
                '$Operatsiyalar.$C$2:$C$5000;$Sozlamalar.$B$10)'
            )
            for kind in inflow_types
        )
        outflow_formula = "+".join(
            (
                f'SUMIFS($Operatsiyalar.${ledger_column}$2:${ledger_column}$5000;'
                f'$Operatsiyalar.$D$2:$D$5000;"{kind}";'
                '$Operatsiyalar.$C$2:$C$5000;$Sozlamalar.$B$10)'
            )
            for kind in outflow_types
        )
        cash_flow.getCellRangeByName(inflow_cell).setFormula("=" + inflow_formula)
        cash_flow.getCellRangeByName(outflow_cell).setFormula("=" + outflow_formula)
    cash_flow.getCellRangeByName("R2").setFormula("=G3+K3+O3")
    cash_flow.getCellRangeByName("R3").setFormula("=H3+L3+P3")

    debt.getCellRangeByName("N1367").setString("")
    settings.getCellRangeByName("A14").setString("Texnik holat")
    settings.getCellRangeByName("B14").setString(
        "Tashqi IMPORTRANGE olib tashlandi; P&L va Cash Flow "
        "Operatsiyalar varag'iga ulandi."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", help="Path to the .xlsx working copy")
    args = parser.parse_args()

    workbook_path = os.path.abspath(args.workbook)
    desktop = connect_desktop()
    document = desktop.loadComponentFromURL(
        uno.systemPathToFileUrl(workbook_path),
        "_blank",
        0,
        (
            property_value("Hidden", True),
            property_value("ReadOnly", False),
        ),
    )
    if document is None:
        raise RuntimeError(f"Workbook could not be loaded: {workbook_path}")

    try:
        sheets = document.getSheets()
        settings, settings_created = get_or_create_sheet(sheets, "Sozlamalar", 0)
        ledger, _ledger_created = get_or_create_sheet(sheets, "Operatsiyalar", 1)
        pnl = sheets.getByName("P&L ")
        configure_settings_sheet(
            document, settings, pnl, created=settings_created
        )
        configure_ledger_sheet(document, ledger)
        repair_template_formulas(sheets)

        for hidden_name in (
            "Справочник",
            "Kassa - Iyul",
            "Sotuv + Kunlik Kassa , Aprel ",
            "Fiksa + Arenda , Aprel ",
            "Sotuv Kunlik + Kassa , Mart ",
            "Zarplata + Arenda Mart ",
        ):
            sheets.getByName(hidden_name).IsVisible = False

        controller = document.getCurrentController()
        controller.setActiveSheet(ledger)
        controller.freezeAtPosition(0, 1)
        document.enableAutomaticCalculation(True)
        document.calculateAll()
        document.store()
        print(f"Prepared workbook: {workbook_path}")
        print(f"Sheets: {len(sheets.getElementNames())}")
    finally:
        document.close(True)


if __name__ == "__main__":
    main()
