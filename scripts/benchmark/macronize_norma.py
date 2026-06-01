"""
Preparing a folder with the 15 remacronized Norma texts for benchmarking.
First stripping syll boundaries and existing ^_.
"""

import os
import signal
import sys
from tqdm import tqdm
from grc_macronizer import Macronizer

macronizer = Macronizer(make_prints=False, lowercase=True)

input_folder = "norma-syllabarum-graecarum/final"
output_folder = "norma_macronizer"
os.makedirs(output_folder, exist_ok=True)

def handle_sigint(sig, frame):
    print("\n⚠️  Caught Ctrl-C, exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)  # install handler

for filename in tqdm(os.listdir(input_folder), desc="Files"):
    if filename.endswith(".txt"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)

        with open(input_path, "r", encoding="utf-8") as infile, \
             open(output_path, "w", encoding="utf-8") as outfile:
            for line in tqdm(infile, desc=f"{filename}", leave=False):
                line = line.rstrip("\n")
                line = line.replace("^", "").replace("_", "").replace("[", "").replace("]", "").replace("{", "").replace("}", "")
                macronized = macronizer.macronize(line)
                outfile.write(macronized + "\n")

print("Done!")