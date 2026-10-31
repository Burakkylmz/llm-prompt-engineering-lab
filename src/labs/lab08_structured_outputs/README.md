# Lab 08 — Yapilandirilmis Ciktilar ve JSON Schema

## Ogrenme Hedefi

"Gecerli JSON" ile "semantik olarak dogru veri" arasindaki farki gosterir: strict JSON
Schema modu en fazla ikinci katmani (yapisal uyum) garanti eder, UCUNCU katmani (anlam/
deger dogrulugu) ASLA garanti etmez.

## Kosullar

| Kosul | response_format | Beklenen |
|---|---|---|
| `plain_nl` | yok (JSON hic istenmiyor) | "Bosluk" (gap) — JSON ayrisma orani cok dusuk |
| `prompt_only_json` | yok (sadece prompt metninde istek) | Degisken |
| `json_object_mode` | `{"type":"json_object"}` | Gecerli JSON garantili, yapi garantisiz |
| `json_schema_best_effort` | `strict:false` | Genelde yapisina uyar, garanti yok |
| `json_schema_strict` | `strict:true` | Yapisal uyum garantili (constrained decoding) |

## Uc Katmanli Degerlendirme

1. **JSON parse basarisi** (serbest metinde gomulu JSON icin bile esnek ayristirici).
2. **Schema uyumu** (`jsonschema` ile HER ZAMAN kontrol edilir, strict modda bile).
3. **Semantik dogruluk** (alan bazinda altin degerle karsilastirma, Turkce-duyarli
   normalizasyon, null/deger ayrimi).

## Veri Kumesi

`data/golden/lab08/records.json`: 45 Turkce musteri talebi, eksik alanlar (`missing_fields`),
birden fazla olasi deger iceren vakalar (`multiple_candidates`), normalizasyon gerektiren
tutarlar (`normalization_required`, orn. "bin iki yuz TL" -> 1200).

## Calistirma

```powershell
uv run lab-runner lab08
uv run lab-runner lab08 --live --config config/live.toml
```

**Fixture modu notu:** `plain_nl` serbest metin dondurur (ayrisma basarisiz), digerleri
gecerli/dogru JSON dondurur. Fixture, `json_object_mode`/`best_effort`/`strict` arasindaki
GERCEK farki simule EDEMEZ (bu fark sadece gercek bir modelin constrained decoding
davranisinda ortaya cikar) — bu uc kosul fixture modunda kasitli olarak ozdestir.

## Replay Dogrulamasi (2026-10-31 tamamlandi)

Onceki kontrol noktasinda eksik olan Lab 08 sentetik kaydi eklendi:
`tests/fixtures/recordings/lab08/synthetic-test-recording-001/` (`execution_mode:
"synthetic_recording_for_tests"` — gercek bir Groq cagrisi DEGILDIR). Kayit, gercek
`ExperimentRunner` ile uretildigi icin prompt hash'leri guncel kosullarla birebir eslesir.
Elle yazilmis 6 yanit, uc katmanin her birini ayri ayri bozar:

| Kosul / kayit | JSON parse | Schema | Semantik | Neyi gosterir |
|---|---|---|---|---|
| `plain_nl` / rec-001 | hayir | hayir | hayir | duz metin, JSON yok |
| `prompt_only_json` / rec-001 | evet (esnek parser) | evet | evet | kod blogu + aciklama icinde JSON |
| `json_schema_strict` / rec-001 | evet | evet | evet | tam dogru |
| `json_object_mode` / rec-002 | evet | **hayir** | hayir | `amount` sayi yerine metin |
| `json_schema_best_effort` / rec-002 | evet | evet | **hayir** | null olmasi gereken e-posta uydurulmus |
| `json_schema_strict` / rec-002 | evet | evet | evet | `null` dogru kullanilmis |

`tests/integration/test_lab08_cli.py::test_replay_of_synthetic_recording_reevaluates_all_three_layers`
replay'in bu deseni birebir yeniden urettigini dogrular. "Gecerli JSON != schema-uyumlu
JSON != semantik olarak dogru veri" ayrimini replay ile canli maliyet olmadan gosterebilirsiniz.

## Testler

`tests/labs/test_lab08_dataset.py`, `test_lab08_conditions.py`, `test_lab08_evaluator.py`,
`tests/integration/test_lab08_cli.py` — veri kumesi minimumlarini, kosul/response_format
eslemesini, uc katmanli degerlendiriciyi (gecerli JSON/schema ihlali/yanlis deger/null
eslesmesi dahil) dogrular.
