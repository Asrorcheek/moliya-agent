# Moliya AI Agent

Telegram/Hermes orqali kelgan moliyaviy xabarni strukturaga ajratib, egadan aniq
tasdiq olgandan keyingina bitta Google Sheets fayliga yozadigan MVP.

## Hozir ishlaydigan qism

- Matndan bir yoki bir nechta moliyaviy entry ajratish.
- `pending → confirmed/rejected` tasdiqlash holati.
- `actor_id + source_id` va `Entry ID` orqali dublikat himoyasi.
- SQLite audit/draft bazasi.
- Bitta workbook ichidagi `Operatsiyalar` tabiga normalized ledger qatorlarini yozish.
- Mavjud P&L va Cash Flow shablonini ledger bilan bog'lash.
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
cd /home/alex/busin/pet-project-2/skills/moliya-agent
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

Dependencylar o'rnatilgach, disposable SQLite bazasi va memory writer bilan
lokal API + Hermes client acceptance testi:

```bash
cd /home/alex/busin/pet-project-2/skills/moliya-agent
.venv/bin/python scripts/acceptance_test_local.py
```

## Lokal API ishga tushirish

Docker bilan:

```bash
cd /home/alex/busin/pet-project-2/skills/moliya-agent
docker compose up --build
```

Yoki Python virtual environment bilan:

```bash
cd /home/alex/busin/pet-project-2/skills/moliya-agent
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
set -a
. ./.env
set +a
.venv/bin/moliya-api
```

## Web interfeys

Responsive React/TypeScript interfeysi `app/` katalogida joylashgan:

```bash
cd app
npm install
npm run dev
```

Production build:

```bash
npm run build
```

`MOLIYA_WEB_DIST_DIR` `app/dist` katalogiga ko'rsatilsa, FastAPI production
frontendni, SPA deep-linklarni va API'ni bitta origin orqali serve qiladi.
Developmentda Vite `/api` so'rovlarini lokal `127.0.0.1:8088` backendga proxy
qiladi.

Hozirgi public deployment:

```text
https://moliya.34-29-145-102.sslip.io
```

Web interfeys quyidagi real backend endpointlaridan foydalanadi:

```text
POST/GET/DELETE /v1/session
GET /v1/drafts
GET /v1/drafts/{draft_id}
GET /v1/transactions
GET /v1/reports/dashboard
GET /v1/audit-events
```

Audit hodisalari SQLite'da doimiy saqlanadi. Hozir yoziladigan hodisalar:
`draft.created`, `draft.confirmed`, `draft.rejected` va `sheet.write_failed`.
Audit javoblari `limit`/`offset` paginationini qo'llaydi.

Brauzer ichki `X-Moliya-Token`ni olmaydi. Login backend imzolagan `HttpOnly`,
`SameSite=Strict` cookie yaratadi. Productionda `MOLIYA_WEB_PASSWORD`,
`MOLIYA_SESSION_SECRET` va `MOLIYA_SESSION_COOKIE_SECURE=true` majburiy tarzda
server secretlarida sozlanadi. `MOLIYA_WEB_ACTOR_ID` qiymati
`MOLIYA_ALLOWED_ACTORS` ro'yxatida bo'lishi kerak.

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

GCloud VM uchun takrorlanadigan deploy:

```bash
./scripts/deploy_gcloud.sh
```

Skript quyidagilarni avtomatik bajaradi:

1. `app/` uchun clean `npm ci`, typecheck va production build.
2. Backend source va frontend `dist` uchun checksumli release yaratish.
3. Release'ni `pet-project-2` VM'ga yuborish.
4. Source, `.env` va SQLite bazaning timestamped backupini olish.
5. Yangi kodni staging konfiguratsiyada validate qilish.
6. Faqat validationdan keyin backend va Telegram botni qisqa to'xtatish.
7. Source va web buildni rsync qilish, servicelarni qayta ishga tushirish.

Default instance va zonani kerak bo'lsa environment orqali almashtirish mumkin:

```bash
MOLIYA_GCLOUD_INSTANCE=pet-project-2 \
MOLIYA_GCLOUD_ZONE=us-central1-c \
./scripts/deploy_gcloud.sh
```

Remote secretlar `/home/busin/.hermes/moliya-agent.env` ichida qoladi va release
paketiga kiritilmaydi. Backup'lar `/home/busin/backups/` ostida saqlanadi.

## Keyingi acceptance testlar

- Bir xil Telegram `source_id` ikki marta yozilmaydi.
- Tasdiqsiz Google Sheets write bo'lmaydi.
- `ha` ikki marta yuborilsa dublikat qator paydo bo'lmaydi.
- Noto'g'ri yoki noaniq summa clarification qaytaradi.
- Faqat ruxsat berilgan Telegram ID Hermes gatewaydan o'tadi.
- Test workbookdan tashqarida yangi fayl yaratilmaydi.
