numerator_sum = 0
denominator_sum = 0

for i in range(3):
    with open (f"stats_{i}.tsv", 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("numerator"):
                numerator_sum += int(line.split('\t')[1].strip())
            elif line.startswith("denominator"):
                denominator_sum += int(line.split('\t')[1].strip())

print(f"Total macronization across all batches = {numerator_sum}/{denominator_sum} = {numerator_sum/denominator_sum:.2%}" if denominator_sum > 0 else "Total macronization across all batches = N/A (no denominator)")