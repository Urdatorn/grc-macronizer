'''
'''

import sys
from pathlib import Path

from grc_utils import macrons_map, patterns, VOWELS

consonants = set(patterns['stops'] + patterns['liquids'] + patterns['nasals'] + patterns['double_cons'] + patterns['sibilants'])

def get_unique_chars_excluding(filepaths):
    unique_chars = set()

    for filepath in filepaths:
        with open(filepath, encoding='utf-8') as f:
            for line in f:
                for ch in line:
                    if not is_excluded(ch):
                        unique_chars.add(ch)

    return unique_chars

def is_excluded(ch):
    chars_to_clean = r'[\^_()\[\]{}<>⟨⟩⎡⎤\"«»\-—…|⏑⏓†×]'
    oga = r'[#$%&*+/=@~£¦§¨ª¬¯°±²³¶¸¹½¿ÁÄÆÈÉÌÍÒÓÖÚÜßàáâäæçèéëìíïòóôö÷ùúüýÿĀāćĎďĹŒœŕźƑǁȳɛʰʳ˘˙˝ˡˢˣ̠̣͎̀́̄̅̆̇̈̊̔͂͞ͅ΅ЗСҀҁҏӄӔӕֹלݲតហឲាិេᵃᵅᵇᵈᵉᵊᵍᵏᵐᵒᵖᵗᵘᵛᵝᶜᶠᶦᶹḍḿṃẂẃẉạụỳ‐‒–―‖✶❮❯⟦⟧⥼⥽⦵⨆⩚⩹⫯⸕⸢⸣⸤⸥⸨〈〉ﬀﬁ＊－｢�𐅵𝒢𝒮𝔮𝕷‹›※‾⁄⁎⁑⁰ⁱ⁴⁵⁶⁷⁸⁹ⁿ€™ℵ∗√∠∴∼∾⊏⊔⊙⊢⊣⊤⊻⋃⋆⋇⋖⌈⌉⌊⌋⌞⌟⏒⏔⏕─═║△○◻★☼☾☿♀♂♃♄]'
    apostrophes = "'’‘´΄\u02bc᾿′‵‛ʹʽ͵"
    
    code = ord(ch)

    # Greek polytonic: U+1F00–U+1FFF
    if 0x1F00 <= code <= 0x1FFF:
        return True

    # Latin: A-Z, a-z
    if 'A' <= ch <= 'Z' or 'a' <= ch <= 'z':
        return True

    # Arabic numerals: 0–9
    if '0' <= ch <= '9':
        return True

    if ch in chars_to_clean or ch in apostrophes:
        return True

    if ch in macrons_map or ch in VOWELS or ch in consonants:
        return True
    
    return False

if __name__ == "__main__":

    filepaths = ["opera_graeca_batch_0.txt", "opera_graeca_batch_1.txt", "opera_graeca_batch_2.txt", "opera_graeca_batch_3.txt"]
    chars = get_unique_chars_excluding(filepaths)

    # Remove control characters like newline, tab, etc.
    printable_chars = [c for c in sorted(chars) if c.isprintable() and not c.isspace()]
    print("".join(printable_chars))