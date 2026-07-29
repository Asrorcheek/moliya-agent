# Apteka moliya shabloni — audit va tuzatishlar

## Fayllar

- Asl fayl: `/home/alex/Downloads/shablon .xlsx`
- Ishchi nusxa: `/home/alex/Downloads/Apteka_Moliya_v2.xlsx`
- Asl faylga o'zgartirish kiritilmagan.

## Aniqlangan holat

Asl shablonda 14 ta varaq va 614 ta formula bor edi. Dorixona kassasi bilan
birga eski gilam/aksessuar savdosi tarixiy varaqlari ham saqlangan. Ular
o'chirilmadi va avvalgi kabi yashirin arxiv holatida qoldirildi.

Asosiy texnik muammolar:

- Google Sheets'ga bog'langan tashqi `IMPORTRANGE` Excel'da ishlamas edi.
- P&L normasida 15 ta `#REF!` formula bor edi.
- Qarzdorlikning `N1367` katagida bitta buzilgan `#REF!` formula bor edi.
- P&L rentabellik ustunida nolga bo'lish sabab 10 ta `#DIV/0!` natija bor edi.
- Kiritish uchun yagona normalized operatsiyalar ledgeri yo'q edi.
- Data validation yo'q edi.
- Qarz undirish va kreditor qarz to'lovi P&L bilan aralashib ketishi mumkin edi.

## Kiritilgan tuzatishlar

- `Sozlamalar` varag'i qo'shildi.
- `Operatsiyalar` varag'i qo'shildi.
- `Operatsiyalar` uchun 20 ustunli barqaror sxema, filter va 4 ta validation
  qoidasi qo'shildi.
- Tashqi valyuta kursi bog'lanishi `Sozlamalar`dagi qo'lda boshqariladigan
  USD kursiga almashtirildi.
- P&L norma formulalari `Sozlamalar`dagi norma jadvaliga bog'landi.
- P&L rentabellik formulalari nolga bo'lishdan himoyalandi.
- P&L daromad, tannarx va asosiy operatsion xarajatlar `Operatsiyalar`
  ledgeriga bog'landi.
- Cash Flow'ning naqd, karta va o'tkazma kirim-chiqim yig'indilari ledgerga
  bog'landi.
- Qarz undirish faqat Cash Flow kirimiga, yetkazib beruvchi qarzi to'lovi
  faqat Cash Flow chiqimiga ta'sir qiladi; ikkalasi ham P&L daromad/xarajati
  sifatida hisoblanmaydi.
- Agent Google Sheets writeri aynan `Operatsiyalar!A:T` sxemasiga moslashtirildi.
- Yashirin tarixiy varaqlar saqlab qolindi.

## Tekshiruv natijasi

- `.xlsx` ZIP yaxlitligi: xatosiz.
- Buzilgan formula reference: 0.
- Tashqi/qo'llab-quvvatlanmaydigan formula: 0.
- `Operatsiyalar` data validation qoidalari: 4.
- Python core testlari: 11/11 muvaffaqiyatli.
- Excel formula smoke testi:
  - 2 000 000 UZS tushum;
  - 500 000 UZS tannarx;
  - 300 000 UZS ma'muriy xarajat;
  - 1 000 000 UZS qarz undirish;
  - 400 000 UZS yetkazib beruvchi qarzi to'lovi.

Kutilgan natijalar olindi:

- P&L sof foyda: 1 200 000 UZS.
- Cash Flow kirim: 3 000 000 UZS.
- Cash Flow chiqim: 700 000 UZS.

## Hali mijoz tasdiqlashi kerak

- USD kursining manbasi va qaysi sana kursi ishlatilishi.
- Uch foydalanuvchining Telegram ID va rollari.
- Boshlang'ich naqd, bank, tovar, debitor va kreditor qoldiqlar.
- Balance va Qarzdorlik uchun yakuniy buxgalteriya formulalari.
- Tarixiy dorixona ma'lumotlarini yangi `Operatsiyalar` ledgeriga ko'chirish
  kerakmi yoki yangi sanadan toza boshlanadimi.
