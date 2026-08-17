#!/usr/bin/env python3
"""Insert an idempotent rolling month of clearly labelled demo operations."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

from dotenv import dotenv_values

from moliya_agent.config import Settings
from moliya_agent.domain import ParsedMessage
from moliya_agent.repository import SQLiteDraftRepository
from moliya_agent.service import MoliyaService
from moliya_agent.sheets import GoogleSheetsWriter, InMemorySheetWriter


@dataclass(frozen=True)
class DemoOperation:
    days_ago: int
    kind: str
    name: str
    amount: int
    category: str
    counterparty: str
    payment: str
    cost: int = 0


OPERATIONS = (
    DemoOperation(
        29,
        "income",
        "Lenovo ThinkPad T14 savdosi",
        7_800_000,
        "Noutbuk savdosi",
        "Akmal Rasulov",
        "card",
        5_900_000,
    ),
    DemoOperation(
        28, "expense", "Instagram reklama kampaniyasi", 1_250_000, "Marketing", "Meta Ads", "card"
    ),
    DemoOperation(
        27,
        "income",
        "HP EliteBook 840 G8 savdosi",
        6_400_000,
        "Noutbuk savdosi",
        "Diyorbek Karimov",
        "cash",
        4_700_000,
    ),
    DemoOperation(
        26,
        "income",
        "Dell Latitude 7420 savdosi",
        7_200_000,
        "Noutbuk savdosi",
        "Nodira Aliyeva",
        "transfer",
        5_300_000,
    ),
    DemoOperation(
        25,
        "expense",
        "Buyurtmalarni yetkazib berish",
        420_000,
        "Logistika",
        "Express Delivery",
        "cash",
    ),
    DemoOperation(
        24,
        "income",
        "MacBook Air M1 savdosi",
        10_800_000,
        "Noutbuk savdosi",
        "Sardor Qodirov",
        "card",
        8_600_000,
    ),
    DemoOperation(
        23, "expense", "Ofis internet to‘lovi", 390_000, "Aloqa", "Uztelecom", "transfer"
    ),
    DemoOperation(
        22,
        "income",
        "Acer Aspire 5 savdosi",
        5_400_000,
        "Noutbuk savdosi",
        "Malika Usmonova",
        "cash",
        3_900_000,
    ),
    DemoOperation(
        21,
        "income",
        "ASUS Vivobook 15 savdosi",
        6_200_000,
        "Noutbuk savdosi",
        "Jamshid Ergashev",
        "card",
        4_500_000,
    ),
    DemoOperation(
        20, "expense", "Ofis ijara to‘lovi", 6_500_000, "Ijara", "Business Center", "transfer"
    ),
    DemoOperation(
        19,
        "income",
        "Lenovo IdeaPad 3 savdosi",
        4_900_000,
        "Noutbuk savdosi",
        "Aziza Nabiyeva",
        "cash",
        3_550_000,
    ),
    DemoOperation(
        18,
        "income",
        "HP ProBook 450 G8 savdosi",
        6_800_000,
        "Noutbuk savdosi",
        "Rustam Hakimov",
        "transfer",
        5_050_000,
    ),
    DemoOperation(
        17,
        "expense",
        "Noutbuk diagnostikasi va ta’miri",
        780_000,
        "Ta’mirlash",
        "Tech Service",
        "card",
    ),
    DemoOperation(
        16,
        "income",
        "Dell Precision 5560 savdosi",
        12_500_000,
        "Noutbuk savdosi",
        "Farrux Ismoilov",
        "transfer",
        9_800_000,
    ),
    DemoOperation(
        15,
        "income",
        "MacBook Pro 2020 savdosi",
        12_200_000,
        "Noutbuk savdosi",
        "Zarina Tursunova",
        "card",
        9_750_000,
    ),
    DemoOperation(
        14, "expense", "Google qidiruv reklamasi", 1_100_000, "Marketing", "Google Ads", "card"
    ),
    DemoOperation(
        13,
        "income",
        "Lenovo ThinkBook 15 savdosi",
        6_100_000,
        "Noutbuk savdosi",
        "Bekzod Yusupov",
        "cash",
        4_400_000,
    ),
    DemoOperation(
        12,
        "income",
        "HP ZBook Firefly savdosi",
        9_600_000,
        "Noutbuk savdosi",
        "Kamola Sobirova",
        "transfer",
        7_300_000,
    ),
    DemoOperation(
        11, "expense", "Kommunal xizmatlar", 690_000, "Kommunal", "Hududiy tarmoqlar", "transfer"
    ),
    DemoOperation(
        10,
        "income",
        "Dell Latitude 5410 savdosi",
        5_700_000,
        "Noutbuk savdosi",
        "Oybek Hamidov",
        "card",
        4_100_000,
    ),
    DemoOperation(
        9,
        "income",
        "ASUS ZenBook 14 savdosi",
        8_900_000,
        "Noutbuk savdosi",
        "Shahnoza Rahimova",
        "cash",
        6_750_000,
    ),
    DemoOperation(
        8, "expense", "Sotuv menejeri oyligi", 4_800_000, "Ish haqi", "Xodimlar", "transfer"
    ),
    DemoOperation(
        7,
        "income",
        "Acer Swift 3 savdosi",
        6_500_000,
        "Noutbuk savdosi",
        "Alisher Murodov",
        "card",
        4_850_000,
    ),
    DemoOperation(
        6,
        "income",
        "Lenovo X1 Carbon savdosi",
        9_900_000,
        "Noutbuk savdosi",
        "Mohira Salimova",
        "transfer",
        7_650_000,
    ),
    DemoOperation(
        5, "expense", "Qadoqlash materiallari", 340_000, "Ofis xarajati", "Pack Market", "cash"
    ),
    DemoOperation(
        4,
        "income",
        "HP EliteBook 850 G7 savdosi",
        6_900_000,
        "Noutbuk savdosi",
        "Sanjar Olimov",
        "cash",
        5_100_000,
    ),
    DemoOperation(
        3, "expense", "Kuryer xizmatlari", 510_000, "Logistika", "Yandex Delivery", "card"
    ),
    DemoOperation(
        2,
        "income",
        "Dell XPS 13 savdosi",
        11_400_000,
        "Noutbuk savdosi",
        "Madina Xolmatova",
        "transfer",
        8_950_000,
    ),
    DemoOperation(
        1,
        "expense",
        "Hisobot davri soliq to‘lovi",
        2_250_000,
        "Soliq",
        "Soliq qo‘mitasi",
        "transfer",
    ),
    DemoOperation(
        0,
        "income",
        "ASUS TUF Gaming F15 savdosi",
        10_600_000,
        "Noutbuk savdosi",
        "Temur Raxmonov",
        "card",
        8_100_000,
    ),
)


class DemoParser:
    def __init__(self) -> None:
        self.current: ParsedMessage | None = None

    def parse(self, _text: str, *, today: date) -> ParsedMessage:
        del today
        if self.current is None:
            raise RuntimeError("Demo parser payload berilmagan")
        return self.current


def parsed(operation: DemoOperation, transaction_date: date) -> ParsedMessage:
    breakdown = {"cash_uzs": 0, "card_uzs": 0, "transfer_uzs": 0}
    breakdown[f"{operation.payment}_uzs"] = operation.amount
    return ParsedMessage.from_dict(
        {
            "transaction_date": transaction_date.isoformat(),
            "currency": "UZS",
            "entries": [
                {
                    "kind": operation.kind,
                    "amount_uzs": operation.amount,
                    "payment_method": operation.payment,
                    "payment_breakdown": breakdown,
                    "cost_uzs": operation.cost,
                    "category": operation.category,
                    "counterparty": operation.counterparty,
                    "note": f"[DEMO] {operation.name}",
                }
            ],
            "new_customer_count": 1 if operation.kind == "income" else 0,
            "needs_clarification": False,
            "clarification_question": None,
            "missing_fields": [],
            "confidence": 1.0,
        }
    )


def load_environment(env_file: Path | None) -> None:
    if env_file is None:
        return
    for key, value in dotenv_values(env_file).items():
        if value is not None:
            os.environ[key] = value


def main() -> None:
    parser_cli = argparse.ArgumentParser()
    parser_cli.add_argument("--apply", action="store_true", help="Yozuvlarni saqlash")
    parser_cli.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    parser_cli.add_argument("--env-file", type=Path)
    args = parser_cli.parse_args()

    load_environment(args.env_file)
    settings = Settings.from_env()
    if not args.apply:
        print(f"dry_run=true operations={len(OPERATIONS)} end_date={args.end_date}")
        return

    repository = SQLiteDraftRepository(settings.db_path)
    writer = (
        GoogleSheetsWriter(
            spreadsheet_id=settings.spreadsheet_id or "",
            service_account_file=settings.service_account_file,
            service_account_json=settings.service_account_json,
        )
        if settings.sheet_mode == "google"
        else InMemorySheetWriter()
    )
    demo_parser = DemoParser()
    service = MoliyaService(
        repository=repository,
        parser=demo_parser,
        sheet_writer=writer,
        allowed_actors=settings.allowed_actors,
        report_reader=writer if isinstance(writer, GoogleSheetsWriter) else None,
    )
    created = already_present = written_rows = 0
    for index, operation in enumerate(OPERATIONS, start=1):
        transaction_date = args.end_date - timedelta(days=operation.days_ago)
        source_id = f"demo:{args.end_date.isoformat()}:v1:{index:02d}"
        existing = repository.get_by_source(settings.web_actor_id, source_id)
        demo_parser.current = parsed(operation, transaction_date)
        draft = service.create_draft(
            actor_id=settings.web_actor_id,
            source_id=source_id,
            text=f"[DEMO] {operation.name}",
            received_at=datetime.combine(transaction_date, time(12), tzinfo=UTC),
        )
        result = service.confirm(actor_id=settings.web_actor_id, draft_id=draft.id)
        already_present += int(existing is not None)
        created += int(existing is None)
        written_rows += result.written_rows
    print(
        f"seed=ok operations={len(OPERATIONS)} created={created} "
        f"already_present={already_present} sheet_rows={written_rows}"
    )


if __name__ == "__main__":
    main()
