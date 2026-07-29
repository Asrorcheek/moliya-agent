# Moliya AI Agent — talablarni yakuniy tasdiqlash

Ushbu hujjat mijoz bilan to'ldirilgach, loyiha scope'i va qabul mezonlari
muzlatiladi. O'zgartirishlar keyin alohida change request sifatida baholanadi.

## 1. Hozircha tasdiqlangan talablar

- Agent Telegram orqali ishlaydi.
- Hermes Telegram gateway sifatida ishlatiladi.
- AI provayderi OpenAI API.
- Matn bir yoki bir nechta moliyaviy operatsiyaga ajratiladi.
- Google Sheets'ga yozishdan oldin egadan aniq tasdiq olinadi.
- Har safar yangi workbook yaratilmaydi; bitta fixed workbook ID ishlatiladi.
- Tasdiqlangan barcha operatsiyalar bitta `Operatsiyalar` ledgerida saqlanadi.
- Mavjud oylik Kassa va hisobot varaqlari ledgerdan avtomatik jamlanadi.
- API kalitlari va Google credentiallar server secretlarida saqlanadi.
- Faqat allowlistdagi Telegram foydalanuvchilar agentdan foydalana oladi.
- Har bir draft, tasdiq, rad etish va yozuv audit-logda saqlanadi.
- Hisob valyutalari UZS va USD.
- Hisob vaqti Asia/Tashkent (UTC+5).
- Tranzaksiyalar alohida ledgerda saqlanadi, Kassa kunlik avtomatik jamlanadi.
- To'lov turi aytilmasa agent aniqlashtirish so'raydi.
- Tasdiqlangan xato reversal va yangi to'g'ri yozuv orqali tuzatiladi.
- Botdan 3 foydalanuvchi foydalanadi; rollari hali aniqlanmagan.
- Hozir integratsiya qilinadigan boshqa kompaniya dasturi yo'q.

## 2. Mijozdan olinadigan fayl

2026-07-28 kuni `shablon .xlsx` haqiqiy moliyaviy shablon sifatida olindi.
Unda 14 ta original varaq, jumladan Kassa, P&L, Cash Flow, Balance,
Qarzdorlik va yordamchi varaqlar bor.

- [x] Formulalar va original formatlar saqlangan
- [x] Kamida bir oylik namunaviy ma'lumot qoldirilgan
- [x] Kassa, P&L, Cash Flow, Balance va yordamchi tablar saqlangan
- [x] AI faqat `Operatsiyalar` varag'iga yozadi
- [x] Formulali hisobot varaqlari AI uchun faqat o'qish
- [x] Asl fayl o'zgartirilmagan

Ishchi nusxa: `/home/alex/Downloads/Apteka_Moliya_v2.xlsx`.
Unga `Sozlamalar` va `Operatsiyalar` varaqlari qo'shildi. Buzilgan tashqi
`IMPORTRANGE`, P&L'dagi `#REF!` formulalar, qarzdorlikdagi uzoq qatordagi
`#REF!` va rentabellikdagi `#DIV/0!` natijalar tuzatildi.

## 3. Mijoz tasdiqlashi kerak bo'lgan asosiy qarorlar

### 3.1. Asosiy parametrlar

- Kompaniya nomi:
- Asosiy valyutalar: UZS va USD
- Hisobot uchun asosiy/base valyuta: aniqlanmagan
- Hisob sanasi va vaqti: Asia/Tashkent (UTC+5)
- Bir Telegram botdan foydalanadigan odamlar: 3
- Foydalanuvchi rollari va huquqlari: aniqlanmagan

USD uchun ochiq savollar:

- USD alohida kassa sifatida yuritiladimi:
- Hisobot UZS'ga konvertatsiya qilinadimi:
- Kurs manbasi:
- Qaysi sana kursi olinadi:
- Kursni foydalanuvchi qo'lda bera oladimi:

### 3.2. Sheets'dagi qator modeli

Quyidagilardan bittasi tanlanadi:

- [ ] Har bir tasdiqlangan operatsiya — alohida qator
- [ ] Har bir kun — bitta jamlangan qator
- [x] Ikkalasi: tranzaksiyalar alohida ledgerda, kunlik Kassa avtomatik jamlanadi

Tavsiya: uchinchi variant. U audit, P&L, Cash Flow va Balance uchun to'g'riroq.

### 3.3. Operatsiya turlari

Keraklilarni belgilang:

- [x] Tushum
- [x] Vazvrat
- [x] Xarajat
- [x] Tannarx
- [x] Debitor qarz
- [x] Debitor qarz to'lovi
- [x] Kreditor qarz
- [x] Kreditor qarz to'lovi
- [ ] Kassaga pul kiritish
- [ ] Kassadan pul olish
- [ ] Bank va kassa o'rtasida o'tkazma
- [ ] Egadan kapital kiritish
- [ ] Dividend/pul yechib olish
- [ ] Boshqa:

