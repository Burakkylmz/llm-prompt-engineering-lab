# Lab 07 — Akil Yurutme Yonlendirmesi ve Gorev Ayristirmasi

## Ogrenme Hedefi

Bir karmasik, kurallara dayali karar gorevinde (coklu kosul/esik iceren harcama onayi),
modelin kendi ic akil yurutmesine (`gpt-oss` modelleri her zaman ic akil yurutme yapar)
guvenmek ile gorevi ACIKCA adimlara ayirmanin (ara ciktilari zorunlu kilmak, birden fazla
cagriya bolmek, uygulama-tarafi dogrulama eklemek) farkini olcer.

**Onemli karisiklik noktasi:** `gpt-oss` modelleri akil yurutme modelleridir — "direkt
cevap" istenen bir promptta bile ic akil yurutme yaparlar. Bu nedenle bu lab'in asil
karsilastirmasi "akil yurutme vs. akil yurutme yok" DEGIL, **"disaridan gorev yapisi vs.
modelin kendi ic akil yurutmesine guvenmek"**tir.

## Senaryo

Kaya Elektronik harcama onay politikasi: kategori kontrolu (bazi kategoriler reddedilir),
fis gereksinimi (1000 TL ustu), yonetici onay zinciri (5000 TL ustu). Model, musteri
aciklamasindan bu bilgileri cikarip nihai karari (approve/deny/escalate) vermelidir.

## Birincil Karsilastirma (reasoning_effort SABIT)

| Kosul | Cagri sayisi | Aciklama |
|---|---|---|
| `direct_answer` | 1 | Sadece nihai karar |
| `single_call_structured` | 1 | Tek cagri, ama ara alanlar (tutar/kategori/fis/onay/gecerli kurallar/kural sonuclari) ZORUNLU |
| `multi_call_decomposition` | 4 | Ayri cagrilar: bilgi cikar -> gecerli kurallari belirle -> kurallari degerlendir -> karar ver |
| `multi_call_validated` | 4-5 | Yukaridaki + uygulama-tarafi deterministik dogrulama; tutarsizlikta EN FAZLA BIR kez tekrar sorar |

## Ikincil Deney

`reasoning_low`, `reasoning_medium`, `reasoning_high`: SADECE `direct_answer` kosulunda,
dogrulanmis `reasoning_effort` degerleri uzerinde tarama (bkz. `docs/groq-capabilities.md`).

## Gizli Akil Yurutme Kurali

Bu lab'da (ve projenin tamaminda) gizli akil yurutme metni ASLA istenmez, yakalanmaz,
saklanmaz veya degerlendirilmez: `GroqClientAdapter` sadece `message.content`'i okur,
`reasoning` alanini hic cekmez. `include_reasoning=False` varsayilan config'de ayarlidir.

## Metrikler

Nihai karar dogrulugu, ARA ADIM dogrulugu (cikarilan bilgiler, gecerli kurallar, kural
sonuclari — SADECE o kosulun urettigi alanlar icin, `direct_answer` hicbirini uretmez),
API cagri sayisi, toplam token/latency, raporlanmissa reasoning token'lari ("Tokens, latency
and cost" tablosunda "Mean reasoning tokens"), tahmini maliyet.

Ara adim kontrolleri, sozlesmesinde ara degerler bulunan her kosulda (structured ve
multi-call) uygulanir; **parse edilemeyen bir ara deger YANLIS sayilir**, "uygulanamaz"
sayilmaz (`DecompositionResult.intermediates_expected`). Coklu cagrida adimlardan biri bir
token alanini raporlamamissa, deneme toplami `null` olur — eksik adimi 0 sayan kismi bir
toplam uretilmez.

## Veri Kumesi

- `data/golden/lab07/cases.json`: 70 harcama uygunluk vakasi, her biri altin nihai karar VE
  altin ara degerlerle (cikarilan bilgiler, gecerli kurallar, kural sonuclari).

## Mimari Not: Coklu-Cagri Orkestrasyon

`multi_call_decomposition`/`multi_call_validated` kosullari `ExperimentRunner`'i KULLANMAZ
(bir "deneme" tek bir API cagrisi varsayimina uymuyor) — `cli.py` kendi orkestrasyonunu
yapar ve `Observation`lari dogrudan olusturur. Replay de bu nedenle bu lab'a ozel, hafif
bir yeniden-degerlendirme olarak uygulanmistir (diger lab'larin kullandigi genel
prompt-hash sapma tespiti burada YOKTUR, cunku coklu-adimli bir denemenin tek bir
"prompt'u" yoktur — `docs/decisions.md`'de detaylandirilmistir).

## Calistirma

```powershell
uv run lab-runner lab07
uv run lab-runner lab07 --replay <kayitli_live_run>
uv run lab-runner lab07 --live --config config/live.toml
```

**Fixture modu notu:** Sahte model her adimda HER ZAMAN dogru (altin) degeri dondurur —
diger bazi lab'larin "kasitli kusurlu" fixture tasarimindan farkli olarak, Lab07'nin fixture
amaci coklu-cagri orkestrasyonunun ve ara-adim dogruluk olcumunun DOGRU CALISTIGINI
kanitlamaktir, belirli bir hipotezi simule etmek degildir.

## Katilimci Icin Okuma Rehberi

`comparison.md`'de `direct_answer`'in SADECE `decision_correct` kontrolune sahip oldugunu,
digerlerinin ek olarak `facts_correct`/`applicable_rules_correct`/`rule_outcomes_correct`
icerdigini gorun. `charts/accuracy_vs_cost.png`, dogrulugu ortalama API cagri sayisina
(maliyet vekili) karsi gosterir.

**Tartisma sorulari:**
1. `multi_call_validated`'in dogrulugu `multi_call_decomposition`'dan daha mi iyi? Kac kat
   daha fazla cagriya mal oluyor?
2. `single_call_structured`, tek cagriyla `multi_call_decomposition`'in COGU faydasini
   sagliyor mu (ara alanlari da zorlayarak)?

## Egitmen Icin Notlar

- **Beklenen vs. Olculen:** Fixture modu her kosulda %100 dogruluk gosterir (sahte model
  her zaman dogru) — bu SADECE boru hattinin dogru oldugunu kanitlar. Gercek karsilastirma
  icin `--replay`/`--live` gerekir.
- **Yanlis kani:** "Gorevi adimlara ayirmak her zaman dogrulugu artirir" — gercekte
  ayristirma oncelikle DENETLENEBILIRLIK ve ara-dogrulama firsati saglar; capable bir akil
  yurutme modeli icin nihai dogrulugu artirmasi GARANTI DEGILDIR (spec'in yorum noktasi).
- **Maliyet farkindaligi:** `multi_call_*` kosullari 4-5 kat daha fazla API cagrisi yapar —
  canli calistirirken `preflight` limitlerini buna gore ayarlayin.

## Testler

`tests/labs/test_lab07_policy.py`, `test_lab07_parsing.py`, `test_lab07_dataset.py`,
`test_lab07_orchestration.py` (dogrulayicinin tam olarak BIR kez yeniden sordugunu test eden
ozel bir test dahil), `test_lab07_evaluator.py`, `tests/integration/test_lab07_cli.py`.
