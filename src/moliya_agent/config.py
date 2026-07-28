from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(RuntimeError):
    """Raised when deployment configuration is unsafe or incomplete."""


def _csv_set(value: str) -> frozenset[str]:
    return frozenset(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str
    bind_host: str
    bind_port: int
    internal_token: str
    allowed_actors: frozenset[str]
    parser_mode: str
    openai_api_key: str | None
    openai_model: str
    openai_reasoning_effort: str
    db_path: Path
    sheet_mode: str
    spreadsheet_id: str | None
    service_account_file: Path | None
    service_account_json: str | None

    @classmethod
    def from_env(cls) -> Settings:
        service_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        settings = cls(
            environment=os.getenv("ENVIRONMENT", "development").strip().lower(),
            bind_host=os.getenv("MOLIYA_BIND_HOST", "127.0.0.1").strip(),
            bind_port=int(os.getenv("MOLIYA_BIND_PORT", "8088")),
            internal_token=os.getenv(
                "MOLIYA_INTERNAL_TOKEN", "dev-only-change-me"
            ).strip(),
            allowed_actors=_csv_set(
                os.getenv("MOLIYA_ALLOWED_ACTORS", "hermes,local-dev")
            ),
            parser_mode=os.getenv("MOLIYA_PARSER_MODE", "rule").strip().lower(),
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip(),
            openai_reasoning_effort=os.getenv(
                "OPENAI_REASONING_EFFORT", "none"
            ).strip(),
            db_path=Path(os.getenv("MOLIYA_DB_PATH", "./data/moliya.db")),
            sheet_mode=os.getenv("MOLIYA_SHEET_MODE", "memory").strip().lower(),
            spreadsheet_id=os.getenv("GOOGLE_SPREADSHEET_ID", "").strip() or None,
            service_account_file=Path(service_file) if service_file else None,
            service_account_json=os.getenv(
                "GOOGLE_SERVICE_ACCOUNT_JSON", ""
            ).strip()
            or None,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.parser_mode not in {"rule", "openai"}:
            raise ConfigurationError("MOLIYA_PARSER_MODE rule yoki openai bo'lishi kerak")
        if self.sheet_mode not in {"memory", "google"}:
            raise ConfigurationError("MOLIYA_SHEET_MODE memory yoki google bo'lishi kerak")
        if self.parser_mode == "openai" and not self.openai_api_key:
            raise ConfigurationError("OpenAI parser uchun OPENAI_API_KEY kerak")
        if self.sheet_mode == "google":
            if not self.spreadsheet_id:
                raise ConfigurationError("Google Sheets uchun GOOGLE_SPREADSHEET_ID kerak")
            if not (self.service_account_file or self.service_account_json):
                raise ConfigurationError(
                    "Google Sheets uchun service account file yoki JSON secret kerak"
                )
        if self.environment == "production":
            if len(self.internal_token) < 24:
                raise ConfigurationError(
                    "Production MOLIYA_INTERNAL_TOKEN kamida 24 belgi bo'lishi kerak"
                )
            if not self.allowed_actors:
                raise ConfigurationError("Productionda MOLIYA_ALLOWED_ACTORS bo'sh bo'lmasin")
            if self.bind_host not in {"127.0.0.1", "::1"}:
                raise ConfigurationError(
                    "MVP backend productionda faqat localhost'ga bind qilinadi"
                )
