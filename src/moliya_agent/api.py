from __future__ import annotations

import secrets
from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .domain import DomainValidationError
from .factory import build_service
from .parser import ParseError
from .repository import DraftNotFoundError
from .service import (
    AuthorizationError,
    ClarificationRequiredError,
    InvalidTransitionError,
    format_draft_preview,
)
from .sheets import SheetWriteError


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1, max_length=128)
    source_id: str = Field(min_length=1, max_length=256)
    text: str = Field(min_length=1, max_length=10_000)
    received_at: datetime | None = None


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(min_length=1, max_length=128)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    service = build_service(resolved_settings)
    app = FastAPI(title="Moliya AI Agent", version="0.1.0")

    def authenticate(
        x_moliya_token: Annotated[str | None, Header()] = None,
    ) -> None:
        if not x_moliya_token or not secrets.compare_digest(
            x_moliya_token, resolved_settings.internal_token
        ):
            raise HTTPException(status_code=401, detail="Internal token noto'g'ri")

    @app.exception_handler(DraftNotFoundError)
    async def draft_not_found_handler(_request, _exc):
        return _error_response(404, "Draft topilmadi")

    @app.exception_handler(AuthorizationError)
    async def authorization_handler(_request, exc):
        return _error_response(403, str(exc))

    async def parse_handler(_request, exc):
        return _error_response(422, str(exc))

    app.add_exception_handler(ParseError, parse_handler)
    app.add_exception_handler(ClarificationRequiredError, parse_handler)
    app.add_exception_handler(DomainValidationError, parse_handler)

    @app.exception_handler(InvalidTransitionError)
    async def transition_handler(_request, exc):
        return _error_response(409, str(exc))

    @app.exception_handler(SheetWriteError)
    async def sheet_handler(_request, exc):
        return _error_response(502, str(exc))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "parser_mode": resolved_settings.parser_mode,
            "sheet_mode": resolved_settings.sheet_mode,
        }

    @app.post("/v1/drafts", dependencies=[Depends(authenticate)])
    def create_draft(request: DraftRequest) -> dict[str, object]:
        draft = service.create_draft(
            actor_id=request.actor_id,
            source_id=request.source_id,
            text=request.text,
            received_at=request.received_at,
        )
        return {"draft": draft.to_dict(), "preview": format_draft_preview(draft)}

    @app.post(
        "/v1/drafts/{draft_id}/confirm", dependencies=[Depends(authenticate)]
    )
    def confirm(draft_id: str, request: ActionRequest) -> dict[str, object]:
        result = service.confirm(actor_id=request.actor_id, draft_id=draft_id)
        return result.to_dict()

    @app.post(
        "/v1/drafts/{draft_id}/reject", dependencies=[Depends(authenticate)]
    )
    def reject(draft_id: str, request: ActionRequest) -> dict[str, object]:
        return {
            "draft": service.reject(
                actor_id=request.actor_id, draft_id=draft_id
            ).to_dict()
        }

    @app.get("/v1/reports/monthly", dependencies=[Depends(authenticate)])
    def monthly_report(actor_id: str, month: str) -> dict[str, int | str]:
        return service.monthly_report(actor_id=actor_id, month=month)

    return app


def _error_response(status_code: int, detail: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content={"detail": detail})


app = create_app()
