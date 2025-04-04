from concurrent.futures import ThreadPoolExecutor, as_completed
import pickle
import os
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import time
import unicodedata
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import ast  # For safely parsing the existing dictionary from the file

from greek_accentuation.characters import length

from db.lsj_keys_last_70k import lsj_keys

SHORT = '̆'
LONG = '̄'


macrons_map = {
    '\u1FB0': 'α',  # ᾰ: GREEK SMALL LETTER ALPHA WITH VRACHY
    '\u1FB8': 'Α',  # Ᾰ: GREEK CAPITAL LETTER ALPHA WITH VRACHY
    '\u1FB1': 'α',  # ᾱ: GREEK SMALL LETTER ALPHA WITH MACRON
    '\u1FB9': 'Α',  # Ᾱ: GREEK CAPITAL LETTER ALPHA WITH MACRON
    '\u03B1\u0306': 'α',  # ᾰ: GREEK SMALL LETTER ALPHA WITH VRACHY
    '\u0391\u0306': 'Α',  # Ᾰ: GREEK CAPITAL LETTER ALPHA WITH VRACHY
    '\u03B1\u0304': 'α',  # ᾱ: GREEK SMALL LETTER ALPHA WITH MACRON
    '\u0391\u0304': 'Α',  # Ᾱ: GREEK CAPITAL LETTER ALPHA WITH MACRON
    '\u1FB0\u0313': 'ἀ',  # ᾰ̓: GREEK SMALL LETTER ALPHA WITH BREVE/VRACHY COMBINING PSILI
    '\u1F00\u0306': 'ἀ',  # ἀ̆: GREEK SMALL LETTER ALPHA WITH PSILI + COMBINING BREVE/VRACHY TODO: 14/03 found in wikt
    '\u1f08\u0306': 'Ἀ',  # Ἀ̆: GREEK CAPITAL LETTER ALPHA WITH PSILI + COMBINING BREVE/VRACHY TODO: 14/03 found in wikt
    '\u1FB8\u0313': 'Ἀ',  # Ᾰ̓: GREEK CAPITAL LETTER ALPHA WITH VRACHY COMBINING COMMA ABOVE
    '\u1FB0\u0314': 'ἁ',  # ᾰ̔: GREEK SMALL LETTER ALPHA WITH VRACHY COMBINING REVERSED COMMA ABOVE
    '\u1f01\u0306': 'ἁ',  # ἁ̆: GREEK SMALL LETTER ALPHA WITH DASIA + COMBINING BREVE/VRACHY TODO: 14/03 found in wikt
    '\u1FB8\u0314': 'Ἁ',  # Ᾰ̔: GREEK CAPITAL LETTER ALPHA WITH VRACHY COMBINING REVERSED COMMA ABOVE
    '\u1FB0\u0301': 'ά',  # ᾰ́: GREEK SMALL LETTER ALPHA WITH VRACHY COMBINING ACUTE ACCENT
    '\u1FB0\u0300': 'ὰ',  # ᾰ̀: GREEK SMALL LETTER ALPHA WITH VRACHY COMBINING GRAVE ACCENT
    '\u1FB1\u0313': 'ἀ',  # ᾱ̓: GREEK SMALL LETTER ALPHA WITH MACRON COMBINING COMMA ABOVE
    '\u1FB9\u0313': 'Ἀ',  # Ᾱ̓: GREEK CAPITAL LETTER ALPHA WITH MACRON COMBINING COMMA ABOVE
    '\u1FB1\u0314': 'ἁ',  # ᾱ̔: GREEK SMALL LETTER ALPHA WITH MACRON COMBINING REVERSED COMMA ABOVE
    '\u1FB9\u0314': 'Ἁ',  # Ᾱ̔: GREEK CAPITAL LETTER ALPHA WITH MACRON COMBINING REVERSED COMMA ABOVE
    '\u1FB1\u0301': 'ά',  # ᾱ́: GREEK SMALL LETTER ALPHA WITH MACRON COMBINING ACUTE ACCENT
    '\u1FB1\u0300': 'ὰ',  # ᾱ̀: GREEK SMALL LETTER ALPHA WITH MACRON COMBINING GRAVE ACCENT
    '\u1FB1\u0345': 'ᾳ',  # ᾱͅ: GREEK SMALL LETTER ALPHA WITH MACRON COMBINING GREEK YPOGEGRAMMENI

    '\u1FD0': 'ι',  # ῐ: GREEK SMALL LETTER IOTA WITH VRACHY
    '\u1FD8': 'Ι',  # Ῐ: GREEK CAPITAL LETTER IOTA WITH VRACHY
    '\u1FD1': 'ι',  # ῑ: GREEK SMALL LETTER IOTA WITH MACRON
    '\u1FD9': 'Ι',  # Ῑ: GREEK CAPITAL LETTER IOTA WITH MACRON
    '\u03B9\u0306': 'ι',  # ῐ: GREEK SMALL LETTER IOTA WITH VRACHY
    '\u0399\u0306': 'Ι',  # Ῐ: GREEK CAPITAL LETTER IOTA WITH VRACHY
    '\u03B9\u0304': 'ι',  # ῑ: GREEK SMALL LETTER IOTA WITH MACRON
    '\u0399\u0304': 'Ι',  # Ῑ: GREEK CAPITAL LETTER IOTA WITH MACRON
    '\u1FD0\u0313': 'ἰ',  # ῐ̓: GREEK SMALL LETTER IOTA WITH VRACHY COMBINING COMMA ABOVE
    '\u1f30\u0306': 'ἰ',  # ἰ̆: GREEK SMALL LETTER IOTA WITH PSILI + COMBINING BREVE/VRACHY TODO: 14/03 found in wikt by AI
    '\u1FD8\u0313': 'Ἰ',  # Ῐ̓: GREEK CAPITAL LETTER IOTA WITH VRACHY COMBINING COMMA ABOVE
    '\u1f38\u0306': 'Ἰ',  # Ἰ̆: GREEK CAPITAL LETTER IOTA WITH PSILI + COMBINING BREVE/VRACHY TODO: 14/03 found in wikt by AI
    '\u1FD0\u0314': 'ἱ',  # ῐ̔: GREEK SMALL LETTER IOTA WITH VRACHY COMBINING REVERSED COMMA ABOVE
    '\u1f31\u0306': 'ἱ',  # ἱ̆: GREEK SMALL LETTER IOTA WITH DASIA + COMBINING BREVE/VRACHY TODO: 14/03 found in wikt by AI
    '\u1FD8\u0314': 'Ἱ',  # Ῐ̔: GREEK CAPITAL LETTER IOTA WITH VRACHY COMBINING REVERSED COMMA ABOVE
    '\u1FD0\u0301': 'ί',  # ῐ́: GREEK SMALL LETTER IOTA WITH VRACHY COMBINING ACUTE ACCENT
    '\u1FD0\u0300': 'ὶ',  # ῐ̀: GREEK SMALL LETTER IOTA WITH VRACHY COMBINING GRAVE ACCENT
    '\u1FD0\u0308': 'ϊ',  # ῐ̈: GREEK SMALL LETTER IOTA WITH VRACHY COMBINING DIAERESIS
    '\u03ca\u0306': 'ϊ',  # ϊ̆: GREEK SMALL LETTER IOTA WITH DIALYTIKA + COMBINING VRACHY TODO: 14/03 found in wikt
    '\u1FD1\u0313': 'ἰ',  # ῑ̓: GREEK SMALL LETTER IOTA WITH MACRON COMBINING COMMA ABOVE
    '\u1FD9\u0313': 'Ἰ',  # Ῑ̓: GREEK CAPITAL LETTER IOTA WITH MACRON COMBINING COMMA ABOVE
    '\u1FD1\u0314': 'ἱ',  # ῑ̔: GREEK SMALL LETTER IOTA WITH MACRON COMBINING REVERSED COMMA ABOVE
    '\u1FD9\u0314': 'Ἱ',  # Ῑ̔: GREEK CAPITAL LETTER IOTA WITH MACRON COMBINING REVERSED COMMA ABOVE
    '\u1FD1\u0301': 'ί',  # ῑ́: GREEK SMALL LETTER IOTA WITH MACRON COMBINING ACUTE ACCENT
    '\u1FD1\u0308': 'ϊ',  # ῑ̈: GREEK SMALL LETTER IOTA WITH MACRON COMBINING DIAERESIS

    '\u1FE0': 'υ',  # ῠ: GREEK SMALL LETTER UPSILON WITH VRACHY
    '\u1FE8': 'Υ',  # Ῠ: GREEK CAPITAL LETTER UPSILON WITH VRACHY
    '\u1FE1': 'υ',  # ῡ: GREEK SMALL LETTER UPSILON WITH MACRON
    '\u1FE9': 'Υ',  # Ῡ: GREEK CAPITAL LETTER UPSILON WITH MACRON
    '\u03C5\u0306': 'υ',  # ῠ: GREEK SMALL LETTER UPSILON WITH VRACHY
    '\u03A5\u0306': 'Υ',  # Ῠ: GREEK CAPITAL LETTER UPSILON WITH VRACHY
    '\u03C5\u0304': 'υ',  # ῡ: GREEK SMALL LETTER UPSILON WITH MACRON
    '\u03A5\u0304': 'Υ',  # Ῡ: GREEK CAPITAL LETTER UPSILON WITH MACRON
    '\u1FE0\u0313': 'ὐ',  # ῠ̓: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING COMMA ABOVE
    '\u1FE0\u0314': 'ὑ',  # ῠ̔: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING REVERSED COMMA ABOVE
    '\u1F51\u0306': 'ὑ',  # ὑ̆: GREEK SMALL LETTER UPSILON WITH DASIA + COMBINING VRACHY TODO: 14/03 just found that there are precomposed breathing marks
    '\u1FE8\u0314': 'Ὑ',  # Ῠ̔: GREEK CAPITAL LETTER UPSILON WITH VRACHY COMBINING REVERSED COMMA ABOVE
    '\u1FE0\u0301': 'ύ',  # ῠ́: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING ACUTE ACCENT
    '\u1FE0\u0300': 'ὺ',  # ῠ̀: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING GRAVE ACCENT
    '\u1FE0\u0342': 'ῦ',  # ῠ͂: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING GREEK PERISPOMENI
    '\u1FE0\u0308': 'ϋ',  # ῠ̈: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING DIAERESIS
    '\u1FE0\u0312': 'ύ',  # ῠ̒: GREEK SMALL LETTER UPSILON WITH VRACHY COMBINING TURNED COMMA ABOVE
    '\u1FE1\u0314': 'ὑ',  # ῡ̔: GREEK SMALL LETTER UPSILON WITH MACRON COMBINING REVERSED COMMA ABOVE
    '\u1FE9\u0314': 'Ὑ',  # Ῡ̔: GREEK CAPITAL LETTER UPSILON WITH MACRON COMBINING REVERSED COMMA ABOVE
    '\u1FE1\u0301': 'ύ',  # ῡ́: GREEK SMALL LETTER UPSILON WITH MACRON COMBINING ACUTE ACCENT
    '\u1FE1\u0308': 'ϋ',  # ῡ̈: GREEK SMALL LETTER UPSILON WITH MACRON COMBINING DIAERESIS
}

