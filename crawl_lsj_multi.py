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
from grc_utils import count_dichrona_in_open_syllables, macrons_map
from greek_accentuation.characters import length

from db.lsj_keys import lsj_keys
from db.crawl_lsj_backup_34425 import lsj

SHORT = '̆'
LONG = '̄'

current_time = time.strftime("%H:%M")

def get_macronized_word(greek_word):
    url = f"https://lsj.gr/wiki/{greek_word}"
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    
    # Random wait time
    wait_time = random.uniform(1, 4)
    #print(f"Waiting for {wait_time:.2f} seconds before making a request...")
    time.sleep(wait_time)
    
    try:
        response = session.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            span_elements = soup.find_all('span', title="Look up on Google")
            if span_elements:
                word = span_elements[0].get_text()
                print(f'\n[{current_time}] Found: \033[32m{word}\033[0m')
                return word
            else:
                print(f'\n\033[31mNo span elements found for {greek_word}\033[0m')
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

# Function to save progress to the output file
def save_progress(output_file, macronized_words_dict):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("lsj = {\n")
        for key, word in macronized_words_dict.items():
            f.write(f'    "{key}": "{word}",\n')
        f.write("}\n")
    print(f"Progress saved: {len(macronized_words_dict)} words processed")

# Load already processed words from the output file if it exists
output_file = "db/crawl_lsj.py"

# Filter out already processed keys
remaining_keys = [key for key in lsj_keys if key not in lsj and count_dichrona_in_open_syllables(key) > 0]

# Set up periodic save interval (every 50 processed words)
save_interval = 50
processed_since_last_save = 0

try:
    # Use ThreadPoolExecutor for concurrent crawling
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all tasks
        futures = {executor.submit(process_key, key): key for key in remaining_keys}
        completed_futures = set()
        
        # Process as futures complete
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing keys"):
            try:
                key, word = future.result()
                completed_futures.add(future)
                if has_macron_or_breve(word):
                    lsj[key] = macron_unicode_to_markup(word)
                    processed_since_last_save += 1
                    
                    # Save progress periodically
                    if processed_since_last_save >= save_interval:
                        save_progress(output_file, lsj)
                        processed_since_last_save = 0
                        
            except Exception as e:
                print(f"Error processing key: {e}")
            time.sleep(0.1)  # Add a small delay to avoid overwhelming the server
            
except KeyboardInterrupt:
    print("\nKeyboardInterrupt detected. Saving current progress...")
    # Process any completed but unprocessed futures
    for future in [f for f in futures if f.done() and f not in completed_futures]:
        try:
            key, word = future.result()
            if has_macron_or_breve(word):
                lsj[key] = macron_unicode_to_markup(word)
        except Exception:
            pass  # Skip errors during cleanup
    
    # Save final progress
    save_progress(output_file, lsj)
    print("Exiting gracefully...")

# Final save after normal completion
save_progress(output_file, lsj)
