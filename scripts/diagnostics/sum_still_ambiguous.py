import os
from collections import defaultdict

def aggregate_word_counts_from_tsv(folder_path):
    word_counts = defaultdict(int)

    for filename in os.listdir(folder_path):
        if filename.endswith('.tsv'):
            with open(os.path.join(folder_path, filename), encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2 and parts[0].isdigit():
                        count = int(parts[0])
                        word = parts[1]
                        word_counts[word] += count

    return dict(word_counts)

if __name__ == "__main__":
    folder_path = 'diagnostics/still_ambiguous'
    counts = aggregate_word_counts_from_tsv(folder_path)

    with open('oga_still_ambiguous.tsv', 'w', encoding='utf-8') as f:
        for word, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{word}\t{count}\n")
