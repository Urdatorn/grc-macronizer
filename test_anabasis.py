import unittest
from anabasis_unicode import anabasis_unicode
from format_macrons import macron_markup_to_unicode, macron_unicode_to_markup

anabasis_markup = macron_unicode_to_markup(anabasis_unicode)

class TestAnabasisUnicode(unittest.TestCase):
    def test_anabasis_conversion(self):
        self.assertEqual(anabasis_unicode, macron_markup_to_unicode(anabasis_markup))

if __name__ == '__main__':
    unittest.main()