from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from .domain import DraftRecord, DraftStatus, ParsedMessage


class DraftNotFoundError(LookupError):
    pass


class SQLiteDraftRepository:
    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=10)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS drafts (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    confirmed_at TEXT,
                    UNIQUE(actor_id, source_id)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status)"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_actor_created "
                "ON audit_events(actor_id, created_at DESC)"
            )

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> DraftRecord:
        return DraftRecord(
            id=row["id"],
            actor_id=row["actor_id"],
            source_id=row["source_id"],
            raw_text=row["raw_text"],
            parsed=ParsedMessage.from_dict(json.loads(row["payload_json"])),
            status=DraftStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            confirmed_at=(
                datetime.fromisoformat(row["confirmed_at"])
                if row["confirmed_at"]
                else None
            ),
        )

    def get(self, draft_id: str) -> DraftRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM drafts WHERE id = ?", (draft_id,)
            ).fetchone()
        if row is None:
            raise DraftNotFoundError(draft_id)
        return self._row_to_record(row)

    def get_by_source(self, actor_id: str, source_id: str) -> DraftRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM drafts WHERE actor_id = ? AND source_id = ?",
                (actor_id, source_id),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def create(
        self,
        *,
        actor_id: str,
        source_id: str,
        raw_text: str,
        parsed: ParsedMessage,
        now: datetime | None = None,
    ) -> DraftRecord:
        now = now or datetime.now(UTC)
        existing = self.get_by_source(actor_id, source_id)
        if existing:
            return existing
        draft_id = str(uuid.uuid4())
        with self._lock, self._connect() as connection:
            try:
                connection.execute(
                    """
                    INSERT INTO drafts (
                        id, actor_id, source_id, raw_text, payload_json,
                        status, created_at, updated_at, confirmed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (
                        draft_id,
                        actor_id,
                        source_id,
                        raw_text,
                        json.dumps(parsed.to_dict(), ensure_ascii=False),
                        DraftStatus.PENDING.value,
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
            except sqlite3.IntegrityError:
                concurrent = self.get_by_source(actor_id, source_id)
                if concurrent:
                    return concurrent
                raise
        return self.get(draft_id)

    def add_audit_event(
        self,
        *,
        actor_id: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        details: dict[str, object] | None = None,
        now: datetime | None = None,
    ) -> dict[str, object]:
        event_id = str(uuid.uuid4())
        created_at = now or datetime.now(UTC)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    id, actor_id, event_type, entity_type, entity_id,
                    details_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    actor_id,
                    event_type,
                    entity_type,
                    entity_id,
                    json.dumps(details or {}, ensure_ascii=False),
                    created_at.isoformat(),
                ),
            )
        return {
            "id": event_id,
            "actor_id": actor_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "created_at": created_at.isoformat(),
        }

    def list_audit_events(
        self, *, actor_id: str, limit: int = 50, offset: int = 0
    ) -> tuple[list[dict[str, object]], int]:
        with self._connect() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM audit_events WHERE actor_id = ?", (actor_id,)
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT * FROM audit_events
                WHERE actor_id = ?
                ORDER BY created_at DESC LIMIT ? OFFSET ?
                """,
                (actor_id, limit, offset),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "actor_id": row["actor_id"],
                "event_type": row["event_type"],
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "details": json.loads(row["details_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ], total

    def set_status(
        self,
        draft_id: str,
        status: DraftStatus,
        *,
        now: datetime | None = None,
    ) -> DraftRecord:
        now = now or datetime.now(UTC)
        confirmed_at = now.isoformat() if status == DraftStatus.CONFIRMED else None
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE drafts
                SET status = ?, updated_at = ?, confirmed_at = ?
                WHERE id = ?
                """,
                (status.value, now.isoformat(), confirmed_at, draft_id),
            )
            if cursor.rowcount == 0:
                raise DraftNotFoundError(draft_id)
        return self.get(draft_id)

    def list_confirmed(self) -> list[DraftRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM drafts WHERE status = ? ORDER BY created_at",
                (DraftStatus.CONFIRMED.value,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def list_drafts(
        self,
        *,
        actor_id: str,
        status: DraftStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DraftRecord], int]:
        clauses = ["actor_id = ?"]
        parameters: list[object] = [actor_id]
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status.value)
        where = " AND ".join(clauses)
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM drafts WHERE {where}", parameters
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT * FROM drafts WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                [*parameters, limit, offset],
            ).fetchall()
        return [self._row_to_record(row) for row in rows], int(total)
