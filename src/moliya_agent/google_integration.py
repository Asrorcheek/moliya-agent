from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import threading
import time
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from .config import Settings
from .settings_store import SQLiteSettingsStore
from .sheets import GoogleSheetsWriter, InMemorySheetWriter, SheetWriter
from .workbook import initialize_workbook

GOOGLE_SCOPES = (
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive.file",
)

logger = logging.getLogger(__name__)


class GoogleIntegrationError(RuntimeError):
    pass


class GoogleIntegrationManager:
    def __init__(self, settings: Settings, store: SQLiteSettingsStore) -> None:
        self._settings = settings
        self._store = store
        encryption_key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.session_secret.encode()).digest()
        )
        self._cipher = Fernet(encryption_key)
        self._state_secret = settings.session_secret.encode()
        self._cache: dict[str, tuple[str, GoogleSheetsWriter]] = {}
        self._cache_lock = threading.RLock()
        if settings.sheet_mode == "google":
            self._fallback: SheetWriter = GoogleSheetsWriter(
                spreadsheet_id=settings.spreadsheet_id or "",
                service_account_file=settings.service_account_file,
                service_account_json=settings.service_account_json,
            )
        else:
            self._fallback = InMemorySheetWriter()

    @property
    def oauth_configured(self) -> bool:
        return bool(
            self._settings.google_oauth_client_id
            and self._settings.google_oauth_client_secret
            and self._settings.google_oauth_redirect_uri
        )

    @property
    def picker_configured(self) -> bool:
        return self.oauth_configured and bool(self._settings.google_picker_api_key)

    def _client_config(self) -> dict[str, object]:
        if not self.oauth_configured:
            raise GoogleIntegrationError("Google OAuth serverda sozlanmagan")
        return {
            "web": {
                "client_id": self._settings.google_oauth_client_id,
                "client_secret": self._settings.google_oauth_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._settings.google_oauth_redirect_uri],
            }
        }

    def _state(self, actor_id: str, user_id: str, code_verifier: str) -> str:
        payload = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "actor_id": actor_id,
                        "user_id": user_id,
                        "nonce": secrets.token_urlsafe(12),
                        "exp": int(time.time()) + 10 * 60,
                        "pkce": self._cipher.encrypt(code_verifier.encode()).decode(),
                    },
                    separators=(",", ":"),
                ).encode()
            )
            .decode()
            .rstrip("=")
        )
        signature = (
            base64.urlsafe_b64encode(
                hmac.new(self._state_secret, payload.encode(), hashlib.sha256).digest()
            )
            .decode()
            .rstrip("=")
        )
        return f"{payload}.{signature}"

    def _verify_state(self, state: str) -> dict[str, object]:
        try:
            payload, signature = state.split(".", 1)
            expected = (
                base64.urlsafe_b64encode(
                    hmac.new(self._state_secret, payload.encode(), hashlib.sha256).digest()
                )
                .decode()
                .rstrip("=")
            )
            if not hmac.compare_digest(signature, expected):
                raise GoogleIntegrationError("Google OAuth state noto'g'ri")
            decoded = base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            data = json.loads(decoded)
            if int(data["exp"]) < int(time.time()):
                raise GoogleIntegrationError("Google OAuth state muddati tugagan")
            return data
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, GoogleIntegrationError):
                raise
            raise GoogleIntegrationError("Google OAuth state noto'g'ri") from exc

    def authorization_url(self, actor_id: str, user_id: str) -> str:
        code_verifier = secrets.token_urlsafe(96)
        state = self._state(actor_id, user_id, code_verifier)
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=GOOGLE_SCOPES,
            state=state,
            code_verifier=code_verifier,
            autogenerate_code_verifier=False,
        )
        flow.redirect_uri = self._settings.google_oauth_redirect_uri
        url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return url

    def complete_oauth(self, *, state: str, code: str) -> str:
        data = self._verify_state(state)
        actor_id = str(data["actor_id"])
        try:
            code_verifier = self._cipher.decrypt(str(data["pkce"]).encode()).decode()
        except (InvalidToken, KeyError, TypeError, ValueError) as exc:
            raise GoogleIntegrationError("Google OAuth PKCE state noto'g'ri") from exc
        member = self._store.get_login_member(str(data["user_id"]))
        if (
            not member
            or not member["active"]
            or member["role"] != "owner"
            or member["actor_id"] != actor_id
        ):
            raise GoogleIntegrationError("Google ulash uchun Owner sessiyasi yaroqsiz")
        flow = Flow.from_client_config(
            self._client_config(),
            scopes=GOOGLE_SCOPES,
            state=state,
            code_verifier=code_verifier,
            autogenerate_code_verifier=False,
        )
        flow.redirect_uri = self._settings.google_oauth_redirect_uri
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            if not credentials.refresh_token:
                raise GoogleIntegrationError("Google refresh token qaytarmadi")
            response = AuthorizedSession(credentials).get(
                "https://openidconnect.googleapis.com/v1/userinfo", timeout=15
            )
            response.raise_for_status()
            account_email = str(response.json().get("email", "")).strip().lower()
            if not account_email:
                raise GoogleIntegrationError("Google account emaili olinmadi")
        except GoogleIntegrationError:
            raise
        except Exception as exc:
            # OAuth responses can contain credentials, so log only the exception type.
            logger.warning("google_oauth_completion_failed exception_type=%s", type(exc).__name__)
            raise GoogleIntegrationError("Google OAuth yakunlanmadi") from exc
        encrypted = self._cipher.encrypt(credentials.refresh_token.encode()).decode()
        self._store.save_google_connection(
            actor_id,
            account_email=account_email,
            encrypted_refresh_token=encrypted,
            scopes=" ".join(credentials.scopes or GOOGLE_SCOPES),
        )
        self.invalidate(actor_id)
        return actor_id

    def _credentials(self, actor_id: str) -> Credentials:
        integration = self._store.get_google_integration(actor_id)
        if not integration:
            raise GoogleIntegrationError("Google account ulanmagan")
        try:
            refresh_token = self._cipher.decrypt(
                str(integration["encrypted_refresh_token"]).encode()
            ).decode()
        except InvalidToken as exc:
            raise GoogleIntegrationError("Google tokenini ochib bo'lmadi") from exc
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._settings.google_oauth_client_id,
            client_secret=self._settings.google_oauth_client_secret,
            scopes=str(integration["scopes"]).split(),
        )

    def picker_config(self, actor_id: str) -> dict[str, str]:
        if not self.picker_configured:
            raise GoogleIntegrationError("Google Picker serverda sozlanmagan")
        credentials = self._credentials(actor_id)
        credentials.refresh(Request())
        return {
            "access_token": credentials.token or "",
            "developer_key": self._settings.google_picker_api_key or "",
            "client_id": self._settings.google_oauth_client_id or "",
        }

    def _sheets_service(self, actor_id: str) -> Any:
        return build(
            "sheets",
            "v4",
            credentials=self._credentials(actor_id),
            cache_discovery=False,
        )

    def select_spreadsheet(
        self, actor_id: str, *, spreadsheet_id: str, spreadsheet_name: str
    ) -> dict[str, object]:
        service = self._sheets_service(actor_id)
        try:
            metadata = (
                service.spreadsheets()
                .get(
                    spreadsheetId=spreadsheet_id,
                    fields="spreadsheetId,properties.title",
                )
                .execute()
            )
            initialize_workbook(service, spreadsheet_id)
        except Exception as exc:
            raise GoogleIntegrationError(f"Google Sheetni ulab bo'lmadi: {exc}") from exc
        selected_name = str(metadata.get("properties", {}).get("title") or spreadsheet_name)
        result = self._store.select_google_spreadsheet(
            actor_id,
            spreadsheet_id=spreadsheet_id,
            spreadsheet_name=selected_name,
        )
        self.invalidate(actor_id)
        return result

    def create_spreadsheet(self, actor_id: str, *, title: str) -> dict[str, object]:
        service = self._sheets_service(actor_id)
        try:
            created = (
                service.spreadsheets()
                .create(
                    body={"properties": {"title": title}},
                    fields="spreadsheetId,spreadsheetUrl,properties.title",
                )
                .execute()
            )
            spreadsheet_id = str(created["spreadsheetId"])
            initialize_workbook(service, spreadsheet_id)
        except Exception as exc:
            raise GoogleIntegrationError(f"Google Sheet yaratilmadi: {exc}") from exc
        result = self._store.select_google_spreadsheet(
            actor_id,
            spreadsheet_id=spreadsheet_id,
            spreadsheet_name=str(created.get("properties", {}).get("title") or title),
        )
        self.invalidate(actor_id)
        return result

    def disconnect(self, actor_id: str) -> None:
        self._store.delete_google_integration(actor_id)
        self.invalidate(actor_id)

    def invalidate(self, actor_id: str) -> None:
        with self._cache_lock:
            self._cache.pop(actor_id, None)

    def writer_for(self, actor_id: str) -> SheetWriter:
        integration = self._store.get_google_integration(actor_id)
        if (
            not self.oauth_configured
            or not integration
            or not integration.get("spreadsheet_id")
        ):
            return self._fallback
        cache_key = hashlib.sha256(
            (
                str(integration["spreadsheet_id"]) + str(integration["encrypted_refresh_token"])
            ).encode()
        ).hexdigest()
        with self._cache_lock:
            cached = self._cache.get(actor_id)
            if cached and cached[0] == cache_key:
                return cached[1]
            writer = GoogleSheetsWriter(
                spreadsheet_id=str(integration["spreadsheet_id"]),
                credentials=self._credentials(actor_id),
            )
            self._cache[actor_id] = (cache_key, writer)
            return writer

    def status(self, actor_id: str) -> dict[str, object]:
        integration = self._store.get_google_integration(actor_id)
        oauth_selected = bool(
            self.oauth_configured and integration and integration.get("spreadsheet_id")
        )
        fallback_connected = self._settings.sheet_mode == "google"
        if oauth_selected:
            spreadsheet_id = str(integration["spreadsheet_id"])
            spreadsheet_name = str(integration.get("spreadsheet_name") or "")
            provider = "oauth"
        else:
            spreadsheet_id = self._settings.spreadsheet_id or ""
            spreadsheet_name = "Moliya Agent Google Sheet" if fallback_connected else ""
            provider = "service_account" if fallback_connected else "memory"
        return {
            "connected": oauth_selected or fallback_connected,
            "provider": provider,
            "oauth_configured": self.oauth_configured,
            "picker_configured": self.picker_configured,
            "google_account_connected": bool(integration),
            "account_email": str(integration.get("account_email") or "") if integration else None,
            "spreadsheet_id": spreadsheet_id or None,
            "spreadsheet_name": spreadsheet_name or None,
            "spreadsheet_url": (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
                if spreadsheet_id
                else None
            ),
        }
