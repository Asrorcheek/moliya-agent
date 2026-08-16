from __future__ import annotations

import secrets
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Cookie, Depends, FastAPI, Header, HTTPException, Query, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .auth import InvalidSessionError, Principal, SessionManager
from .config import Settings
from .domain import DomainValidationError, DraftStatus, EntryKind, PaymentMethod
from .factory import build_service
from .parser import ParseError
from .repository import DraftNotFoundError
from .service import (
    AuthorizationError,
    ClarificationRequiredError,
    InvalidTransitionError,
    format_draft_preview,
)
from .settings_store import (
    SettingsConflictError,
    SettingsItemNotFoundError,
    SQLiteSettingsStore,
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


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class BusinessProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=160)
    phone: str = Field(default="", max_length=64)
    address: str = Field(default="", max_length=300)
    timezone: Literal["Asia/Tashkent"] = "Asia/Tashkent"


class TeamMemberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=160)
    role: Literal["owner", "manager", "accountant"]


class CategoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name_uz: str = Field(min_length=1, max_length=80)
    name_ru: str = Field(min_length=1, max_length=80)
    name_en: str = Field(min_length=1, max_length=80)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or Settings.from_env()
    service = build_service(resolved_settings)
    settings_store = SQLiteSettingsStore(resolved_settings.db_path)
    app = FastAPI(title="Moliya AI Agent", version="0.1.0")
    sessions = SessionManager(resolved_settings.session_secret)

    def authenticate(
        x_moliya_token: Annotated[str | None, Header()] = None,
        moliya_session: Annotated[str | None, Cookie()] = None,
    ) -> Principal:
        if x_moliya_token and secrets.compare_digest(
            x_moliya_token, resolved_settings.internal_token
        ):
            return Principal(actor_id="", username="internal", authentication="token")
        if moliya_session:
            try:
                return sessions.verify(moliya_session)
            except InvalidSessionError:
                pass
        raise HTTPException(status_code=401, detail="Autentifikatsiya talab qilinadi")

    def actor_for(principal: Principal, requested_actor: str | None = None) -> str:
        if principal.authentication == "session":
            if requested_actor and requested_actor != principal.actor_id:
                raise HTTPException(status_code=403, detail="Actor ruxsat etilmagan")
            return principal.actor_id
        if not requested_actor:
            raise HTTPException(status_code=422, detail="actor_id talab qilinadi")
        return requested_actor

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

    @app.exception_handler(SettingsItemNotFoundError)
    async def settings_not_found_handler(_request, _exc):
        return _error_response(404, "Sozlama elementi topilmadi")

    @app.exception_handler(SettingsConflictError)
    async def settings_conflict_handler(_request, exc):
        return _error_response(409, str(exc))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "parser_mode": resolved_settings.parser_mode,
            "sheet_mode": resolved_settings.sheet_mode,
        }

    @app.post("/v1/session")
    def login(request: LoginRequest, response: Response) -> dict[str, str]:
        username_matches = secrets.compare_digest(
            request.username, resolved_settings.web_username
        )
        password_matches = secrets.compare_digest(
            request.password, resolved_settings.web_password
        )
        if not (username_matches and password_matches):
            raise HTTPException(status_code=401, detail="Login yoki parol noto'g'ri")
        token = sessions.create(
            username=resolved_settings.web_username,
            actor_id=resolved_settings.web_actor_id,
        )
        response.set_cookie(
            "moliya_session",
            token,
            max_age=sessions.lifetime_seconds,
            httponly=True,
            secure=resolved_settings.session_cookie_secure,
            samesite="strict",
            path="/",
        )
        return {
            "username": resolved_settings.web_username,
            "actor_id": resolved_settings.web_actor_id,
        }

    @app.get("/v1/session")
    def current_session(principal: Principal = Depends(authenticate)) -> dict[str, str]:
        return {"username": principal.username, "actor_id": principal.actor_id}

    @app.delete("/v1/session")
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie("moliya_session", path="/")
        return {"logged_out": True}

    @app.post("/v1/drafts", dependencies=[Depends(authenticate)])
    def create_draft(
        request: DraftRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        actor_id = actor_for(principal, request.actor_id)
        draft = service.create_draft(
            actor_id=actor_id,
            source_id=request.source_id,
            text=request.text,
            received_at=request.received_at,
        )
        return {"draft": draft.to_dict(), "preview": format_draft_preview(draft)}

    @app.post(
        "/v1/drafts/{draft_id}/confirm", dependencies=[Depends(authenticate)]
    )
    def confirm(
        draft_id: str,
        request: ActionRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        result = service.confirm(
            actor_id=actor_for(principal, request.actor_id), draft_id=draft_id
        )
        return result.to_dict()

    @app.post(
        "/v1/drafts/{draft_id}/reject", dependencies=[Depends(authenticate)]
    )
    def reject(
        draft_id: str,
        request: ActionRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        return {
            "draft": service.reject(
                actor_id=actor_for(principal, request.actor_id), draft_id=draft_id
            ).to_dict()
        }

    @app.get("/v1/reports/monthly", dependencies=[Depends(authenticate)])
    def monthly_report(
        month: str,
        principal: Principal = Depends(authenticate),
        actor_id: str | None = None,
    ) -> dict[str, int | str]:
        return service.monthly_report(
            actor_id=actor_for(principal, actor_id), month=month
        )

    @app.get("/v1/drafts", dependencies=[Depends(authenticate)])
    def list_drafts(
        principal: Principal = Depends(authenticate),
        actor_id: str | None = None,
        status: DraftStatus | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, object]:
        items, total = service.list_drafts(
            actor_id=actor_for(principal, actor_id),
            status=status,
            limit=limit,
            offset=offset,
        )
        return {"items": [item.to_dict() for item in items], "total": total}

    @app.get("/v1/drafts/{draft_id}", dependencies=[Depends(authenticate)])
    def get_draft(
        draft_id: str,
        principal: Principal = Depends(authenticate),
        actor_id: str | None = None,
    ) -> dict[str, object]:
        return {
            "draft": service.get_draft(
                actor_id=actor_for(principal, actor_id), draft_id=draft_id
            ).to_dict()
        }

    @app.get("/v1/transactions", dependencies=[Depends(authenticate)])
    def list_transactions(
        principal: Principal = Depends(authenticate),
        actor_id: str | None = None,
        month: str | None = None,
        kind: EntryKind | None = None,
        payment_method: PaymentMethod | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, object]:
        items, total = service.list_transactions(
            actor_id=actor_for(principal, actor_id),
            month=month,
            kind=kind,
            payment_method=payment_method,
            limit=limit,
            offset=offset,
        )
        return {"items": items, "total": total}

    @app.get("/v1/reports/dashboard", dependencies=[Depends(authenticate)])
    def dashboard_report(
        month: str,
        principal: Principal = Depends(authenticate),
        actor_id: str | None = None,
    ) -> dict[str, object]:
        return service.dashboard_report(
            actor_id=actor_for(principal, actor_id), month=month
        )

    @app.get("/v1/audit-events", dependencies=[Depends(authenticate)])
    def list_audit_events(
        principal: Principal = Depends(authenticate),
        actor_id: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> dict[str, object]:
        items, total = service.list_audit_events(
            actor_id=actor_for(principal, actor_id), limit=limit, offset=offset
        )
        return {"items": items, "total": total}

    def settings_actor(principal: Principal) -> str:
        return actor_for(principal, None)

    @app.get("/v1/settings", dependencies=[Depends(authenticate)])
    def get_settings(principal: Principal = Depends(authenticate)) -> dict[str, object]:
        actor_id = settings_actor(principal)
        return {
            "business": settings_store.get_business(actor_id, principal.username),
            "users": settings_store.list_members(actor_id, principal.username),
            "categories": settings_store.list_categories(actor_id, principal.username),
            "integration": {
                "sheet_mode": resolved_settings.sheet_mode,
                "parser_mode": resolved_settings.parser_mode,
                "connected": resolved_settings.sheet_mode == "google",
                "spreadsheet_url": (
                    f"https://docs.google.com/spreadsheets/d/{resolved_settings.spreadsheet_id}/edit"
                    if resolved_settings.spreadsheet_id
                    else None
                ),
            },
        }

    @app.put("/v1/settings/business", dependencies=[Depends(authenticate)])
    def update_business(
        request: BusinessProfileRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        return {
            "business": settings_store.update_business(
                settings_actor(principal),
                principal.username,
                name=request.name.strip(),
                phone=request.phone.strip(),
                address=request.address.strip(),
                timezone=request.timezone,
            )
        }

    @app.get("/v1/users", dependencies=[Depends(authenticate)])
    def list_users(principal: Principal = Depends(authenticate)) -> dict[str, object]:
        return {
            "items": settings_store.list_members(
                settings_actor(principal), principal.username
            )
        }

    @app.post("/v1/users", status_code=201, dependencies=[Depends(authenticate)])
    def create_user(
        request: TeamMemberRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        return {
            "user": settings_store.create_member(
                settings_actor(principal),
                principal.username,
                full_name=request.full_name.strip(),
                role=request.role,
            )
        }

    @app.put("/v1/users/{user_id}", dependencies=[Depends(authenticate)])
    def update_user(
        user_id: str,
        request: TeamMemberRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        return {
            "user": settings_store.update_member(
                settings_actor(principal),
                user_id,
                full_name=request.full_name.strip(),
                role=request.role,
            )
        }

    @app.delete("/v1/users/{user_id}", dependencies=[Depends(authenticate)])
    def delete_user(
        user_id: str, principal: Principal = Depends(authenticate)
    ) -> dict[str, bool]:
        settings_store.delete_member(settings_actor(principal), user_id)
        return {"deleted": True}

    @app.get("/v1/categories", dependencies=[Depends(authenticate)])
    def list_categories(principal: Principal = Depends(authenticate)) -> dict[str, object]:
        return {
            "items": settings_store.list_categories(
                settings_actor(principal), principal.username
            )
        }

    @app.post("/v1/categories", status_code=201, dependencies=[Depends(authenticate)])
    def create_category(
        request: CategoryRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        return {
            "category": settings_store.create_category(
                settings_actor(principal),
                principal.username,
                name_uz=request.name_uz.strip(),
                name_ru=request.name_ru.strip(),
                name_en=request.name_en.strip(),
            )
        }

    @app.put("/v1/categories/{category_id}", dependencies=[Depends(authenticate)])
    def update_category(
        category_id: str,
        request: CategoryRequest,
        principal: Principal = Depends(authenticate),
    ) -> dict[str, object]:
        return {
            "category": settings_store.update_category(
                settings_actor(principal),
                category_id,
                name_uz=request.name_uz.strip(),
                name_ru=request.name_ru.strip(),
                name_en=request.name_en.strip(),
            )
        }

    @app.delete("/v1/categories/{category_id}", dependencies=[Depends(authenticate)])
    def delete_category(
        category_id: str, principal: Principal = Depends(authenticate)
    ) -> dict[str, bool]:
        settings_store.delete_category(settings_actor(principal), category_id)
        return {"deleted": True}

    web_dist_dir = resolved_settings.web_dist_dir
    if web_dist_dir and (web_dist_dir / "index.html").is_file():
        assets_dir = web_dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=assets_dir), name="web-assets")

        @app.get("/", include_in_schema=False)
        def web_index() -> FileResponse:
            return FileResponse(web_dist_dir / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        def web_spa(full_path: str) -> FileResponse:
            if full_path.startswith("v1/") or full_path == "health":
                raise HTTPException(status_code=404, detail="Topilmadi")
            requested = _safe_web_file(web_dist_dir, full_path)
            if requested is not None:
                return FileResponse(requested)
            return FileResponse(web_dist_dir / "index.html")

    return app


def _safe_web_file(root: Path, relative_path: str) -> Path | None:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def _error_response(status_code: int, detail: str):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=status_code, content={"detail": detail})


app = create_app()
