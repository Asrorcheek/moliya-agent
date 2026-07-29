# Moliya AI Agent

Telegram/Hermes orqali kelgan moliyaviy xabarni strukturaga ajratib, egadan aniq
tasdiq olgandan keyingina bitta Google Sheets fayliga yozadigan MVP.

## Hozir ishlaydigan qism

- Matndan bir yoki bir nechta moliyaviy entry ajratish.
- `pending → confirmed/rejected` tasdiqlash holati.
- `actor_id + source_id` va `Entry ID` orqali dublikat himoyasi.
- SQLite audit/draft bazasi.
- Bitta workbook ichidagi `Operatsiyalar` tabiga normalized ledger qatorlarini yozish.
- Mavjud Kassa, P&L va Cash Flow shablonini ledger bilan bog'lash.
- Oylik tushum, vazvrat, tannarx, xarajat va foyda xulosasi.
- Hermes uchun `/moliya` skill va stdlib HTTP client.

Ovoz, screenshot, USD operatsiyalarining yakuniy kurs qoidasi, mijozlar bazasi,
PostgreSQL va to'liq Balance/Qarzdorlik avtomatizatsiyasi keyingi bosqichda.

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
Tasdiqlangan barcha operatsiyalar shu workbook ichidagi bitta normalized ledger
tabiga yoziladi:

```text
Operatsiyalar
```

Ustunlar:

```text
Entry ID | Sana | Oy | Turi | Summa (UZS) | Naqd | Karta | O'tkazma |
Tan narx | Kategoriya | Kontragent | Izoh | Source ID | Tasdiqlagan |
Tasdiqlangan vaqt | Valyuta | Summa (valyutada) | Kurs | Holat |
Bekor qilingan Entry ID
```

Ishchi Excel nusxasi: `/home/alex/Downloads/Apteka_Moliya_v2.xlsx`.
Asl `shablon .xlsx` o'zgartirilmagan. Ishchi nusxaga `Sozlamalar` va
`Operatsiyalar` varaqlari qo'shilgan; P&L hamda Cash Flow formulalari ledgerga
ulangan. Formulali hisobot tablarini AI emas, tasdiqlangan shablon boshqaradi.

Shablonni qayta tayyorlash skripti:

```text
scripts/prepare_excel_template.py
```

U mavjud `Operatsiyalar` qatorlarini o'chirmaydi.

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
