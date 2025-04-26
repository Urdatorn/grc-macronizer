import sys
import signal
import warnings
import argparse

warnings.filterwarnings("ignore", message=".*Can't initialize NVML.*", category=UserWarning)

from grc_macronizer import Macronizer

macronizer = Macronizer(make_prints=True, doc_from_file=False)

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

CHUNK_SIZE = 1000

# Read and slice the input lines
try:
    with open(args.input_file, 'r', encoding='utf-8') as f:
        all_lines = f.readlines()
        print(f'Total lines: {len(all_lines)}')
except FileNotFoundError:
    print(f"File '{args.input_file}' not found.")
    sys.exit(1)

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

            for orig, macr in zip(original_lines, macronized_lines):
                out_f.write(f"{orig}\t{macr}\n")
            out_f.flush()

            print(f"Processed and saved lines up to {absolute_start_line + len(chunk_lines)}")

        except KeyboardInterrupt:
            print(f"\nInterrupted. Last successfully processed line: {absolute_start_line}")
            sys.exit(130)
        except Exception as e:
            print(f"Error at line {absolute_start_line}: {e}")
            sys.exit(1)

print("All done.")