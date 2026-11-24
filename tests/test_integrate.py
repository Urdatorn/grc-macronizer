'''
Regression tests for Text.integrate(), the step that writes macronized words back
into the text.

The cases come from the OGA corpus run of 2026-11-24 (grc-macronizer a949b76), where 29
of 2,234,754 sentences came out with a doubled word-final letter, e.g. ῾πάντα -> ῾πάνταα:
a bare word (πάντα) also matched inside another macronized token with a non-letter
attached (῾πάντα, βαδίζειν῾, \\x7fτύποϲ), and the two overlapping replacements
duplicated the last letter. The other cases guard behavior that must not change.
'''

import pytest

import grc_macronizer.class_text as class_text
from grc_macronizer.class_text import Text


def make_text(text, macronized_words):
    t = Text.__new__(Text)  # bypass __init__ (odyCy); integrate() needs only these attributes
    t.text = text
    t.macronized_words = macronized_words
    t.debug = False
    return t


@pytest.mark.parametrize("text, macronized_words, expected", [
    pytest.param(
        "περὶ τοῦ ῾πάντα ἐστὶν ἀόριστα καὶ πάντα",
        ["῾πά^ντα^", "πά^ντα^"],
        "περὶ τοῦ ῾πά^ντα^ ἐστὶν ἀόριστα καὶ πά^ντα^",
        id="rough-breathing-as-opening-quote"),
    pytest.param(
        "πάντα μὲν οὖν ῾πάντα ἐστὶν ἀκατάληπτα'",
        ["πά^ντα^", "῾πά^ντα^"],
        "πά^ντα^ μὲν οὖν ῾πά^ντα^ ἐστὶν ἀκατάληπτα'",
        id="bare-word-first"),
    pytest.param(
        "τὸ δὲ ῾ δύναται βαδίζειν῾ καὶ βαδίζειν",
        ["βα^δί^ζειν῾", "βα^δί^ζειν"],
        "τὸ δὲ ῾ δύναται βα^δί^ζειν῾ καὶ βα^δί^ζειν",
        id="rough-breathing-as-closing-quote"),
    pytest.param(
        "ὁ τρίτοϲ \x7fτύποϲ πάϲϲων καὶ τύποϲ",
        ["\x7fτύ^ποϲ", "τύ^ποϲ"],
        "ὁ τρίτοϲ \x7fτύ^ποϲ πάϲϲων καὶ τύ^ποϲ",
        id="control-character-attached"),
    pytest.param(
        "ἀλλήλοις “ἔστιν ἀπόδειξις” καὶ ἔστιν",
        ["ἔστι^ν", "ἔστι^ν"],
        "ἀλλήλοις “ἔστι^ν ἀπόδειξις” καὶ ἔστι^ν",
        id="word-with-attached-quotation-mark-still-matches"),
    pytest.param(
        "῾πάντα καὶ ῾πάντα πάντα",
        ["῾πά^ντα^", "῾πά^ντα^", "πά^ντα^"],
        "῾πά^ντα^ καὶ ῾πά^ντα^ πά^ντα^",
        id="bare-word-after-several-quoted-tokens"),
    pytest.param(
        "καθ' ἡμέραν καὶ καθ ἡμέραν",
        ["κα^θ"],
        "καθ' ἡμέραν καὶ κα^θ ἡμέραν",
        id="elided-word-is-its-own-word"),
    pytest.param(
        "τἄλλα^ πάντα",
        ["πά^ντα^"],
        "τἄλλα^ πά^ντα^",
        id="premarked-word-mark-is-a-boundary"),
    pytest.param(
        "«πάντα», (πάντα) πάντα· πάντα;",
        ["πά^ντα^", "πά^ντα^", "πά^ντα^", "πά^ντα^"],
        "«πά^ντα^», (πά^ντα^) πά^ντα^· πά^ντα^;",
        id="punctuation-delimits"),
    pytest.param(
        "ἄνα ἄνα ἄνα",
        ["ἄ^να^", "ἄ_να^"],
        "ἄ^να^ ἄ_να^ ἄνα",
        id="repeated-word-in-order"),
])
def test_integrate(text, macronized_words, expected):
    out = make_text(text, macronized_words).integrate()
    assert out == expected
    strip = lambda s: s.replace("^", "").replace("_", "")
    assert strip(out) == strip(text)  # only marks were added


def test_no_macronized_words_leaves_text_unchanged():
    assert make_text("πάντα ῥεῖ", []).integrate() == "πάντα ῥεῖ"


def test_corrupted_integration_raises(monkeypatch):
    # make 'πάντες^' be found at πάντα's span, so the replacement changes letters:
    # integrate() must raise instead of returning the corrupted text
    monkeypatch.setattr(class_text, "normalize_word", lambda w: "πάντα")
    with pytest.raises(AssertionError, match="Integration corrupted the text"):
        make_text("πάντα", ["πάντες^"]).integrate()
