'''
Script to macronize the entire Opera Graeca Adnotata, 393.8 MB of text.

python macronize_oga.py opera_graeca_batch_0.txt macronized/oga_0.tsv
python macronize_oga.py opera_graeca_batch_1.txt macronized/oga_1.tsv
python macronize_oga.py opera_graeca_batch_2.txt macronized/oga_2.tsv
python macronize_oga.py opera_graeca_batch_3.txt macronized/oga_3.tsv

'''

import warnings
warnings.filterwarnings("ignore", message=".*Can't initialize NVML.*", category=UserWarning)

import argparse
import re
import sys
import signal
import time
from tqdm import tqdm

from grc_macronizer import Macronizer
from grc_utils import count_dichrona_in_open_syllables, lower_grc, vowel

#########################
### Settings          ###
#########################

CHUNK_SIZE = 1000
make_prints = False
no_hypotactic = True # Now trying with Hypotactic again
lowercase = True

#########################
### Utility functions ###
#########################

def macronization_stats(text:str, macronized_text:str) -> dict:
    count_before = count_dichrona_in_open_syllables(text)
    count_after = count_dichrona_in_open_syllables(macronized_text)
            
    difference = count_before - count_after
    ratio = difference / count_before if count_before > 0 else 0

    return difference, count_before, ratio

def normalize_lunate_sigma(text: str) -> str:
    text = re.sub(r'\u03f2(?=\s|$)', 'ς', text)
    return text.replace('\u03f2', 'σ')

def lower_first_word(text):
    parts = text.split(maxsplit=1)
    if not parts:
        return ''
    first, rest = parts[0], parts[1] if len(parts) > 1 else ''
    if any(vowel(ch) for ch in first):
        first = lower_grc(first)
    return f"{first} {rest}".rstrip()

def normalize_for_comparison(text: str) -> str:
    text = re.sub(r"[\^_\[\]‘’ʼ`⏑⏓(){}<>\-—…«»†×–]", "", text)
    text = text.replace("‘", "'").replace("’", "'").replace("ʼ", "'").replace("`", "'").replace("´", "'")
    return text.strip()

def signal_handler(sig, frame):
    print("\nAborted by user. Cleaning up...")
    sys.exit(130)

#########################
### CLI arguments     ###
#########################

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="Path to the input file")
parser.add_argument("output_file", help="Path to the output file")
parser.add_argument("--start-line", type=int, default=0, help="Line number to resume from (default: 0)")
args = parser.parse_args()

batch_nr = args.input_file.split('_')[-1].split('.')[0]

#########################
### Load and read     ###
#########################

signal.signal(signal.SIGINT, signal_handler)

macronizer = Macronizer(make_prints=make_prints, doc_from_file=False, no_hypotactic=no_hypotactic, lowercase=lowercase)

print(f"###########################################")
print(f"### Macronizing OGA batch {batch_nr}... ###")
print(f"###########################################")

try:
    with open(args.input_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
        print(f'Total lines: {len(all_lines)}')
except FileNotFoundError:
    print(f"File '{args.input_file}' not found.")
    sys.exit(1)

#########################
### Clean             ###
#########################

all_lines = [re.sub(r"[0-9]", "", line) for line in all_lines]  # Remove Arabic numerals
all_lines = [normalize_lunate_sigma(line) for line in all_lines]
all_lines = [lower_first_word(line) for line in all_lines]
all_lines = [normalize_for_comparison(line) for line in all_lines]
all_lines = [line for line in all_lines if any(vowel(char) for char in line)]
all_lines = [s[:-2] + s[-1] if len(s) >= 2 and s[-2] == ' ' else s for s in all_lines] # Experimental: Remove trailing spaces before punctuation

#########################
### Macronize batches ###
#########################

lines = all_lines[args.start_line:]
total_lines = len(lines)

total_chunks = (total_lines + CHUNK_SIZE - 1) // CHUNK_SIZE
print(f"Chunks: {total_chunks} of {CHUNK_SIZE} lines")

numerator = 0
denominator = 0

time_start = time.time()

with open(args.output_file, 'a', encoding='utf-8') as out_f: # 'a' = append mode
    for i in tqdm(range(0, total_lines, CHUNK_SIZE), desc=f"Macronizing batch {batch_nr}...", unit="chunk", total=total_chunks):
        chunk_lines = lines[i:i + CHUNK_SIZE]
        chunk_text = '\n'.join(line.rstrip('\n') for line in chunk_lines) + '\n' # rstrip('\n') removes trailing newlines, so we avoid double newlines
        absolute_start_line = args.start_line + i

        try:
            output = macronizer.macronize(chunk_text)
            if not output:
                print(f"Warning: macronizer returned empty output for lines {absolute_start_line}–{absolute_start_line + len(chunk_lines)}")
                continue

            a, b, c = macronization_stats(chunk_text, output)
            numerator += a
            denominator += b
            
            macronized_lines = output.splitlines()
            for macronized_line in macronized_lines:
                unmacronized_line = macronized_line.replace('^', '').replace('_', '')
                out_f.write(f"{unmacronized_line}\t{macronized_line}\n")

            out_f.flush()
            # tqdm.write(f"Processed and saved lines up to {absolute_start_line + len(chunk_lines)}")

        except Exception as e:
            tqdm.write(f"\n⚠️ Chunk-level error at lines {absolute_start_line}–{absolute_start_line + len(chunk_lines)}: {e}")

time_end = time.time()
total_time = (time_end - time_start) / 60**2 # Convert seconds to hours

print(f"\nMacronization completed for batch {batch_nr} in {total_time:.2f} hours.")

print(f"-----------------------------------------------------")
print(f"---------- Stats for batch {batch_nr} ---------------")
print(f"-----------------------------------------------------")

if denominator > 0:
    print(f"Total macronization = {numerator}/{denominator} = {numerator/denominator:.2%}")
else:
    print(f"Total macronization = {numerator}/{denominator} = N/A (no denominator)")

with open(f"stats_{batch_nr}.tsv", 'w', encoding='utf-8') as f:
    f.write(f"numerator\t{numerator}\n")
    f.write(f"denominator\t{denominator}\n")

