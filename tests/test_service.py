from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from moliya_agent.domain import DraftStatus
from moliya_agent.parser import RuleBasedParser
from moliya_agent.repository import SQLiteDraftRepository
from moliya_agent.service import InvalidTransitionError, MoliyaService
from moliya_agent.sheets import InMemorySheetWriter


class MoliyaServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = SQLiteDraftRepository(
            Path(self.temp_dir.name) / "moliya.db"
        )
        self.writer = InMemorySheetWriter()
        self.service = MoliyaService(
            repository=self.repository,
            parser=RuleBasedParser(),
            sheet_writer=self.writer,
            allowed_actors=frozenset({"owner"}),
        )
        self.received_at = datetime(
            2026, 7, 28, 12, 0, tzinfo=ZoneInfo("Asia/Tashkent")
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _draft(self, source_id: str = "telegram:100") -> object:
        return self.service.create_draft(
            actor_id="owner",
            source_id=source_id,
            text="2 mln tushum, 500 ming xarajat",
            received_at=self.received_at,
        )

    def test_duplicate_source_returns_same_draft(self) -> None:
        first = self._draft()
        second = self._draft()
        self.assertEqual(first.id, second.id)

    def test_confirm_writes_once(self) -> None:
        draft = self._draft()
        first = self.service.confirm(actor_id="owner", draft_id=draft.id)
        second = self.service.confirm(actor_id="owner", draft_id=draft.id)

        self.assertEqual(first.draft.status, DraftStatus.CONFIRMED)
        self.assertEqual(first.written_rows, 2)
        self.assertFalse(first.already_confirmed)
        self.assertEqual(second.written_rows, 0)
        self.assertTrue(second.already_confirmed)
        self.assertEqual(len(self.writer.rows), 2)

    def test_rejected_draft_cannot_be_confirmed(self) -> None:
        draft = self._draft()
        rejected = self.service.reject(actor_id="owner", draft_id=draft.id)
        self.assertEqual(rejected.status, DraftStatus.REJECTED)
        with self.assertRaises(InvalidTransitionError):
            self.service.confirm(actor_id="owner", draft_id=draft.id)

    def test_monthly_report_uses_confirmed_entries_only(self) -> None:
        confirmed = self._draft("telegram:confirmed")
        self.service.confirm(actor_id="owner", draft_id=confirmed.id)
        self._draft("telegram:pending")

        report = self.service.monthly_report(actor_id="owner", month="2026-07")
        self.assertEqual(report["income_uzs"], 2_000_000)
        self.assertEqual(report["expense_uzs"], 500_000)
        self.assertEqual(report["net_profit_uzs"], 1_500_000)

    def test_debt_collection_is_not_counted_as_new_income(self) -> None:
        draft = self.service.create_draft(
            actor_id="owner",
            source_id="telegram:debt-payment",
            text="Mijoz qarzini to'ladi 1 mln",
            received_at=self.received_at,
        )
        self.service.confirm(actor_id="owner", draft_id=draft.id)

        report = self.service.monthly_report(actor_id="owner", month="2026-07")
        self.assertEqual(report["income_uzs"], 0)
        self.assertEqual(report["net_profit_uzs"], 0)


if __name__ == "__main__":
    unittest.main()
