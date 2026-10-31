# Lab 03 — Few-Shot Ornek Muhendisligi

## Ogrenme Hedefi

Few-shot orneklerin SAYISININ mi, KALITESININ mi (ve hangi kalite boyutunun) siniflandirma
performansini etkiledigini ayri ayri olcer. Temel ogretici nokta: **hangi orneklerin
secildigi, kac ornek secildiginden daha onemli olabilir**. Sayi ve kalite ASLA ayni kosulda
birlikte degistirilmez — iki ayri seri vardir.

## Senaryo

Kaya Elektronik B2B satis ekibi, gelen potansiyel musteri (lead) mesajlarini bes kategoriden
birine ayirir: `hot`, `warm`, `cold`, `not_a_lead`, `partner_inquiry`.

## Hipotez

Ornek SAYISI arttikca (0->2->4->8, sabit "cesitli+sinir-durumu" secim stratejisiyle) dogruluk
tek duze artmaz ve bir noktadan sonra platoya ulasir; ornek KALITESI (sabit k=4'te) sayidan
daha fazla fark yaratir — ozellikle "sinir-durumu odakli" (boundary-focused) ornekler, en cok
karistirilan sinif ciftlerinde dogrulugu `random`/`redundant` orneklerden daha fazla
iyilestirir.

**Hipotezi curutecek sonuc:** `quality_boundary_focused`, karistirilan sinif ciftlerinde
(confusion matrix'te) `quality_random_seed*` veya `quality_redundant`'tan daha iyi
performans GOSTERMEZSE. Ya da `count_8`, `count_2`'den konfidans araligi disinda anlamli
olcude iyi degilse (sayi tek basina onemli degilse bu beklenen bir sonuctur, ama hipotez
yine de "daha fazla ornek otomatik iyilesme saglar" seklinde YANLIS anlasilmamalidir).

## Kosullar (11 + istege bagli 2)

**Seri 1 — Sayi** (sabit strateji: once "typical", yetmezse "boundary", sinif-dengeli):
`count_0`, `count_2`, `count_4`, `count_8`.

**Seri 2 — Kalite** (sabit k=4):
- `quality_random_seed1/2/3`: havuzdan rastgele (farkli seed'ler).
- `quality_redundant`: birbirine cok benzeyen 4 ornek (hepsi "hot" sinifinin paralog
  anlatimlari) — cesitlilik yok.
- `quality_diverse_typical`: her siniftan birer tipik ornek.
- `quality_boundary_focused`: 4 farkli "karistirilan sinif cifti"nden birer ornek (hot/warm,
  warm/cold, cold/not_a_lead, partner_inquiry/not_a_lead).
- `quality_misleading`: yanlis etikete isaret eden yanilti bir yuzeysel ipucu (orn. "butce"
  kelimesi gecen ama gercekte cold/not_a_lead olan mesajlar) tasiyan ornekler.

Her 11 kosulda talimat/baglam/kisitlar/cikti-sozlesmesi TAM AYNI — sadece `examples` degisir
(`tests/labs/test_lab03_conditions.py` ile dogrulanir).

**Seri 3 — Siralama etkisi (istege bagli, `--order-effect` veya `--profile full`):**
`quality_boundary_focused` ile BIREBIR AYNI 4 ornek, farkli sirada:
- `order_boundary_reversed`: ters sira.
- `order_boundary_permuted`: sabit bir permutasyon (`(2, 0, 3, 1)` — ne orijinal ne ters sira).

Burada sayi da kalite de sabittir; degisen TEK sey siradir (testle dogrulanir:
`test_order_conditions_use_the_identical_example_set_in_a_different_order`).
`comparison.md` sonundaki "Example order effect" tablosu bu iki kosulu baseline'a (`count_0`)
degil, orijinal siradaki `quality_boundary_focused`'a gore karsilastirir (eslestirilmis
bootstrap %95 CI + flip'ler). Siralama tek basina vakalari cevirebiliyorsa, bu "ornek
secimi" tartismasinin onemli bir uyarisidir: ayni ornekler bile farkli sirada farkli
sonuc verebilir.

## Veri Kumesi

- `data/golden/lab03/eval.json`: 93 vaka, 5 sinif (17-20/sinif, min. 15 sarti asiliyor),
  %23.7 edge_case etiketli (min. %20).
- `data/golden/lab03/example_pool.json`: 31 vaka, dort amaç etiketiyle (`typical`:15,
  `boundary`:8, `redundant`:4, `misleading_candidate`:4), eval ile sifir metin orgusu
  (shingle-Jaccard sizinti kontrolu).

## Metrikler

Dogruluk, sinif-basi precision/recall/F1 ve karisiklik matrisi (her kosul icin
`comparison.md`'nin "Per-class precision / recall and confusion matrices" bolumunde ve
`summary.json`'da `per_class` / `confusion_matrix` alanlarinda), macro-F1 (seed'li bootstrap
%95 CI ile), edge-case dogrulugu (`edge_case_correct` kontrolu — paydasi yalnizca edge-case
vakalaridir, `n_evaluated` alaninda gorulur), ortalama prompt token sayisi ve "dogru basina
prompt token" (`charts/quality_vs_tokens.png`'de dogruluga karsi cizilir).

> Not (2026-10-31): `edge_case_correct` orani onceden TUM vakalara bolunuyordu (edge olmayan
> vakalar "basarisiz" sayiliyordu), bu da edge-case dogrulugunu sistematik olarak dusuk
> gosteriyordu. Cekirdek raporlama artik her kontrolu yalnizca uygulandigi vakalar uzerinden
> hesaplar.

## Calistirma

```powershell
uv run lab-runner lab03
uv run lab-runner lab03 --order-effect                 # siralama serisini ekle (+2 kosul)
uv run lab-runner lab03 --replay <kayitli_live_run>
uv run lab-runner lab03 --live --config config/live.toml
```

**Fixture modu notu:** Sahte model her kosulda altin (gold) etiketi dogru formatta tekrar
eder — bu, tum kosullarin fixture modunda ~%100 dogruluk gostermesi anlamina gelir (Lab01'in
baseline'indaki gibi). Bu durumda farkli olan METRIK, ornek sayisi/kalitesine gore degisen
TOKEN SAYISIDIR (`quality_vs_tokens.png`'de goruldugu uzere) — gercek dogruluk farklarini
gormek icin `--replay` veya `--live` gerekir.

## Katilimci Icin Okuma Rehberi

`comparison.md`'deki confusion matrix'i (summary.json icinde, macro_f1 hesaplamasinin
girdisi olarak) inceleyin: `quality_boundary_focused` kosulunun, hedeflenen sinif ciftlerinde
(orn. hot/warm) hata oranini dusurup dusurmedigine bakin — bu, "boundary ornekler spesifik
olarak hedeflenen karisikligi azaltir mi" sorusuna cevap verir.

**Tartisma sorulari:**
1. `count_8`, `count_4`'ten anlamli olcude mi iyi, yoksa guven araliklari ortusuyor mu?
2. `quality_redundant` (4 benzer ornek) ile `quality_diverse_typical` (4 farkli sinif)
   arasindaki fark ne kadar buyuk?
3. `quality_misleading`'in dogrulugu diger kalite kosullarindan daha mi dusuk? Bu, yanilti
   yuzeysel ipucunun modeli gercekten yanilttigini mi gosterir?

## Egitmen Icin Notlar

- **Beklenen vs. Olculen:** Fixture modunda tum kosullar ayni (gold-echo) kuralla calisir;
  gercek sayi-vs-kalite farkini gormek icin kayitli bir `--replay` calismasi gerekir.
- **Yanlis kani:** "Daha fazla ornek her zaman daha iyidir" — bu lab, `count_8` ile
  `count_2`/`count_4` arasindaki farkin kucuk veya guven araligi icinde kalabilecegini
  gostererek bu kaniyi sorgulatir.
- **Hata modlari:** `quality_redundant` kosulunun `quality_diverse_typical`'dan daha kotu
  performans gostermesi beklenir (ayni bilgiyi 4 kez tekrarlamak yeni bilgi eklemez) — eger
  gostermiyor ise, bu ya ornek secimin yeterince "redundant" olmadigini ya da modelin bu
  gorevde ornek cesitliligine hassas olmadigini gosterebilir.

## Testler

`tests/labs/test_lab03_dataset.py`, `test_lab03_selectors.py`, `test_lab03_conditions.py`,
`test_lab03_evaluator.py`, `tests/integration/test_lab03_cli.py` — veri kumesi minimumlarini,
her secim stratejisinin dogru orneklerı dondurdugunu, kosullar arasinda sadece `examples`in
degistigini, paired-design'i (tum kosullar ayni vaka kumesinde), ve replay akisini dogrular.
