import json

INPUT = "macronizer2_adjusted.cast"
OUTPUT = "macronizer2_faster.cast"
SPEEDUP = 2.0  # Make it 2× faster (i.e. divide delays by 2)

with open(INPUT, "r", encoding="utf-8") as f:
    lines = [json.loads(line) for line in f]

header = lines[0]
events = lines[1:]

base_time = events[0][0]
new_events = []

for event in events:
    if isinstance(event, list) and isinstance(event[0], (int, float)):
        t, *rest = event
        new_t = base_time + (t - base_time) / SPEEDUP
        new_events.append([round(new_t, 6)] + rest)
    else:
        new_events.append(event)

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(json.dumps(header, ensure_ascii=False) + "\n")
    for e in new_events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")