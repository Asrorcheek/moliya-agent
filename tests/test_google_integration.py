from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from moliya_agent.config import Settings
from moliya_agent.google_integration import GoogleIntegrationManager
from moliya_agent.settings_store import SQLiteSettingsStore


class _Credentials:
    refresh_token = "test-refresh-token"
    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/drive.file",
    ]


class _Flow:
    def __init__(self, state: str, code_verifier: str) -> None:
        self.state = state
        self.code_verifier = code_verifier
        self.credentials = _Credentials()
        self.redirect_uri = ""

    def authorization_url(self, **_kwargs: object) -> tuple[str, str]:
        return f"https://accounts.example/authorize?state={self.state}", self.state

    def fetch_token(self, *, code: str) -> None:
        if code != "test-code":
            raise AssertionError("unexpected authorization code")


class _UserInfoResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, str]:
        return {"email": "owner@example.com"}


class _AuthorizedSession:
    def __init__(self, _credentials: object) -> None:
        pass

    def get(self, _url: str, *, timeout: int) -> _UserInfoResponse:
        if timeout != 15:
            raise AssertionError("unexpected timeout")
        return _UserInfoResponse()


class GoogleIntegrationTests(unittest.TestCase):
    def test_oauth_callback_reuses_encrypted_pkce_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings = replace(
                Settings.from_env(),
                db_path=Path(directory) / "oauth.db",
                sheet_mode="memory",
                google_oauth_client_id="client.apps.googleusercontent.com",
                google_oauth_client_secret="test-secret",
                google_oauth_redirect_uri="https://example.com/callback",
            )
            store = SQLiteSettingsStore(settings.db_path)
            store.ensure_owner_login(
                "web-owner",
                "Owner",
                email="owner@example.com",
                password="safe-test-password",
            )
            owner_id = str(store.list_members("web-owner", "owner@example.com")[0]["id"])
            manager = GoogleIntegrationManager(settings, store)
            verifier_calls: list[str] = []

            def build_flow(_config: object, **kwargs: object) -> _Flow:
                self.assertFalse(kwargs["autogenerate_code_verifier"])
                verifier = str(kwargs["code_verifier"])
                verifier_calls.append(verifier)
                return _Flow(str(kwargs["state"]), verifier)

            with (
                patch(
                    "moliya_agent.google_integration.Flow.from_client_config",
                    side_effect=build_flow,
                ),
                patch(
                    "moliya_agent.google_integration.AuthorizedSession",
                    _AuthorizedSession,
                ),
            ):
                authorization_url = manager.authorization_url("web-owner", owner_id)
                state = parse_qs(urlparse(authorization_url).query)["state"][0]
                manager.complete_oauth(state=state, code="test-code")

            self.assertEqual(len(verifier_calls), 2)
            self.assertEqual(verifier_calls[0], verifier_calls[1])
            self.assertGreaterEqual(len(verifier_calls[0]), 43)
            integration = store.get_google_integration("web-owner")
            self.assertIsNotNone(integration)
            self.assertNotEqual(integration["encrypted_refresh_token"], "test-refresh-token")


if __name__ == "__main__":
    unittest.main()
