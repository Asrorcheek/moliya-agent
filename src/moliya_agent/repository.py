from __future__ import annotations

import json
import sqlite3
import threading
import uuid
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

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

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