def oxia_to_tonos(string):
    mapping = {
        '\u1f71': '\u03AC',  # alpha
        '\u1f73': '\u03AD',  # epsilon
        '\u1f75': '\u03AE',  # eta
        '\u1f77': '\u03AF',  # iota
        '\u1f79': '\u03CC',  # omicron
        '\u1f7b': '\u03CD',  # upsilon
        '\u1f7d': '\u03CE'   # omega
    }
    return ''.join(mapping.get(char, char) for char in string)

def normalize_word(word):
    normalized = unicodedata.normalize('NFC', word)
    tonos = oxia_to_tonos(normalized)
    return tonos

def macron_unicode_to_markup(text):
    '''
    >>> macron_unicode_to_markup('νεᾱνῐ́ᾱς')
    >>> νεα_νί^α_ς

    NB1: Sending markup through this is fine; it will do nothing.
    NB2: I grappled with a unicode bug for a LONG time! The solution came from Grok 3.
    '''
    #if not SHORT in text and not LONG in text:
    #    return text

    # Step 1: Decompose into base characters and combining marks
    decomposed = unicodedata.normalize('NFD', text)
    
    result = ''
    i = 0
    while i < len(decomposed):
        char = decomposed[i]
        # Step 2: Check if this is a letter
        if unicodedata.category(char).startswith('L'):
            # Collect all combining marks for this base character
            diacritics = ''
            length_marker = ''
            i += 1
            # Step 3: Process combining marks
            while i < len(decomposed) and unicodedata.category(decomposed[i]).startswith('M'):
                mark = decomposed[i]
                # Step 4: Classify the mark
                if mark == LONG:  # Macron
                    length_marker = '_'
                elif mark == SHORT:  # Breve
                    length_marker = '^'
                else:
                    diacritics += mark  # Keep other diacritics (e.g., acute)
                i += 1
            # Step 5: Rebuild: base + diacritics + length marker
            result += char + diacritics + length_marker
        else:
            # Non-letter (e.g., punctuation), append as is
            result += char
            i += 1
    
    # Most Greek punctuation decomposes to Latin punctuation, so we need to revert that
    # middle dot (U+00B7) -> ano teleia (U+0387)
    # semicolon (U+003B) -> Greek question mark (U+037E)
    result = result.replace('\u00b7', '\u0387')
    result = result.replace('\u003b', '\u037e')
    return normalize_word(result)

