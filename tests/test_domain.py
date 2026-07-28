from __future__ import annotations

import unittest

from moliya_agent.domain import DomainValidationError, FinancialEntry


class FinancialEntryTests(unittest.TestCase):
    def test_rejects_mismatched_cash_breakdown(self) -> None:
        with self.assertRaises(DomainValidationError):
            FinancialEntry.from_dict(
                {
                    "kind": "income",
                    "amount_uzs": 2_000_000,
                    "payment_method": "cash",
                    "payment_breakdown": {
                        "cash_uzs": 1_000_000,
                        "card_uzs": 0,
                        "transfer_uzs": 0,
                    },
                    "cost_uzs": 0,
                    "category": None,
                    "counterparty": None,
                    "note": None,
                }
            )

    def test_unknown_payment_requires_zero_breakdown(self) -> None:
        entry = FinancialEntry.from_dict(
            {
                "kind": "expense",
                "amount_uzs": 500_000,
                "payment_method": "unknown",
                "payment_breakdown": {
                    "cash_uzs": 0,
                    "card_uzs": 0,
                    "transfer_uzs": 0,
                },
                "cost_uzs": 0,
                "category": "ijara",
                "counterparty": None,
                "note": None,
            }
        )
        self.assertEqual(entry.amount_uzs, 500_000)


if __name__ == "__main__":
    unittest.main()
