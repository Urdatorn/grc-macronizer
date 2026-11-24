'''Lunate sigma: tokens are looked up with ordinary sigmas and keep their lunate spelling.'''
import pytest

from grc_macronizer.lunate import has_lunate, normalize_lunate, restore_spelling


@pytest.mark.parametrize("word, expected", [
    ("πόλιϲ", "πόλις"),
    ("τὰϲ", "τὰς"),
    ("ἐϲτιν", "ἐστιν"),
    ("Ἀριϲτοφάνηϲ", "Ἀριστοφάνης"),
    ("Ϲωκράτηϲ", "Σωκράτης"),
    ("ἐϲτ'", "ἐστ'"),
    ("πόλις", "πόλις"),
])
def test_normalize_lunate(word, expected):
    assert normalize_lunate(word) == expected


@pytest.mark.parametrize("macronized, original, expected", [
    ("πό^λις", "πόλιϲ", "πό^λιϲ"),
    ("τὰ^ς", "τὰϲ", "τὰ^ϲ"),
    ("Ἀ^ρι^στοφά_νης", "Ἀριϲτοφάνηϲ", "Ἀ^ρι^ϲτοφά_νηϲ"),
    ("τι^ς", "τιϲ", "τι^ϲ"),
    ("πόλις", "πόλιϲ", "πόλιϲ"),
])
def test_restore_spelling(macronized, original, expected):
    out = restore_spelling(macronized, original)
    assert out == expected
    assert out.replace("^", "").replace("_", "") == original


def test_restore_spelling_misaligned():
    assert restore_spelling("πό^λε^ις", "πόλιϲ") is None


def test_has_lunate():
    assert has_lunate("πόλιϲ") and has_lunate("Ϲωκράτης") and not has_lunate("πόλις")
