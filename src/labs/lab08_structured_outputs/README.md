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

## Bilinen Sinirlama (bu kontrol noktasinda)

Diger lab'lardan farkli olarak, Lab 08 icin SENTETIK KAYIT (`tests/fixtures/recordings/
lab08/`) ve replay entegrasyon testi HENUZ eklenmedi (kullanim limiti nedeniyle M4'u
tamamlama asamasinda kesildi) — `lab_core.replay` mekanizmasinin kendisi zaten M2'den
itibaren genel olarak test edilmistir ve Lab08 standart `ExperimentRunner`/`run_replay`
yolunu (Lab01/03/04/05/06 ile ayni) kullanir, bu nedenle risk dusuktur, ama bu lab'a ozel
bir replay dogrulamasi yapilmamistir — `docs/tasks.md`'de acikca not edilmistir.

## Testler

`tests/labs/test_lab08_dataset.py`, `test_lab08_conditions.py`, `test_lab08_evaluator.py`,
`tests/integration/test_lab08_cli.py` — veri kumesi minimumlarini, kosul/response_format
eslemesini, uc katmanli degerlendiriciyi (gecerli JSON/schema ihlali/yanlis deger/null
eslesmesi dahil) dogrular.
