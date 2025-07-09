import os
import re
from collections import defaultdict

def aggregate_word_counts_from_py(folder_path):
    word_counts = defaultdict(int)
    pattern = re.compile(r"['\"](.*?)['\"].*?#\s*(\d+)\s*occurrence")

    for filename in os.listdir(folder_path):
        if filename.endswith('.py'):
            with open(os.path.join(folder_path, filename), encoding='utf-8') as f:
                for line in f:
                    match = pattern.search(line)
                    if match:
                        word, count = match.groups()
                        word_counts[word] += int(count)

    return dict(word_counts)

if __name__ == "__main__":
    folder_path = 'diagnostics/still_ambiguous'
    counts = aggregate_word_counts_from_py(folder_path)

    for word, count in sorted(counts.items(), key=lambda x: x[1]):
        print(f"{word:<20}\t{count:>4}")