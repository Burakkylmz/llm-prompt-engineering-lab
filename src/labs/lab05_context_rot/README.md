# Lab 05 — Baglam Curumesi (Context Rot)

## Ogrenme Hedefi

Baglam penceresi uzadikca, AYNI hedef bilgiye (sabit konumda) ulasma dogrulugunun nasil
degistigini olcer. "Context rot" terimi, modelin daha fazla token gormesinin otomatik
olarak daha iyi performans anlamina gelmedigini, bazen aksine kafa karisikligi veya
"bulunamadi" cevaplarina yol actigini ifade eder.

## Senaryo

Kaya Elektronik'e ait uzun, tutarli (lorem ipsum DEGIL) sentetik is metinleri icinde
gizlenmis tek bir hedef gercek (orn. bir projenin butcesi) hakkinda soru sorulur.

## Hipotez

Baglam uzunlugu arttikca (sabit konum ve sabit yanitlama sozlesmesiyle) dogru cevap verme
orani TEK DUZE AZALMAZ ama belirli bir uzunluktan sonra olculebilir sekilde duser; bu
dususun sekli (dogru -> yakin-yanilti ile karisma -> "bulunamadi") rapor edilmelidir.

**Hipotezi curutecek sonuc:** Dogruluk butun test edilen uzunluklarda (1K-32K token) sabit
kalirsa — bu GECERLI bir bulgudur ve gizlenmemelidir (spec'in yorum noktasi): bu model ve
gorev icin olculen uzunluklarda "context rot" gozlenmemis demektir.

## Bagimsiz Degisken

Toplam baglam uzunlugu: 1.000 / 4.000 / 8.000 / 16.000 / 32.000 token (tahmini). Yapilandirma
limitini (`preflight.max_input_tokens_per_request`) asan uzunluklar calistirilmaz, "skipped"
olarak kayit edilir — basarisizlik olarak SAYILMAZ.

## Kontrol Edilen Degiskenler

- Hedef gercegin baglam icindeki BAGIL konumu: her uzunlukta SABIT (%50, ortada).
- Yakin-yanilti (near-miss) yogunlugu: her uzunlukta SABIT (%10).
- Soru ifadesi: sabit.
- Dolgu metni: tutarli sentetik is metni (Kaya Elektronik ekip/proje raporlari), 2300 farkli
  cumleden olusan bir havuzdan, 32K token'a kadar AYNI cumleyi tekrarlamadan cekilir.

## Cevaplama Sozlesmesi

Model KESIN olarak cevap vermeli ya da acik bir "BULUNAMADI" tokeni dondurmeli.

## Metrikler

Dogruluk (exact match), "bulunamadi" orani, yakin-yanilti ile karisma orani, halusinasyon
orani (bilinen iki adaydan (altin/yakin-yanilti) hicbirine uymayan bir cevap), raporlanan
girdi token sayisi, en kisa uzunluga gore goreli bozulma (guven araliklariyla).

## Veri Kumesi

- `data/golden/lab05/facts.json`: 20 hedef gercek (4 tur x 5 deger), her biri kendi
  yakin-yanilti versiyonuyla.
- `data/contexts/lab05/filler.json`: 2300 farkli, kombinatoryal olarak uretilmis (ama her
  biri ayri ayri okunabilir, tutarli) dolgu cumlesi — 32K token'a rahatlikla yeter.

## Calistirma

```powershell
uv run lab-runner lab05
uv run lab-runner lab05 --replay <kayitli_live_run>
uv run lab-runner lab05 --live --config config/live.toml
```

**Fixture modu notu:** Sahte model, baglam uzunluguna gore BELIRLENMIS bir kural izler:
<=5000 token'da dogru cevap, 5000-18000 token arasinda yakin-yanilti ile karisir, >18000
token'da "BULUNAMADI" der. Bu, raporun "context rot" egrisini olcme/cizme mekanigini test
eder — GERCEK bir modelin boyle bir egri izleyecegini KANITLAMAZ.

## Katilimci Icin Okuma Rehberi

`charts/accuracy_vs_length.png` grafiginde x ekseni (log olcek) baglam uzunlugu, y ekseni
dogruluktur (Wilson guven araligi hata cubuklariyla). `comparison.md`'deki
`constraint_adherence` alaninda her uzunluk icin `exact_match`, `confused_by_near_miss`,
`not_found_reported`, `hallucinated` oranlarina ayri ayri bakin — SADECE dogrulugun dusmesi
degil, DUSUSUN NEDENI (karisma mi, reddetme mi, halusinasyon mu) onemlidir.

**Tartisma sorulari:**
1. Dogruluk dususu ani mi (bir esikten sonra) yoksa kademeli mi?
2. Model yanlis cevap verdiginde, bu daha cok "yakin-yanilti ile karisma" mi yoksa
   "tamamen halusinasyon" mu?

## Egitmen Icin Notlar

- **Beklenen vs. Olculen:** Fixture modundaki esik degerler (5000/18000 token) KEYFIDIR,
  gercek bir modelin esiklerini temsil ETMEZ. Gercek egri icin `--replay` kullanin.
  Egitmen, egitimden once `--live` ile bu lab'i calistirip kaydetmelidir.
  Kayit prosedürü icin `docs/live-smoke.md` ve `data/recordings/README.md`'ye bakin.
  Uzunluk basina ayri bir API cagrisi gerektigi icin bu lab'in canli kaydi diger labs'tan
  daha fazla token/maliyet gerektirebilir — 32K token'lik bir baglam, tek basina
  `preflight.max_estimated_tokens_per_run` limitini zorlayabilir, config'i gozden gecirin.
- **Yanlis kani:** "Daha genis baglam penceresi = her zaman daha iyi hatirlama" — bu lab
  tam olarak bunu sorgular.

## Testler

`tests/labs/test_lab05_dataset.py`, `test_lab05_conditions.py`, `test_lab05_evaluator.py`,
`tests/integration/test_lab05_cli.py` — veri kumesi minimumlarini (20 gercek, dolgu havuzu
32K token'a yetiyor), sabit konumu her uzunlukta dogrulayan, degerlendiriciyi, ve
yapilandirma limitini asan uzunluklarin basarisizlik degil "skipped" olarak kaydedildigini
dogrulayan testler icerir.
