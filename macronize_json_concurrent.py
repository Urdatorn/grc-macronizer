import json
import os
import time
import signal
from tqdm import tqdm
import concurrent.futures

from class_macronizer import Macronizer

# Worker function must be importable (for multiprocessing)
def macronize_verse(verse):
    macronizer = Macronizer()
    time.sleep(0.01)  # simulate delay
    return macronizer.macronize(verse)

# Read safe partial output if available
def read_existing_output(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
            if text:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
    return []

# Process a batch of verses concurrently
def process_batch(batch, max_workers=2):
    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(macronize_verse, batch))

# Main logic
def main():
    input_json = 'tests/unified_simplified.json'
    output_json = 'tests/unified_simplified_macronized.json'
    batch_size = 500
    max_workers = 2

    # Load input data
    with open(input_json, 'r', encoding='utf-8') as f:
        data = json.load(f)
    all_verses = [entry["verse_text"] for entry in data]

    # Load previously macronized entries
    completed_data = read_existing_output(output_json)
    completed_verses = {entry["verse_text"] for entry in completed_data}

    # Index of verses still needing processing
    remaining_indices = [i for i, verse in enumerate(all_verses) if verse not in completed_verses]
    total_remaining = len(remaining_indices)

    if total_remaining == 0:
        print("✅ All verses already macronized.")
        return

    print(f"🔄 Resuming from {len(completed_verses)} macronized verses. {total_remaining} remaining.")

    # Prepare for appending JSON
    is_first_entry = len(completed_data) == 0
    output_file_mode = 'w' if is_first_entry else 'r+'

    with open(output_json, output_file_mode, encoding='utf-8') as f:
        if is_first_entry:
            f.write('[\n')
        else:
            # Trim trailing ] so we can continue appending
            f.seek(0, os.SEEK_END)
            f.seek(f.tell() - 1, os.SEEK_SET)
            f.truncate()
            f.write(',\n')

        try:
            with tqdm(total=total_remaining, desc="🔧 Macronizing") as pbar:
                for i in range(0, total_remaining, batch_size):
                    batch_indices = remaining_indices[i:i + batch_size]
                    batch = [all_verses[j] for j in batch_indices]

                    macronized = process_batch(batch, max_workers=max_workers)

                    for idx, verse_index in enumerate(batch_indices):
                        data[verse_index]["verse_text"] = macronized[idx]
                        entry_json = json.dumps(data[verse_index], ensure_ascii=False, indent=4)

                        if not is_first_entry or f.tell() > 2:
                            f.write(',\n')
                        f.write(entry_json)
                        f.flush()
                        pbar.update(1)
                        is_first_entry = False

        except KeyboardInterrupt:
            print("\n⛔ Interrupted! Partial progress saved.")

        finally:
            f.write('\n]\n')
            print("💾 Output written to:", output_json)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.default_int_handler)
    main()