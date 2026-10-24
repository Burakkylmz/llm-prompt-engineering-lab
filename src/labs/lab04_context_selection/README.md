# Lab 04 — Baglam Secimi, Butce, Siralama ve Guncellik

## Ogrenme Hedefi

Bir RAG (retrieval) sistemindeki cevap kalitesinin, SECIM asamasinda mi (dogru belge
baglama hic girmedi) yoksa KULLANIM asamasinda mi (dogru belge baglamdaydi ama model onu
kullanmadi) bozuldugunu AYIRT ETMEYI ogretir. Ayrica alaka (relevance), tekillestirme
(dedup) ve guncellik (freshness) filtrelerinin BIRBIRINDEN FARKLI sorunlari cozdugunu
gosterir: tekillestirme metinsel kopyalari yakalar, guncellik ise metinsel olarak FARKLI
ama ICERIK OLARAK CAKISAN (eski/yeni politika suruumu) belgeleri yakalar.

## Senaryo

Kaya Elektronik'in ic politika belgeleri uzerinde soru-cevap. Cevaplar belge ID'si ile
kanitlanmali (citation).

## Hipotez

Alaka puanlamasi (BM25) tek basina, ayni konudaki ESKI (superseded) ve YENI politika
belgelerini ayirt EDEMEZ (ikisi de ayni terimleri icerir) — bu nedenle guncellik filtresi
OLMADAN secilen baglam, eski/yeni cakismasi barindirmaya devam eder, oysa tekillestirme
(dedup) bu sorunu COZMEZ (ikisi metinsel olarak "near-duplicate" degildir, sadece ayni
konuda farkli degerler icerirler).

**Hipotezi curutecek sonuc:** `relevance_dedup_top5` (dedup var, freshness yok) kosulunun
"stale-doc inclusion rate"i `relevance_dedup_fresh_top5`den (freshness de var) anlamli
olcude farkli DEGILSE — bu, dedup'in freshness'in isini de yaptigini, iki ayri mekanizmaya
gerek olmadigini gosterir (hipotezi curutur).

## Kosullar

| Kosul | Aciklama |
|---|---|
| `all_documents` | Tum korpus (gerekirse token limitine gore kirpilir) — BASELINE |
| `relevance_top5` | BM25 ile en alakali 5 belge, dedup/freshness yok |
| `relevance_dedup_top5` | relevance_top5 + tekillestirme (aday havuzu: ilk 10, sonra dedup, sonra ilk 5) |
| `relevance_dedup_fresh_top5` | relevance_dedup_top5 + guncellik filtresi (superseded belgeler cikarilir) |
| `budget_200` / `budget_500` / `budget_1000` | Token butcesi altinda greedy alaka secimi |
| `order_relevance_asc` | `relevance_dedup_fresh_top5` ile AYNI belge kumesi, artan alaka sirasiyla |
| `order_seeded_random` | Ayni kume, seed'li rastgele sira |

## Metrikler (iki seviye)

**Secim-seviyesi (LLM gerektirmez, her zaman gercek, hic SIMULATED degil):**
evidence recall/precision (secilen belgeler altin kanitla ne kadar ortusuyor), stale-doc
inclusion rate (secilen kumede eski/superseded bir belge var mi).

**Cevap-seviyesi:** grounded answer accuracy, citation correctness, stale-answer rate
(cevap eski degeri yansitiyor mu), context token sayisi.

## Veri Kumesi

- `data/golden/lab04/corpus.json`: 42 belge — 10 konu x (guncel+eski cift) = 20, 4 birebir
  kopya, 6 yakin-kopya (near-duplicate, tek kelime degisik), 12 ilgisiz belge.
- `data/golden/lab04/questions.json`: 30 soru (10 konu x 3 ifade), her biri altin cevap +
  altin kanit belge ID'si + (varsa) eski deger/belge ID'si ile.

## Calistirma

```powershell
uv run lab-runner lab04
uv run lab-runner lab04 --replay <kayitli_live_run>
uv run lab-runner lab04 --live --config config/live.toml
```

**Fixture modu notu:** Sahte model, baglamda HANGI belge ID etiketinin ("[BELGE_ID: ...]")
gorundugune gore cevap verir — guncel belge varsa dogru cevap+kaynak, sadece eski belge
varsa eski deger+eski kaynak, hicbiri yoksa "bulunamadi". Bu, secim mekanizmasinin
cevap kalitesini nasil SINIRLADIGINI fixture modunda bile gosterir (ornegin
`relevance_dedup_fresh_top5` ve siralama kosullarinda stale-inclusion %0'a duserken,
digerlerinde %100 kaliyor) — ama bu GERCEK bir modelin boyle davranacagini KANITLAMAZ.

## Katilimci Icin Okuma Rehberi

`comparison.md`'nin sonundaki "Selection-level metrics" tablosuna bakin: hangi kosullarda
`stale_inclusion_rate` dusuyor? Bu, SADECE guncellik filtresi eklenen kosullarda (
`relevance_dedup_fresh_top5`, `order_relevance_asc`, `order_seeded_random`) dusmelidir —
`relevance_dedup_top5`'te DUSMEMELIDIR (dedup, freshness'in isini yapmaz).

**Tartisma sorulari:**
1. `all_documents` kosulunun evidence precision'i neden cok dusuk (cogu belge ilgisiz)?
2. Budget serisinde (`budget_200/500/1000`) recall butce arttikca nasil degisiyor?
3. Siralama (`order_relevance_asc` vs `order_seeded_random`) AYNI belge kumesini kullaniyor
   — buna gore bu iki kosul arasinda cevap kalitesinde fark bekler misiniz? Neden?

## Egitmen Icin Notlar

- **Beklenen vs. Olculen:** Secim-seviyesi metrikler GERCEKTIR (LLM cagrisi gerektirmez),
  fixture modunda da gecerlidir. Cevap-seviyesi metrikler fixture modunda SADECE boru
  hattini test eder.
- **Yanlis kani:** "Tekillestirme (deduplication) eski/yeni surum cakismasini da cozer" —
  bu lab'in temel gosterdigi YANLIS kanidir. Deduplication SADECE metinsel kopyalari yakalar.
- **Hata modlari:** Eger `relevance_top5`'te recall dusukse, bu BM25'in bu soru icin yeterince
  ayirt edici olmadigini gosterir — bu durumda cevap kalitesizliginin nedeni SECIM
  basarisizligidir, model basarisizligi degil (spec'in "distinguish selection failure from
  usage failure" noktasi).

## Testler

`tests/labs/test_lab04_dataset.py`, `test_lab04_selection.py`, `test_lab04_evaluator.py`,
`test_lab04_selection_metrics.py`, `tests/integration/test_lab04_cli.py` — veri kumesi
minimumlarini, her secim fonksiyonunun dogru davranisini (ozellikle dedup'in freshness'in
isini yapmadigini), degerlendiriciyi, secim-seviyesi metrik hesaplamasini, ve tam
fixture/replay akisini dogrular.
