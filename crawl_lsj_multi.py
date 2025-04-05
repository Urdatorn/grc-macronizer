import ast
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import random
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tqdm import tqdm
import time

from format_macrons import macron_unicode_to_markup
from grc_utils import macrons_map
from greek_accentuation.characters import length
from db.lsj_keys import lsj_keys

SHORT = '̆'
LONG = '̄'

def get_macronized_word(greek_word):
    url = f"https://lsj.gr/wiki/{greek_word}"
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    # Random wait time between 2 and 5 seconds (you can adjust these values)
    wait_time = random.uniform(2, 5)
    print(f"Waiting for {wait_time:.2f} seconds before making a request...")
    time.sleep(wait_time)
    
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            span_elements = soup.find_all('span', title="Look up on Google")
            if span_elements:
                word = span_elements[0].get_text()
                return word
            else:
                # Return a dummy placeholder if the word is not found
                return "NOT_FOUND"
    except requests.RequestException as e:
        print(f"Error fetching {greek_word}: {e}")
        # Return a dummy placeholder in case of an error
        return "NOT_FOUND"

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
