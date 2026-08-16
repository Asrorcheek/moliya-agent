from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

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
            }.issubset(paths)
        )


if __name__ == "__main__":
    unittest.main()
