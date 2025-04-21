'''
This script is (at least initially!) *really* taxing on everyday computers because it runs four instances of the AI parts of the spaCy pipeline concurrently, and should either be run
    1) on a cluster or a powerful desktop or
    2) with `nice -n 19` and after having switched to max_workers=2 to avoid hangs or crashing the OS.

'''

import re
import sys
from tqdm import tqdm
from grc_macronizer import Macronizer
from grc_utils import count_dichrona_in_open_syllables

macronizer = Macronizer(make_prints=False, cores=4)

if __name__ == "__main__":
    # -- args --

    input_file = sys.argv[1]

    # -- Reading --

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_text = f.read()
    except FileNotFoundError:
        print(f"File '{input_file}' not found.")
        sys.exit(1)  # 1 means failure, 0 means success

    # -- Sentence grouping --

    # Group text into units ending with punctuation (Greek period, newline, semicolon, ano teleia)
    input_sentences = re.findall(r'.+?[.\n;\u037e]', input_text, flags=re.DOTALL)
    if not input_sentences:
        print("No sentences found in input.")
        sys.exit(1)

    # -- Batching --

    length = len(input_sentences)
    batch_size = length // 4

    batches = [
        "".join(input_sentences[:batch_size]),
        "".join(input_sentences[batch_size:2 * batch_size]),
        "".join(input_sentences[2 * batch_size:3 * batch_size]),
        "".join(input_sentences[3 * batch_size:])
    ]

    print("Finished preparation... Ready to execute!")

    # -- Executing --

    for i, batch in tqdm(enumerate(batches), desc="Macronizing batches", total=len(batches), unit="batch"):
        output_sentences = macronizer.macronize(batch)

        counter = 0
        with open(f'batch_{i}' + '.tsv', 'w', encoding='utf-8') as f:
            for input_sentence, output_sentence in zip(input_sentences, output_sentences):
                if count_dichrona_in_open_syllables(output_sentence) == 0:
                    f.write(f"{input_sentence.strip()}\t{output_sentence.strip()}\n")
                    counter += 1

    print(f"\nWrote {counter} tsv lines with each and every second column entry macronized with consummate perfection.")

    # -- Sanity check --

    # if len(input_sentences) != len(output_sentences):
    #     print(f"WARNING: sentence count mismatch: {len(input_sentences)} input vs {len(output_sentences)} output")
