---
name: moliya
description: Telegramdagi moliyaviy matnni draftga aylantirish, egadan tasdiq olish, Google Sheets'ga yozish va oylik hisobotni ko'rish
version: 0.1.0
author: Mohir
license: Proprietary
platforms: [linux]
metadata:
  hermes:
    tags: [finance, telegram, google-sheets, uzbek]
required_environment_variables:
  - name: MOLIYA_AGENT_URL
    prompt: "Moliya backend URL"
    required_for: "Backend bilan aloqa"
  - name: MOLIYA_INTERNAL_TOKEN
    prompt: "Moliya backend internal token"
    required_for: "Backend autentifikatsiyasi"
---

# Moliya

## Qachon ishlatish

Foydalanuvchi tushum, xarajat, vazvrat, tannarx, qarz yoki moliyaviy hisobot haqida
yozganda ushbu skillni ishlat.

## Asosiy qoida

Moliyaviy yozuvni hech qachon foydalanuvchining aniq tasdig'isiz Google Sheets'ga
yozma. Birinchi xabarda faqat draft yarat va previewni ko'rsat.

Tasdiq deb faqat quyidagilarni qabul qil:

- `ha`
- `tasdiqlayman`
- `yoz`
- `to'g'ri`

Noaniq javob, yangi summa yoki tuzatish kelsa eski draftni tasdiqlama. Uni rad etib,
yangi to'liq draft yarat.

## Buyruqlar

Skill katalogi Hermes tomonidan `${HERMES_SKILL_DIR}` ga almashtiriladi.

### 1. Draft yaratish

```bash
python3 ${HERMES_SKILL_DIR}/scripts/moliya_client.py draft \
  --actor hermes \
  --text "<foydalanuvchining aynan o'z matni>"
```

Natijadagi `DRAFT_ID`ni shu suhbat uchun eslab qol. Foydalanuvchiga `PREVIEW`
qismini o'zgartirmasdan ko'rsat.

### 2. Tasdiqlash

Faqat foydalanuvchi yuqoridagi aniq tasdiqlardan birini yuborganda:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/moliya_client.py confirm \
  --actor hermes \
  --draft-id "<oxirgi pending DRAFT_ID>"
```

Muvaffaqiyatli bo'lsa nechta qator yozilganini ayt.

### 3. Rad etish

```bash
python3 ${HERMES_SKILL_DIR}/scripts/moliya_client.py reject \
  --actor hermes \
  --draft-id "<DRAFT_ID>"
```

### 4. Oylik hisobot

```bash
python3 ${HERMES_SKILL_DIR}/scripts/moliya_client.py report \
  --actor hermes \
  --month "YYYY-MM"
```

## Xavfsizlik chegaralari

- API token yoki service account ma'lumotini javobda ko'rsatma.
- Backenddan tashqarida summalarni o'zing hisoblab Google Sheets'ga yozma.
- Terminal orqali Google Sheets credentialini o'qima yoki chop etma.
- Tasdiqlangan yozuvni o'chirma; tuzatish uchun keyinchalik reversal oqimi ishlatiladi.
- Backend xato qaytarsa yozildi deb aytma. Xatoni qisqa ayt va draft IDni saqla.
- Screenshot yoki ovozdagi raqamlarni preview orqali albatta egaga tekshirtir.

## Tekshirish

Backend holati:

```bash
python3 ${HERMES_SKILL_DIR}/scripts/moliya_client.py health
```

`status=ok` bo'lmasa moliyaviy yozuv boshlama.
