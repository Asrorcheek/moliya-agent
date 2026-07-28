# Moliya AI Agent

Telegram/Hermes orqali kelgan moliyaviy xabarni strukturaga ajratib, egadan aniq
tasdiq olgandan keyingina bitta Google Sheets fayliga yozadigan MVP.

## Hozir ishlaydigan qism

- Matndan bir yoki bir nechta moliyaviy entry ajratish.
- `pending → confirmed/rejected` tasdiqlash holati.
- `actor_id + source_id` va `Entry ID` orqali dublikat himoyasi.
- SQLite audit/draft bazasi.
- Har oy bir xil workbook ichida `Tranzaksiyalar <Oy> <Yil>` tabini yaratish.
- Google Sheets'ga normalized ledger qatorlarini yozish.
- Oylik tushum, vazvrat, tannarx, xarajat va foyda xulosasi.
- Hermes uchun `/moliya` skill va stdlib HTTP client.

Ovoz, screenshot, yakuniy “Apteka Biznes” ustun mappingi, mijozlar bazasi,
PostgreSQL va to'liq Balance/Cash Flow keyingi bosqichda.

## Muhim arxitektura qoidasi

AI faqat matnni JSON sxemaga ajratadi. AI Google Sheets'ga bevosita yozmaydi.
Yozish oddiy kod orqali, faqat aniq tasdiqdan keyin amalga oshadi.

```text
Telegram → Hermes → Moliya backend
                         ├─ OpenAI parser
                         ├─ draft/audit bazasi
                         └─ Google Sheets writer
```

## Lokal test

Core testlar tashqi dependency va API kalitisiz ishlaydi:

```bash
cd /home/alex/Downloads/moliya-agent
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Lokal API ishga tushirish

Docker bilan:

```bash
cd /home/alex/Downloads/moliya-agent
docker compose up --build
```

Yoki Python virtual environment bilan:

```bash
cd /home/alex/Downloads/moliya-agent
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
set -a
. ./.env
set +a
.venv/bin/moliya-api
```

Default holatda `rule` parser va `memory` writer ishlaydi. Bu faqat lokal wiring
testi; productionda quyidagilarni almashtirish kerak:

```dotenv
ENVIRONMENT=production
MOLIYA_INTERNAL_TOKEN=<kamida-24-belgili-tasodifiy-secret>
MOLIYA_ALLOWED_ACTORS=hermes
MOLIYA_PARSER_MODE=openai
OPENAI_API_KEY=<server-secret>
OPENAI_MODEL=gpt-5.6-luna
OPENAI_REASONING_EFFORT=none
MOLIYA_SHEET_MODE=google
GOOGLE_SPREADSHEET_ID=<fixed-workbook-id>
GOOGLE_SERVICE_ACCOUNT_JSON=<single-line-json-secret>
```

Secretlarni repo, Telegram yoki chatga qo'ymang.

## API oqimi

### Draft

```bash
curl -sS http://127.0.0.1:8088/v1/drafts \
  -H "Content-Type: application/json" \
  -H "X-Moliya-Token: $MOLIYA_INTERNAL_TOKEN" \
  -d '{
    "actor_id": "hermes",
    "source_id": "telegram-message-123",
    "text": "Bugun 2 mln tushum, 500 ming xarajat",
    "received_at": null
  }'
```

### Tasdiqlash

```bash
curl -sS -X POST http://127.0.0.1:8088/v1/drafts/DRAFT_ID/confirm \
  -H "Content-Type: application/json" \
  -H "X-Moliya-Token: $MOLIYA_INTERNAL_TOKEN" \
  -d '{"actor_id":"hermes"}'
```

### Oylik hisobot

```bash
curl -sS \
  "http://127.0.0.1:8088/v1/reports/monthly?actor_id=hermes&month=2026-07" \
  -H "X-Moliya-Token: $MOLIYA_INTERNAL_TOKEN"
```

## Hermes skillni ulash

Backend va skillni VM'ga ko'chirgandan keyin:

```bash
mkdir -p /home/busin/.hermes/skills/business
cp -R hermes-skill/moliya /home/busin/.hermes/skills/business/moliya
```

`/home/busin/.hermes/.env` yoki Hermes service environmentiga:

```dotenv
MOLIYA_AGENT_URL=http://127.0.0.1:8088
MOLIYA_INTERNAL_TOKEN=<backend-bilan-bir-xil-secret>
```

So'ng yangi Hermes sessiyasida:

```text
/moliya Bugun 2 mln tushum, 500 ming rasxod
```

Hermes preview ko'rsatadi. Faqat foydalanuvchi `ha` degandan keyin confirm
buyrug'ini chaqiradi.

## Google Sheets

MVP bitta `GOOGLE_SPREADSHEET_ID` bilan ishlaydi va yangi workbook yaratmaydi.
Har oy shu workbook ichida quyidagi normalized ledger tabini yaratadi:

```text
Tranzaksiyalar Iyul 2026
```

Ustunlar:

```text
Entry ID | Sana | Turi | Summa | Naqd | Karta | O'tkazma | Tan narx |
Kategoriya | Kontragent | Izoh | Source ID | Tasdiqlagan | Tasdiqlangan vaqt
```

`Apteka Biznes` nusxasi kelgach, shu normalized ledgerdan mavjud Kassa/P&L
shabloniga mapping qilinadi. Formulali hisobot tabini AI emas, tasdiqlangan
shablon boshqaradi.

## VM deployment tartibi

1. Loyihani `/home/busin/moliya-agent` ga joylash.
2. `.venv` yaratib `pip install -e .` bajarish.
3. Secretlarni `/home/busin/.hermes/moliya-agent.env` ga yozish.
4. `deploy/moliya-agent.service` ni user systemd katalogiga o'rnatish.
5. Backend health checkni tekshirish.
6. Hermes skillni o'rnatish.
7. Avval test workbookda end-to-end sinash.
8. Faqat acceptance testlardan keyin haqiqiy workbook IDga o'tish.

## Keyingi acceptance testlar

- Bir xil Telegram `source_id` ikki marta yozilmaydi.
- Tasdiqsiz Google Sheets write bo'lmaydi.
- `ha` ikki marta yuborilsa dublikat qator paydo bo'lmaydi.
- Noto'g'ri yoki noaniq summa clarification qaytaradi.
- Faqat ruxsat berilgan Telegram ID Hermes gatewaydan o'tadi.
- Test workbookdan tashqarida yangi fayl yaratilmaydi.
