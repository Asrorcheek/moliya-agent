from __future__ import annotations

import threading
import unittest
from unittest.mock import MagicMock

from moliya_agent.sheets import GoogleSheetsWriter


class GoogleSheetsFinancialOverviewTests(unittest.TestCase):
    def test_formatted_month_cells_match_financial_report_period(self) -> None:
        response = {
            "valueRanges": [
                {
                    "values": [
                        [
                            "2026-08",
                            "100300000",
                            "0",
                            "100300000",
                            "76750000",
                            "23550000",
                            "10924000",
                            "12626000",
                        ]
                    ]
                },
                {
                    "values": [
                        [
                            "2026-08",
                            "100300000",
                            "9690000",
                            "90610000",
                            "21900000",
                            "340000",
                            "78400000",
                            "9350000",
                            "136770000",
                        ]
                    ]
                },
                {"values": [["Naqd", "37840000"], ["Karta/bank", "98930000"]]},
            ]
        }
        request = MagicMock()
        request.execute.return_value = response
        values = MagicMock()
        values.batchGet.return_value = request
        sheets = MagicMock()
        sheets.values.return_value = values
        service = MagicMock()
        service.spreadsheets.return_value = sheets

        writer = object.__new__(GoogleSheetsWriter)
        writer._spreadsheet_id = "spreadsheet-id"
        writer._service = service
        writer._report_cache = {}
        writer._cache_lock = threading.RLock()

        overview = writer.read_financial_overview("2026-08")

        current = overview["trend"][-1]
        self.assertEqual(current["income_uzs"], 100_300_000)
        self.assertEqual(current["expense_uzs"], 10_924_000)
        self.assertEqual(current["net_profit_uzs"], 12_626_000)
        self.assertEqual(current["net_cash_flow_uzs"], 90_610_000)
        self.assertEqual(current["ending_cash_uzs"], 136_770_000)
        self.assertEqual(overview["balance"]["cash_uzs"], 37_840_000)
        values.batchGet.assert_called_once_with(
            spreadsheetId="spreadsheet-id",
            ranges=["'P&L'!A5:H64", "'Cash Flow'!A5:I64", "'Balance'!A4:B18"],
            valueRenderOption="FORMATTED_VALUE",
        )


if __name__ == "__main__":
    unittest.main()
