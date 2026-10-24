from __future__ import annotations

from lab_core.text_similarity import shingle_jaccard


def test_identical_text_is_similarity_one():
    text = "Merhaba, faturamda bir hata var ve bunu düzeltmenizi istiyorum lütfen"
    assert shingle_jaccard(text, text) == 1.0


def test_completely_different_text_is_similarity_zero():
    a = "Merhaba, faturamda bir hata var ve bunu düzeltmenizi istiyorum lütfen"
    b = "Ürünün garanti süresi hakkında bilgi almak istiyorum acaba"
    assert shingle_jaccard(a, b) == 0.0


def test_near_duplicate_with_minor_edit_is_highly_similar():
    a = "Siparişim KE-1001 numaralı akıllı saat için kredi kartımdan iki kez çekim yapılmış"
    b = "Siparişim KE-1001 numaralı akıllı saat için kredi kartımdan iki kez tahsilat yapılmış"
    assert shingle_jaccard(a, b) > 0.5


def test_empty_strings_are_trivially_identical():
    assert shingle_jaccard("", "") == 1.0


def test_one_empty_one_nonempty_is_zero():
    assert shingle_jaccard("", "merhaba nasılsınız bugün hava güzel") == 0.0
