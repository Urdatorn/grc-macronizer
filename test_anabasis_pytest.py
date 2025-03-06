from anabasis_unicode import anabasis_unicode
from format_macrons import macron_markup_to_unicode, macron_unicode_to_markup

anabasis_markup = macron_unicode_to_markup(anabasis_unicode)

def test_anabasis_conversion():
        assert anabasis_unicode == macron_markup_to_unicode(anabasis_markup)