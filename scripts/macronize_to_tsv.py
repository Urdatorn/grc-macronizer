import sys
import signal
from tqdm import tqdm
from grc_macronizer import Macronizer
from grc_utils import count_dichrona_in_open_syllables

def main():
    macronizer = Macronizer(make_prints=False)

    input_file = sys.argv[1]

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            input_sentences = f.read().splitlines()
    except FileNotFoundError:
        print(f"File '{input_file}' not found.")
        sys.exit(1)

    if not input_sentences:
        print("No sentences found in input.")
        sys.exit(1)

    length = len(input_sentences)
    batch_size = length // 4

    batches = [
        input_sentences[:batch_size],
        input_sentences[batch_size:2 * batch_size],
        input_sentences[2 * batch_size:3 * batch_size],
        input_sentences[3 * batch_size:]
    ]

    print("Finished preparation... Ready to execute!")

    # Function to handle SIGINT (Ctrl+C)
    def signal_handler(sig, frame):
        print("\nAborted by user. Cleaning up...")
        sys.exit(130)  # 128 + SIGINT

    # Register the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    try:
        counter = 0
        for i, batch_input_sentences in tqdm(enumerate(batches), desc="Macronizing batches", total=len(batches), unit="batch"):
            batch_text = "\n".join(batch_input_sentences)
            output_sentences = macronizer.macronize(batch_text)

            with open(f'{input_file}_batch_{i}.tsv', 'w', encoding='utf-8') as f:
                for input_sentence, output_sentence in zip(batch_input_sentences, output_sentences):
                    if count_dichrona_in_open_syllables(output_sentence) == 0:
                        f.write(f"{input_sentence.strip()}\t{output_sentence.strip()}\n")
                        counter += 1

        print(f"\nWrote {counter} tsv lines with each and every second column entry macronized with consummate perfection.")

    except KeyboardInterrupt:
        # If the signal was caught, it'll now exit cleanly
        pass

if __name__ == "__main__":
    main()