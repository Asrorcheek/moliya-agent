from __future__ import annotations

import unittest
from datetime import date

from moliya_agent.domain import EntryKind
from moliya_agent.parser import RuleBasedParser


class RuleBasedParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = RuleBasedParser()
        self.today = date(2026, 7, 28)

    def test_parses_income_expense_and_customer_metric(self) -> None:
        parsed = self.parser.parse(
            "Bugun 2 mln tushum, 500 ming rasxod, 3 ta yangi mijoz",
            today=self.today,
        )
        self.assertEqual(parsed.transaction_date, self.today)
        self.assertEqual(len(parsed.entries), 2)
        self.assertEqual(parsed.entries[0].kind, EntryKind.INCOME)
        self.assertEqual(parsed.entries[0].amount_uzs, 2_000_000)
        self.assertEqual(parsed.entries[1].kind, EntryKind.EXPENSE)
        self.assertEqual(parsed.entries[1].amount_uzs, 500_000)
        self.assertEqual(parsed.new_customer_count, 3)
        self.assertFalse(parsed.needs_clarification)

    def test_understands_yesterday_and_cash(self) -> None:
        parsed = self.parser.parse(
            "Kecha naqd 1.5 mln tushum", today=self.today
        )
        self.assertEqual(parsed.transaction_date, date(2026, 7, 27))
        self.assertEqual(parsed.entries[0].payment_method.value, "cash")
        self.assertEqual(parsed.entries[0].payment_breakdown.cash_uzs, 1_500_000)

    def test_requires_clarification_when_no_amount(self) -> None:
        parsed = self.parser.parse("Bugun tushum bo'ldi", today=self.today)
        self.assertTrue(parsed.needs_clarification)
        self.assertIn("income.amount_uzs", parsed.missing_fields)


if __name__ == "__main__":
    unittest.main()
