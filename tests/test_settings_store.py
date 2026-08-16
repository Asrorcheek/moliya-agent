from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from moliya_agent.settings_store import SettingsConflictError, SQLiteSettingsStore


class SettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = SQLiteSettingsStore(Path(self.directory.name) / "settings.db")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_defaults_and_business_profile_persist(self) -> None:
        profile = self.store.get_business("actor-1", "admin")
        self.assertEqual(profile["currency"], "UZS")
        self.assertEqual(profile["timezone"], "Asia/Tashkent")
        updated = self.store.update_business(
            "actor-1",
            "admin",
            name="Asror Business",
            phone="+998901234567",
            address="Toshkent",
            timezone="Asia/Tashkent",
        )
        self.assertEqual(updated["name"], "Asror Business")
        reopened = SQLiteSettingsStore(Path(self.directory.name) / "settings.db")
        self.assertEqual(reopened.get_business("actor-1", "admin")["phone"], "+998901234567")

    def test_team_member_crud_keeps_one_owner(self) -> None:
        users = self.store.list_members("actor-1", "admin")
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["role"], "owner")
        with self.assertRaises(SettingsConflictError):
            self.store.delete_member("actor-1", str(users[0]["id"]))

        member = self.store.create_member(
            "actor-1", "admin", full_name="Manager One", role="manager"
        )
        changed = self.store.update_member(
            "actor-1",
            str(member["id"]),
            full_name="Accountant One",
            role="accountant",
        )
        self.assertEqual(changed["role"], "accountant")
        self.store.delete_member("actor-1", str(member["id"]))
        self.assertEqual(len(self.store.list_members("actor-1", "admin")), 1)

    def test_custom_categories_are_isolated_and_crud_works(self) -> None:
        defaults = self.store.list_categories("actor-1", "admin")
        self.assertEqual(len(defaults), 7)
        created = self.store.create_category(
            "actor-1",
            "admin",
            name_uz="Internet",
            name_ru="Интернет",
            name_en="Internet",
        )
        changed = self.store.update_category(
            "actor-1",
            str(created["id"]),
            name_uz="Aloqa",
            name_ru="Связь",
            name_en="Communications",
        )
        self.assertEqual(changed["name_uz"], "Aloqa")
        self.assertEqual(len(self.store.list_categories("actor-2", "other")), 7)
        self.store.delete_category("actor-1", str(created["id"]))
        self.assertEqual(len(self.store.list_categories("actor-1", "admin")), 7)


if __name__ == "__main__":
    unittest.main()
