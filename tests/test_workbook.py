from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from moliya_agent.workbook import (
    MANAGED_TABS,
    WorkbookInitializationError,
    initialize_workbook,
)


class WorkbookInitializationTests(unittest.TestCase):
    def test_rejects_incompatible_ledger_before_mutating_workbook(self) -> None:
        service = MagicMock()
        sheets = service.spreadsheets.return_value
        sheets.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "Operatsiyalar", "sheetId": 1}}]
        }
        sheets.values.return_value.get.return_value.execute.return_value = {
            "values": [["Unrelated data"]]
        }

        with self.assertRaises(WorkbookInitializationError):
            initialize_workbook(service, "spreadsheet-id")

        sheets.batchUpdate.assert_not_called()
        sheets.values.return_value.update.assert_not_called()

    def test_adds_only_missing_managed_tabs(self) -> None:
        service = MagicMock()
        sheets = service.spreadsheets.return_value
        sheets.get.return_value.execute.return_value = {
            "sheets": [{"properties": {"title": "Sheet1", "sheetId": 0}}]
        }

        initialize_workbook(service, "spreadsheet-id")

        requests = sheets.batchUpdate.call_args.kwargs["body"]["requests"]
        added = {
            request["addSheet"]["properties"]["title"]
            for request in requests
            if "addSheet" in request
        }
        self.assertEqual(added, set(MANAGED_TABS))
        self.assertEqual(sheets.values.return_value.update.call_count, len(MANAGED_TABS))


if __name__ == "__main__":
    unittest.main()
