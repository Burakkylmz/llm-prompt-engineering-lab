# Lab 06 — Lost-in-the-Middle

## Ogrenme Hedefi

Baglam SABIT uzunlukta tutuldugunda, hedef bilginin baglam icindeki KONUMUNUN (basta,
ortada, sonda) hatirlama dogrulugunu nasil etkiledigini olcer. "Lost in the middle" bulgusu:
bazi modeller baglamin basindaki ve sonundaki bilgiyi ortasindaki bilgiden daha iyi
hatirlar (U-seklinde bir dogruluk egrisi).

**Lab 05 ile farki:** Lab 05 KONUMU sabit tutup UZUNLUGU degistirir; Lab 06 UZUNLUGU sabit
tutup KONUMU degistirir. Ikisi ayri deneylerdir, veri havuzunu paylasirlar ama FARKLI
sorulari test ederler.

## Senaryo

Lab 05 ile AYNI 20 hedef gercek ve dolgu havuzu, ama her gercek artik bir "madde numarasi"
(orn. MADDE-07) ile etiketlenmis bir ic politika belgesi maddesi gibi sunulur — model hem
cevabi hem de hangi maddeyi kullandigini bildirmelidir (kanit tanimlama).

## Hipotez

Sabit ~8000 token'lik bir baglamda, hedef gercek ortaya (yakinda %25-%75) yerlestirildiginde
dogruluk, baslangica (%0) veya sona (%100) yerlestirildiginde olculenden daha dusuk olacaktir
(U-seklinde egri).

**Hipotezi curutecek sonuc:** Dogruluk butun pozisyonlarda esit veya ortada daha YUKSEK
cikarsa — bu GECERLI bir bulgudur (spec'in yorum noktasi: "etki modele, uzunluga ve goreve
gore degisir; zayif veya hic yok bir etki de mesru bir sonuctur").

## Bagimsiz Degisken

Hedef gercegin bagil konumu: %0, %25, %50, %75, %100 (5 konum, 5 kosul).

## Kontrol Edilen Degiskenler

- Toplam baglam uzunlugu: SABIT (~8000 token, her kosulda).
- Dolgu icerigi ve yakin-yanilti yogunlugu: sabit (Lab05 ile ayni havuz ve oran).
- Her hedef gercek butun 5 pozisyonda test edilir (paired design — "counterbalanced"
  gereksinimi, her olgu her pozisyonda gorunur, trivially, ayni vaka kumesi her kosulda
  kullanildigi icin).

## Metrikler

Dogruluk (pozisyona gore), exact match, kanit tanimlama (model dogru MADDE numarasini
bildirdi mi), latency.

## Calistirma

```powershell
uv run lab-runner lab06
uv run lab-runner lab06 --replay <kayitli_live_run>
uv run lab-runner lab06 --live --config config/live.toml
```

**Fixture modu notu:** Sahte model, madde etiketinin metindeki KARAKTER KONUMU oranina
bakarak karar verir: oran <=%20 veya >=%80 ise dogru cevap, aradaysa yakin-yanilti ile
karisir — bu KASITLI olarak klasik U-egrisini taklit eder, boru hattinin bu egriyi dogru
olcup cizdigini gostermek icin. GERCEK bir modelin boyle davranacagini KANITLAMAZ.

## Katilimci Icin Okuma Rehberi

`charts/accuracy_by_position.png`'deki egri sekline bakin: U mu, duz mu, yoksa baska bir
sekil mi? `evidence_identified` oranini da inceleyin — dogru cevap verilse bile model yanlis
maddeyi mi gosteriyor (bu, "dogru cevap ama yanlis gerekce" durumunu yakalar).

**Tartisma sorulari:**
1. Lab05'in uzunluk-bazli bozulmasi ile Lab06'nin konum-bazli bozulmasi birbirinden bagimsiz
   mi, yoksa ayni temel mekanizmanin iki farkli gorunumu mu olabilir?
2. `evidence_identified` orani `exact_match`'ten daha mi dusuk? Bu ne anlama gelir?

## Egitmen Icin Notlar

- **Beklenen vs. Olculen:** Fixture modundaki %20/%80 esikleri KEYFIDIR. Gercek U-egrisinin
  sekli (varsa) sadece `--replay`/`--live` ile gorulebilir.
- **Yanlis kani:** "Baglam icinde konum onemli degildir, sadece bilginin orada olmasi
  yeterlidir" — bu lab'in dogrudan sorguladigi kanidir.

## Testler

`tests/labs/test_lab06_conditions.py`, `test_lab06_evaluator.py`,
`tests/integration/test_lab06_cli.py` — her kosulun AYNI toplam uzunluga sahip oldugunu
(kontrollu degisken), hedef gercegin dogru bagil konuma yerlestigini, degerlendiriciyi, ve
U-seklindeki fixture-modu egrisini dogrular.