# Function to get the macronized word from the LSJ website
def get_macronized_word(greek_word):
    url = f"https://lsj.gr/wiki/{greek_word}"
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            span_elements = soup.find_all('span', title="Look up on Google")
            if span_elements:
                word = span_elements[0].get_text()
                return word
    except requests.RequestException as e:
        print(f"Error fetching {greek_word}: {e}")
    return None

def has_macron_or_breve(word):
    if word:
        for char in word:
            if length(char) in [SHORT, LONG] or char in macrons_map:
                return True
    return False

# Function to process a single key and return its macronized word
def process_key(key):
    return key, get_macronized_word(key)

# Load already processed words from the output file if it exists
output_file = "db/crawl_lsj.py"
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        content = f.read()
        try:
            existing_data = ast.literal_eval(content.split("=", 1)[1].strip())  # Parse the dictionary
            macronized_words_lsj = existing_data if isinstance(existing_data, dict) else {}
        except Exception as e:
            print(f"Error loading existing data: {e}")
            macronized_words_lsj = {}
else:
    macronized_words_lsj = {}

# Filter out already processed keys
remaining_keys = [key for key in lsj_keys if key not in macronized_words_lsj]

try:
    # Use ThreadPoolExecutor for concurrent crawling
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_key, key): key for key in remaining_keys}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing keys"):
            try:
                key, word = future.result()
                if has_macron_or_breve(word):
                    macronized_words_lsj[key] = macron_unicode_to_markup(word)
            except Exception as e:
                print(f"Error processing key: {e}")
            time.sleep(0.1)  # Add a small delay to avoid overwhelming the server
except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected. Saving progress...")

# Save the dictionary to the output file
with open(output_file, "w", encoding="utf-8") as f:
    f.write("lsj = {\n")
    for key, word in macronized_words_lsj.items():
        f.write(f'    "{key}": "{word}",\n')
    f.write("}\n")
