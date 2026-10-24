"""System prompts for every step/condition. Kept in one module so the primary comparison's
controlled text (policy description, rule definitions) is visibly shared rather than
quietly drifting between conditions."""

from __future__ import annotations

POLICY_SUMMARY = (
    "Kaya Elektronik harcama politikasi:\n"
    "- category_check: kategori su listede olmali: seyahat, ofis_malzemesi, egitim, yazilim. "
    "Degilse REDDET.\n"
    "- receipt_requirement: tutar 1000 TL'den fazlaysa fis/fatura gerekir. "
    "Yoksa UST MAKAMA ESKALE ET.\n"
    "- approval_chain: tutar 5000 TL'den fazlaysa onceden yonetici onayi gerekir. "
    "Yoksa UST MAKAMA ESKALE ET.\n"
    "- Tum kurallar PASS ise ONAYLA."
)

DIRECT_SYSTEM = (
    f"{POLICY_SUMMARY}\n\n"
    "Musteri aciklamasini oku ve nihai karari ver. "
    "Cevabini TAM OLARAK su formatta ver: 'KARAR: <approve|deny|escalate>'"
)

STRUCTURED_SINGLE_CALL_SYSTEM = (
    f"{POLICY_SUMMARY}\n\n"
    "Musteri aciklamasini oku, asagidaki adimlari SIRAYLA takip et ve HEPSINI tek "
    "cevapta bildir:\n"
    "1. Bilgileri cikar: tutar, kategori, fis durumu, onay durumu.\n"
    "2. Hangi kurallarin gecerli oldugunu belirle.\n"
    "3. Her gecerli kural icin PASS/FAIL belirle.\n"
    "4. Nihai karari ver.\n"
    "Cevabini TAM OLARAK su formatta ver (hepsi bir satirda, | ile ayrilmis):\n"
    "'TUTAR: <sayi> | KATEGORI: <kategori> | FIS: <var|yok> | ONAY: <var|yok> | "
    "GECERLI_KURALLAR: <kural1,kural2,...> | KURAL_SONUCLARI: <kural1:pass/fail,...> | "
    "KARAR: <approve|deny|escalate>'"
)

EXTRACT_FACTS_SYSTEM = (
    "Musteri aciklamasindan su alanlari cikar: tutar (sayi, TL), kategori, fis/fatura "
    "durumu, yonetici onay durumu. Cevabini TAM OLARAK su formatta ver: "
    "'TUTAR: <sayi> | KATEGORI: <kategori> | FIS: <var|yok> | ONAY: <var|yok>'"
)

DETERMINE_RULES_SYSTEM = (
    f"{POLICY_SUMMARY}\n\n"
    "Verilen tutar ve kategoriye gore hangi kurallar GECERLIDIR (uygulanir)? "
    "Cevabini TAM OLARAK su formatta ver: 'GECERLI_KURALLAR: <kural1,kural2,...>'"
)

EVALUATE_RULES_SYSTEM = (
    f"{POLICY_SUMMARY}\n\n"
    "Verilen bilgilere ve gecerli kurallara dayanarak HER kural icin PASS veya FAIL "
    "belirle. Cevabini TAM OLARAK su formatta ver: "
    "'KURAL_SONUCLARI: <kural1:pass/fail,kural2:pass/fail,...>'"
)

DECIDE_SYSTEM = (
    f"{POLICY_SUMMARY}\n\n"
    "Kural sonuclarina dayanarak nihai karari ver. Cevabini TAM OLARAK su formatta ver: "
    "'KARAR: <approve|deny|escalate>'"
)

REVALIDATE_RULES_SYSTEM = (
    f"{EVALUATE_RULES_SYSTEM}\n\n"
    "NOT: Onceki cevabin uygulama tarafi dogrulamasiyla uyusmadi. Verilen bilgileri "
    "tekrar dikkatlice degerlendirip duzeltilmis sonucu ver."
)
