# Lab 01 — Prompt Anatomi ve Talimat Netligi

## Ogrenme Hedefi

Bu lab, bir prompt'un bilesenlerinin (talimat, baglam, kisitlar, cikti sozlesmesi, ornekler)
Turkce bir isletme musteri destegi siniflandirma gorevinde dogruluk ve talimat uyumuna
(instruction adherence) ayri ayri ne kadar katki sagladigini olcer. Katilimcilarin cikarmasi
gereken temel sonuc: **daha fazla bilesen otomatik olarak daha iyi sonuc anlamina gelmez** —
onemli olan bilesenin tasidigi bilgi, bilesenin uzunlugu (token sayisi) degildir.

## Senaryo

Kaya Elektronik (hayali bir tuketici elektronigi sirketi) musteri destek ekibine gelen
mesajlari bes kapali kategoriden birine ayirir: `billing`, `technical_issue`, `cancellation`,
`complaint`, `general_inquiry`; ayrica bir `priority` (`low`/`medium`/`high`) alani uretir.

## Hipotez (sonuclardan ONCE yazilmistir)

Prompt bilesenleri sirayla eklendiginde (talimat -> baglam -> kisitlar -> cikti sozlesmesi ->
ornekler) dogruluk ve format uyumu **tek duze artmaz**; artis, bilesenin tasidigi bilgiden
kaynaklanir, salt token uzunlugundan degil.

**Hipotezi curutecek sonuc:** `B_len` (B_constraints + uzunluk-esleyen dolgu metni) kosulu,
`D_examples` kosuluna (gercek orneklerle, cok daha fazla gorevle-ilgili token icerir) kendi
calismasinin gurultu araligi icinde kalan bir dogruluk/format-uyum skoru verirse, bu "token
sayisi arttikca sonuc iyilesir" savini curutur ve "bilgi, token degil" iddiasini dogrular.
Ayrica baseline -> A -> B -> C kosullari arasinda dogruluk tek duze artmazsa ve bu bir
bilesen-catismasiyla aciklanamiyorsa, hipotez de kismen curutulmus sayilir.

## Kosullar (birikimli)

| Kosul | Icerik |
|---|---|
| `baseline` | Sadece tek satir talimat |
| `A_context` | baseline + sirket baglami ve etiket tanimlari |
| `B_constraints` | A + kapali etiket seti, "ekstra metin yok" kurali, belirsizlik durumunda ilk bahsedilen konunun kazanmasi kurali |
| `B_len` | B ile AYNI icerik + D_examples'in tahmini token uzunluguna denk, gorevle ilgisiz, notr dolgu metni (uzunluk kontrolu) |
| `C_output_contract` | B + tam cikti formati (`ETIKET: <...>` / `ONCELIK: <...>`, baska hicbir metin yok) |
| `D_examples` | C + ornek havuzundan her sinif icin birer tipik ornek (5 ornek) |