### 3.4. To'lov turlari

- [x] Naqd
- [x] Karta
- [x] Bank o'tkazmasi
- [x] Aralash to'lov
- [ ] Boshqa:

Muhim qoida:

- [ ] `Tushum = Naqd + Karta + O'tkazma` bo'lishi shart
- [x] To'lov turi aytilmasa agent aniqlashtirish so'raydi
- [ ] To'lov turi aytilmasa `Noma'lum` sifatida draft ko'rsatishi mumkin

### 3.5. Sana qoidalari

- `"bugun"` qaysi timezone bo'yicha:
- Sana aytilmasa bugungi sana olinadimi: ha / yo'q
- Oldingi oyga kechikib yozish mumkinmi: ha / yo'q
- Yopilgan oyga yozish mumkinmi: ha / yo'q
- Oy yopilishi sanasi/qoidasi:

### 3.6. Tasdiqlash va tuzatish

Tasdiq sifatida qabul qilinadigan javoblar:

- [ ] ha
- [ ] tasdiqlayman
- [ ] yoz
- [ ] to'g'ri
- [ ] boshqa:

Tasdiqlangan xatoni tuzatish:

- [ ] Eski yozuvni tahrirlash
- [x] Reversal yozuvi + yangi to'g'ri yozuv

Tavsiya: reversal, chunki audit tarixi saqlanadi.

### 3.7. Xarajat kategoriyalari

Yakuniy ro'yxat:

1. Ijara
2. Oylik
3. Kommunal
4. Soliq
5. Marketing
6. Yetkazib berish
7. Boshqa:

Agent yangi kategoriya yarata oladimi: ha / yo'q

### 3.8. Mijoz va qarzdorlik

- Mijoz uchun majburiy maydonlar:
- Bir xil mijozni aniqlash kaliti: telefon / ID / ism / boshqa
- Qarz limiti bormi:
- Qarz muddati bormi:
- Qisman to'lov qanday yuritiladi:
- Debitor va kreditor alohida tablarda bo'ladimi:

### 3.9. Hisobot ta'riflari

Mijoz/buxgalter quyidagi formulalarni yozma tasdiqlaydi:

- Sof tushum =
- Yalpi foyda =
- Sof foyda =
- Operatsion Cash Flow =
- Kassa qoldig'i =
- Debitor qoldiq =
- Kreditor qoldiq =

Balance uchun boshlang'ich qoldiqlar sanasi:

- Naqd:
- Bank:
- Tovar/ombor:
- Debitor:
- Kreditor:
- Asosiy vositalar:
- Kapital:
- Boshqa aktiv/majburiyat:

### 3.10. Mavjud dastur integratsiyasi

- Dastur nomi: mavjud dastur yo'q
- API/Webhook/Database integratsiyasi: MVP scope'dan chiqarildi
- Asosiy source of truth: backend audit bazasi + tasdiqlangan
  `Operatsiyalar` moliyaviy ledgeri

## 4. Namunaviy xabarlar

Kamida 30 ta real misol va kutilgan natija kerak.

| # | Telegram xabari | Kutilgan operatsiya | Sheets'dagi kutilgan natija |
|---|---|---|---|
| 1 | Bugun 2 mln tushum, 500 ming xarajat | 2 ta entry | Mijoz to'ldiradi |
| 2 |  |  |  |
| 3 |  |  |  |

Quyidagi holatlar albatta bo'lsin:

- Oddiy tushum
- Bir xabarda tushum va xarajat
- Naqd/karta/o'tkazma bo'linishi
- Vazvrat
- Tannarx
- Debitor va kreditor
- Noaniq summa
- Sana aytilmagan xabar
- Oldingi sana
- Xato va tuzatish
- Bir xil xabar ikki marta kelishi

## 5. Scope bosqichlari

### MVP

- Matn
- Draft va tasdiqlash
- Normalized tranzaksiyalar ledgeri
- Google Sheets test workbook
- Oylik qisqa hisobot
- 3 foydalanuvchi va role-based ruxsat

### Keyingi bosqich

- Ovoz
- Screenshot
- Mijozlar bazasi
- Debitor/kreditor
- Mavjud dastur integratsiyasi
- To'liq Balance va Qarzdorlik avtomatizatsiyasi

## 6. Talablarni muzlatish

- Mijoz vakili:
- Buxgalter:
- Developer:
- Tasdiqlangan sana:
- MVP scope tasdiqlandi: ha / yo'q
- Qo'shimcha izoh:
