from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from moliya_agent.api import create_app
from moliya_agent.auth import InvalidSessionError, SessionManager
from moliya_agent.config import Settings


class SessionManagerTests(unittest.TestCase):
    def test_signed_session_round_trip_and_tamper_protection(self) -> None:
        sessions = SessionManager("test-session-secret")
        token = sessions.create(username="owner", actor_id="web-owner")
        principal = sessions.verify(token)
        self.assertEqual(principal.username, "owner")
        self.assertEqual(principal.actor_id, "web-owner")
        with self.assertRaises(InvalidSessionError):
            sessions.verify(token[:-1] + ("a" if token[-1] != "a" else "b"))


class WebRouteTests(unittest.TestCase):
    def test_required_web_routes_are_registered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = replace(
                Settings.from_env(), db_path=Path(directory) / "api.db"
            )
            paths = {route.path for route in create_app(settings).routes}
        self.assertTrue(
            {
                "/v1/session",
                "/v1/drafts",
                "/v1/drafts/{draft_id}",
                "/v1/transactions",
                "/v1/reports/dashboard",
                "/v1/audit-events",
                "/v1/settings",
                "/v1/settings/business",
                "/v1/users",
                "/v1/users/{user_id}",
                "/v1/categories",
                "/v1/categories/{category_id}",
            }.issubset(paths)
        )

    def test_settings_endpoints_require_session_and_support_crud(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = replace(
                Settings.from_env(),
                db_path=Path(directory) / "api.db",
                web_username="owner",
                web_password="safe-test-password",
                web_actor_id="web-owner",
                allowed_actors=frozenset({"web-owner"}),
                session_cookie_secure=False,
            )
            with TestClient(create_app(settings)) as client:
                self.assertEqual(client.get("/v1/settings").status_code, 401)
                login = client.post(
                    "/v1/session",
                    json={"username": "owner", "password": "safe-test-password"},
                )
                self.assertEqual(login.status_code, 200)

                initial = client.get("/v1/settings")
                self.assertEqual(initial.status_code, 200)
                self.assertEqual(len(initial.json()["categories"]), 7)
                self.assertTrue(initial.json()["users"])

                business = client.put(
                    "/v1/settings/business",
                    json={
                        "name": "Test Business",
                        "phone": "+998901234567",
                        "address": "Toshkent",
                        "timezone": "Asia/Tashkent",
                    },
                )
                self.assertEqual(business.status_code, 200)
                self.assertEqual(business.json()["business"]["name"], "Test Business")

                user = client.post(
                    "/v1/users", json={"full_name": "Test Manager", "role": "manager"}
                )
                self.assertEqual(user.status_code, 201)
                user_id = user.json()["user"]["id"]
                changed_user = client.put(
                    f"/v1/users/{user_id}",
                    json={"full_name": "Test Accountant", "role": "accountant"},
                )
                self.assertEqual(changed_user.json()["user"]["role"], "accountant")
                self.assertEqual(client.delete(f"/v1/users/{user_id}").status_code, 200)

                category = client.post(
                    "/v1/categories",
                    json={
                        "name_uz": "Aloqa",
                        "name_ru": "Связь",
                        "name_en": "Communications",
                    },
                )
                self.assertEqual(category.status_code, 201)
                category_id = category.json()["category"]["id"]
                changed_category = client.put(
                    f"/v1/categories/{category_id}",
                    json={
                        "name_uz": "Internet",
                        "name_ru": "Интернет",
                        "name_en": "Internet",
                    },
                )
                self.assertEqual(changed_category.json()["category"]["name_uz"], "Internet")
                self.assertEqual(
                    client.delete(f"/v1/categories/{category_id}").status_code, 200
                )


if __name__ == "__main__":
    unittest.main()
