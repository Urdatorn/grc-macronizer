from grc_utils import oxia_to_tonos

grave_to_acute = {
    'ὰ': 'ά',
    'ὲ': 'έ',
    'ὴ': 'ή',
    'ὶ': 'ί',
    'ὸ': 'ό',
    'ὺ': 'ύ',
    'ὼ': 'ώ',
    'ῒ': 'ΐ',
    'ῢ': 'ΰ',
    'ἂ': 'ἄ',
    'ἃ': 'ἅ',
    'ἒ': 'ἔ',
    'ἓ': 'ἕ',
    'ἢ': 'ἤ',
    'ἣ': 'ἥ',
    'ἲ': 'ἴ',
    'ἳ': 'ἵ',
    'ὂ': 'ὄ',
    'ὃ': 'ὅ',
    'ὒ': 'ὔ',
    'ὓ': 'ὕ',
    'ὢ': 'ὤ',
    'ὣ': 'ὥ',
    'ᾂ': 'ᾄ',
    'ᾃ': 'ᾅ',
    'ᾲ': 'ᾴ',
    'ᾒ': 'ᾔ',
    'ᾓ': 'ᾕ',
    'ῂ': 'ῄ',
    'ᾢ': 'ᾤ',
    'ᾣ': 'ᾥ',
    'ῲ': 'ῴ'
}


def replace_grave_with_acute(string):
    '''
    Replaces grave accents with acute accents in a given string.
    '''
    return ''.join(grave_to_acute.get(char, char) for char in string)


if __name__ == '__main__':
    input_graves = 'ὰὲὶὸὺὴὼ'
    output_acutes = replace_grave_with_acute(input_graves)
    assert output_acutes == 'άέίόύήώ'
