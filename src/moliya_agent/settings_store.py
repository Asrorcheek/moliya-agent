from __future__ import annotations

import sqlite3
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class SettingsItemNotFoundError(LookupError):
    pass


class SettingsConflictError(RuntimeError):
    pass


DEFAULT_CATEGORIES = (
    ("rent", "Ijara", "Аренда", "Rent"),
    ("salary", "Oylik", "Зарплата", "Salary"),
    ("utilities", "Kommunal", "Коммунальные", "Utilities"),
    ("tax", "Soliq", "Налоги", "Tax"),
    ("marketing", "Marketing", "Маркетинг", "Marketing"),
    ("delivery", "Yetkazib berish", "Доставка", "Delivery"),
    ("other", "Boshqa", "Другое", "Other"),
)


class SQLiteSettingsStore:
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
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS business_profiles (
                    actor_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    timezone TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS team_members (
                    id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    telegram_linked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_team_actor
                    ON team_members(actor_id, created_at);
                CREATE TABLE IF NOT EXISTS categories (
                    actor_id TEXT NOT NULL,
                    id TEXT NOT NULL,
                    name_uz TEXT NOT NULL,
                    name_ru TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    is_custom INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(actor_id, id)
                );
                """
            )

    def _ensure_defaults(self, actor_id: str, owner_name: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO business_profiles (
                    actor_id, name, phone, address, timezone, currency, updated_at
                ) VALUES (?, ?, '', '', 'Asia/Tashkent', 'UZS', ?)
                """,
                (actor_id, "Moliya Agent", now),
            )
            owner_exists = connection.execute(
                "SELECT 1 FROM team_members WHERE actor_id = ? AND role = 'owner' LIMIT 1",
                (actor_id,),
            ).fetchone()
            if owner_exists is None:
                connection.execute(
                    """
                    INSERT INTO team_members (
                        id, actor_id, full_name, role, telegram_linked, created_at
                    ) VALUES (?, ?, ?, 'owner', 0, ?)
                    """,
                    (str(uuid.uuid4()), actor_id, owner_name, now),
                )
            for category_id, name_uz, name_ru, name_en in DEFAULT_CATEGORIES:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO categories (
                        actor_id, id, name_uz, name_ru, name_en, is_custom, created_at
                    ) VALUES (?, ?, ?, ?, ?, 0, ?)
                    """,
                    (actor_id, category_id, name_uz, name_ru, name_en, now),
                )

    @staticmethod
    def _business(row: sqlite3.Row) -> dict[str, str]:
        return {
            "name": row["name"],
            "phone": row["phone"],
            "address": row["address"],
            "timezone": row["timezone"],
            "currency": row["currency"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _member(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "full_name": row["full_name"],
            "role": row["role"],
            "telegram_linked": bool(row["telegram_linked"]),
        }

    @staticmethod
    def _category(row: sqlite3.Row) -> dict[str, object]:
        return {
            "id": row["id"],
            "name_uz": row["name_uz"],
            "name_ru": row["name_ru"],
            "name_en": row["name_en"],
            "is_custom": bool(row["is_custom"]),
        }

    def get_business(self, actor_id: str, owner_name: str) -> dict[str, str]:
        self._ensure_defaults(actor_id, owner_name)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM business_profiles WHERE actor_id = ?", (actor_id,)
            ).fetchone()
        return self._business(row)

    def update_business(
        self,
        actor_id: str,
        owner_name: str,
        *,
        name: str,
        phone: str,
        address: str,
        timezone: str,
    ) -> dict[str, str]:
        self._ensure_defaults(actor_id, owner_name)
        now = datetime.now(UTC).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE business_profiles
                SET name = ?, phone = ?, address = ?, timezone = ?, updated_at = ?
                WHERE actor_id = ?
                """,
                (name, phone, address, timezone, now, actor_id),
            )
        return self.get_business(actor_id, owner_name)

    def list_members(self, actor_id: str, owner_name: str) -> list[dict[str, object]]:
        self._ensure_defaults(actor_id, owner_name)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM team_members WHERE actor_id = ?
                ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'manager' THEN 1 ELSE 2 END,
                         created_at
                """,
                (actor_id,),
            ).fetchall()
        return [self._member(row) for row in rows]

    def create_member(
        self, actor_id: str, owner_name: str, *, full_name: str, role: str
    ) -> dict[str, object]:
        self._ensure_defaults(actor_id, owner_name)
        member_id = str(uuid.uuid4())
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO team_members (
                    id, actor_id, full_name, role, telegram_linked, created_at
                ) VALUES (?, ?, ?, ?, 0, ?)
                """,
                (member_id, actor_id, full_name, role, datetime.now(UTC).isoformat()),
            )
            row = connection.execute(
                "SELECT * FROM team_members WHERE actor_id = ? AND id = ?",
                (actor_id, member_id),
            ).fetchone()
        return self._member(row)

    def update_member(
        self, actor_id: str, member_id: str, *, full_name: str, role: str
    ) -> dict[str, object]:
        with self._lock, self._connect() as connection:
            current = connection.execute(
                "SELECT * FROM team_members WHERE actor_id = ? AND id = ?",
                (actor_id, member_id),
            ).fetchone()
            if current is None:
                raise SettingsItemNotFoundError(member_id)
            if current["role"] == "owner" and role != "owner":
                owner_count = connection.execute(
                    "SELECT COUNT(*) FROM team_members WHERE actor_id = ? AND role = 'owner'",
                    (actor_id,),
                ).fetchone()[0]
                if owner_count <= 1:
                    raise SettingsConflictError("Kamida bitta owner qolishi kerak")
            connection.execute(
                "UPDATE team_members SET full_name = ?, role = ? WHERE actor_id = ? AND id = ?",
                (full_name, role, actor_id, member_id),
            )
            row = connection.execute(
                "SELECT * FROM team_members WHERE actor_id = ? AND id = ?",
                (actor_id, member_id),
            ).fetchone()
        return self._member(row)

    def delete_member(self, actor_id: str, member_id: str) -> None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT role FROM team_members WHERE actor_id = ? AND id = ?",
                (actor_id, member_id),
            ).fetchone()
            if row is None:
                raise SettingsItemNotFoundError(member_id)
            if row["role"] == "owner":
                owner_count = connection.execute(
                    "SELECT COUNT(*) FROM team_members WHERE actor_id = ? AND role = 'owner'",
                    (actor_id,),
                ).fetchone()[0]
                if owner_count <= 1:
                    raise SettingsConflictError("Oxirgi ownerni o'chirib bo'lmaydi")
            connection.execute(
                "DELETE FROM team_members WHERE actor_id = ? AND id = ?",
                (actor_id, member_id),
            )

    def list_categories(self, actor_id: str, owner_name: str) -> list[dict[str, object]]:
        self._ensure_defaults(actor_id, owner_name)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM categories WHERE actor_id = ?
                ORDER BY is_custom, created_at, name_uz
                """,
                (actor_id,),
            ).fetchall()
        return [self._category(row) for row in rows]

    def create_category(
        self,
        actor_id: str,
        owner_name: str,
        *,
        name_uz: str,
        name_ru: str,
        name_en: str,
    ) -> dict[str, object]:
        self._ensure_defaults(actor_id, owner_name)
        category_id = str(uuid.uuid4())
        with self._lock, self._connect() as connection:
            duplicate = connection.execute(
                "SELECT 1 FROM categories WHERE actor_id = ? AND lower(name_uz) = lower(?)",
                (actor_id, name_uz),
            ).fetchone()
            if duplicate:
                raise SettingsConflictError("Bu kategoriya allaqachon mavjud")
            connection.execute(
                """
                INSERT INTO categories (
                    actor_id, id, name_uz, name_ru, name_en, is_custom, created_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    actor_id,
                    category_id,
                    name_uz,
                    name_ru,
                    name_en,
                    datetime.now(UTC).isoformat(),
                ),
            )
            row = connection.execute(
                "SELECT * FROM categories WHERE actor_id = ? AND id = ?",
                (actor_id, category_id),
            ).fetchone()
        return self._category(row)

    def update_category(
        self,
        actor_id: str,
        category_id: str,
        *,
        name_uz: str,
        name_ru: str,
        name_en: str,
    ) -> dict[str, object]:
        with self._lock, self._connect() as connection:
            current = connection.execute(
                "SELECT * FROM categories WHERE actor_id = ? AND id = ?",
                (actor_id, category_id),
            ).fetchone()
            if current is None:
                raise SettingsItemNotFoundError(category_id)
            if not current["is_custom"]:
                raise SettingsConflictError("Standart kategoriyani tahrirlab bo'lmaydi")
            duplicate = connection.execute(
                """
                SELECT 1 FROM categories
                WHERE actor_id = ? AND id != ? AND lower(name_uz) = lower(?)
                """,
                (actor_id, category_id, name_uz),
            ).fetchone()
            if duplicate:
                raise SettingsConflictError("Bu kategoriya allaqachon mavjud")
            connection.execute(
                """
                UPDATE categories SET name_uz = ?, name_ru = ?, name_en = ?
                WHERE actor_id = ? AND id = ?
                """,
                (name_uz, name_ru, name_en, actor_id, category_id),
            )
            row = connection.execute(
                "SELECT * FROM categories WHERE actor_id = ? AND id = ?",
                (actor_id, category_id),
            ).fetchone()
        return self._category(row)

    def delete_category(self, actor_id: str, category_id: str) -> None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT is_custom FROM categories WHERE actor_id = ? AND id = ?",
                (actor_id, category_id),
            ).fetchone()
            if row is None:
                raise SettingsItemNotFoundError(category_id)
            if not row["is_custom"]:
                raise SettingsConflictError("Standart kategoriyani o'chirib bo'lmaydi")
            connection.execute(
                "DELETE FROM categories WHERE actor_id = ? AND id = ?",
                (actor_id, category_id),
            )
