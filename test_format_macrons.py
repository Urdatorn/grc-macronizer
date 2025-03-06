'''
pytest
'''

from anabasis_unicode import anabasis_unicode # long string with unicode macra and brevia used for testing
from format_macrons import macron_markup_to_unicode, macron_unicode_to_markup, macron_integrate_markup


def test_anabasis_conversion():
        anabasis_markup = macron_unicode_to_markup(anabasis_unicode)
        assert anabasis_unicode == macron_markup_to_unicode(anabasis_markup)


def test_macron_integrate_markup():
        test_word = 'νεανίας'
        test_macrons = '_3,^5,_6'
        assert macron_integrate_markup(test_word, test_macrons) == 'νεα_νί^α_ς'