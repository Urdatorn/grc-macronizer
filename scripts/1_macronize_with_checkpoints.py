# python 1_macronize_with_checkpoints.py opera_graeca_batch_0.txt macronized/oga_0.tsv --start-line 8690
# python 1_macronize_with_checkpoints.py opera_graeca_batch_1.txt macronized/oga_1.tsv --start-line 8690
# python 1_macronize_with_checkpoints.py opera_graeca_batch_2.txt macronized/oga_2.tsv --start-line 9072
# python 1_macronize_with_checkpoints.py opera_graeca_batch_3.txt macronized/oga_3.tsv --start-line 9072

# 1_macronize_with_checkpoints.py
import warnings
warnings.filterwarnings("ignore", message=".*Can't initialize NVML.*", category=UserWarning)

import argparse
import re
import sys
import signal

from grc_macronizer import Macronizer
from grc_utils import lower_grc, vowel

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

macronizer = Macronizer(make_prints=True, doc_from_file=False, no_hypotactic=True)

# Handle SIGINT (Ctrl+C)
def signal_handler(sig, frame):
    print("\nAborted by user. Cleaning up...")
    sys.exit(130)

signal.signal(signal.SIGINT, signal_handler)

# CLI arguments
parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="Path to the input file")
parser.add_argument("output_file", help="Path to the output file")
parser.add_argument("--start-line", type=int, default=0, help="Line number to resume from (default: 0)")
args = parser.parse_args()

CHUNK_SIZE = 500

# Read and preprocess input lines
try:
    with open(args.input_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
        print(f'Total lines: {len(all_lines)}')
except FileNotFoundError:
    print(f"File '{args.input_file}' not found.")
    sys.exit(1)

all_lines = [normalize_lunate_sigma(line) for line in all_lines]
all_lines = [lower_first_word(line) for line in all_lines]
all_lines = [line for line in all_lines if any(vowel(char) for char in line)]

lines = all_lines[args.start_line:]
total_lines = len(lines)

with open(args.output_file, 'a', encoding='utf-8') as out_f:
    for i in range(0, total_lines, CHUNK_SIZE):
        chunk_lines = lines[i:i + CHUNK_SIZE]
        chunk_text = ''.join(chunk_lines)
        absolute_start_line = args.start_line + i

        try:
            output = macronizer.macronize(chunk_text)
            if not output:
                print(f"Warning: macronizer returned empty output for lines {absolute_start_line}–{absolute_start_line + len(chunk_lines)}")
                continue

            macronized_lines = output.splitlines()
            original_lines = [line.rstrip('\n') for line in chunk_lines]

            if len(macronized_lines) != len(original_lines):
                print(f"Mismatch at line {absolute_start_line}: {len(original_lines)} input vs {len(macronized_lines)} output lines")
                sys.exit(1)

            # ✅ Changed this block:
            for j, (orig, macr) in enumerate(zip(original_lines, macronized_lines)):
                macr_clean = macr.replace("^", "").replace("_", "")
                if macr_clean == orig:
                    out_f.write(f"{orig}\t{macr}\n")
                else:
                    print(f"Skipped mismatched line {absolute_start_line + j}: {orig} ≠ {macr_clean}")

            out_f.flush()
            print(f"Processed and saved lines up to {absolute_start_line + len(chunk_lines)}")

        except KeyboardInterrupt:
            print(f"\nInterrupted. Last successfully processed line: {absolute_start_line}")
            sys.exit(130)
        except Exception as e:
            print(f"Error at line {absolute_start_line}: {e}")
            sys.exit(1)

print("All done.")