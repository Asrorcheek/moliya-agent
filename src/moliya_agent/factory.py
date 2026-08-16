from __future__ import annotations

from .config import Settings
from .parser import HermesParser, OpenAIParser, RuleBasedParser
from .repository import SQLiteDraftRepository
from .service import MoliyaService
from .sheets import GoogleSheetsWriter, InMemorySheetWriter


def build_service(settings: Settings) -> MoliyaService:
    repository = SQLiteDraftRepository(settings.db_path)
    if settings.parser_mode == "openai":
        parser = OpenAIParser(
            api_key=settings.openai_api_key or "",
            model=settings.openai_model,
            reasoning_effort=settings.openai_reasoning_effort,
        )
    elif settings.parser_mode == "hermes":
        parser = HermesParser(
            api_base=settings.hermes_api_base,
            api_key=settings.hermes_api_key or "",
            model=settings.hermes_model,
        )
    else:
        parser = RuleBasedParser()

    if settings.sheet_mode == "google":
        sheet_writer = GoogleSheetsWriter(
            spreadsheet_id=settings.spreadsheet_id or "",
            service_account_file=settings.service_account_file,
            service_account_json=settings.service_account_json,
        )
    else:
        sheet_writer = InMemorySheetWriter()

    return MoliyaService(
        repository=repository,
        parser=parser,
        sheet_writer=sheet_writer,
        allowed_actors=settings.allowed_actors,
    )