Her kosul AYNI 6 model parametresini kullanir (`temperature=0.0`, `max_tokens=64`,
`reasoning_effort` ve `include_reasoning` config'den sabit) — bu
`tests/labs/test_lab01_conditions.py::test_generation_overrides_identical_across_conditions`
ile dogrulanir.

## Talimat Uyumu (Instruction Adherence)

Her kosulun ciktisinda, kosulun kendisi bunu istemis olsun ya da olmasin, ayni uc kontrol
uygulanir (bu, deneyin asil ogretici noktasidir — baseline/A/B/B_len'in bu kontrollerde
dusuk puan almasi beklenir, cunku onlardan bu format hic istenmemistir):

1. `label_in_closed_set` — serbest metinde kapali kumeden bir etiket bulunabiliyor mu (esnek arama).
2. `priority_valid` — gecerli bir oncelik degeri (`low`/`medium`/`high`) bulunabiliyor mu.
3. `format_compliant` — cikti TAM OLARAK `ETIKET: <etiket>\nONCELIK: <oncelik>` iki satirina uyuyor mu (regex ile, baska hic metin olmadan).

`primary_correct` (dogruluk icin kullanilir) esnek aramayla bulunan etiketin gold etiketle
eslesmesidir — bu, baseline'in da olculebilir bir dogruluk puani almasini saglar.

## Veri Kumesi

- `data/golden/lab01/eval.json`: 73 vaka, 5 sinif (her sinifta >=14 vaka, minimum 12 sarti
  asiliyor), %15,1 belirsiz/ucra (edge_case/ambiguous) etiketli — minimum %15 sartini karsiliyor.
- `data/golden/lab01/example_pool.json`: 20 vaka (minimum 15), eval ile metin duzeyinde
  cakisma YOK (shingle-Jaccard sizinti kontrolu, esik 0.8 — `check_leakage`).
- Tum veri sentetik, hayali "Kaya Elektronik" sirketi baglaminda, gercek kisi/sirket icermez.
- Semalar: `data/schemas/lab01_case_set.schema.json`. Dogrulama: `uv run lab-runner validate-data`.

## Calistirma Modlari

```powershell
uv run lab-runner lab01                                    # fixture (varsayilan, SIMULATED)
uv run lab-runner lab01 --profile full                      # daha fazla vaka/tekrar
uv run lab-runner lab01 --replay <onceki_live_run_dizini>   # replay (sinif-ici varsayilan)
uv run lab-runner lab01 --live --config config/live.toml    # gercek Groq cagrisi (maliyetli)
```

**Onemli:** Fixture modu, boru hattinin (pipeline) dogru olcup olcmedigini test eder; modelin
gercek davranisi hakkinda HICBIR KANIT tasimaz. Raporlarda `SIMULATED` damgasi gorursuniz.
Gercek model davranisini gormek icin egitmenin onceden kaydettigi bir `--replay` calismasini
kullanin veya (dikkatli ve maliyeti bilerek) `--live` calistirin.

## Katilimci Icin Okuma Rehberi

- `comparison.md` dosyasindaki tabloda her kosulun dogruluk (%95 Wilson guven araligiyla) ve
  Macro-F1 degerlerine bakin. Guven araliklari birbirine cok yakinsa ("Caution" notu
  otomatik eklenir), kosullar arasindaki fark bu calismada gurultu icinde olabilir demektir.
- `constraint_adherence` alaninda her kosulun uc kontrolu ayri ayri incelenebilir — ozellikle
  `format_compliant`'in sadece `C_output_contract` ve `D_examples`'ta yuksek cikmasi beklenir.
- "Per-case flips" bolumu, baseline'a gore hangi vakalarin dogru-yanlis yon degistirdigini
  gosterir — toplam dogruluktan daha ayrintili bir resim verir.

**Tartisma sorulari:**
1. `B_len` ile `D_examples` arasindaki fark (varsa) ne kadar buyuk, guven araliklari ortusuyor mu?
2. `format_compliant` orani `C_output_contract`'ta neden `B_constraints`'ten cok daha yuksek —
   oysa B de "ekstra metin yok" diyor?
3. Baseline'in dogrulugu neden sifirdan yuksek olabiliyor (format hic istenmemisken)?

## Egitmen Icin Notlar

- **Beklenen vs. Olculen:** Fixture modunda tum kosullar ayni (gold-echo) kurala gore yanit
  uretir, yani fixture modunda dogruluk her kosulda ~%100 cikar — bu sadece boru hattinin
  dogru calistigini gosterir, gercek modelin boyle davranacagini GOSTERMEZ. Gercek farklar
  yalnizca `--replay` (kayitli canli calisma) veya `--live` ile gorulebilir.
- **Yanlis kanilar:** "Daha uzun prompt daha iyi sonuc verir" yanlis kanisini `B_len` kosulu
  dogrudan test eder. "Ornekler her zaman yardimci olur" kanisi da sorgulanmali — D'nin C'ye
  katkisi kucukse (CI'lar ortusuyorsa) bu, 5 ornegin bu gorev icin yeterli ayirt edicilige
  sahip olmayabilecegini gosterir (bkz. Lab 03'un ornek kalitesi/sayisi ayrimi).
- **Hata modlari:** Model kapali kume disinda bir etiket uretirse (`label_in_closed_set=False`),
  bu baslica baseline/A kosullarinda beklenir (kapali kume hic belirtilmemis). C/D'de hala
  olursa, bu modelin kisitlamaya uymadigini (gercek bir basarisizlik, kurulum hatasi degil)
  gosterir ve tartismaya deger bir bulgudur.
- **Onerilen akis:** Once fixture ile boru hattini gosterin (SIMULATED damgasini vurgulayin),
  sonra onceden kaydedilmis bir `--replay` calismasiyla gercek sonuclari inceleyin.

## Testler

`tests/labs/test_lab01_dataset.py`, `test_lab01_conditions.py`, `test_lab01_evaluator.py`, ve
`tests/integration/test_lab01_cli.py` bu lab'in veri kumesini, kosul uretimini (kumulatiflik,
kontrollu degiskenlerin sabitligi, beklenen calistirma sayisi), degerlendiriciyi, ve tam
fixture/replay akisini (kayitli sentetik replay fixture'i dahil) dogrular.
