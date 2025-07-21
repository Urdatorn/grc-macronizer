import re
import time

from grc_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer(make_prints=False, doc_from_file=False)

input = "καθ' ἃς φαίνε' ὑπ' αὐτῶν καθ' ἑκάστην ἡμέραν"

time_start = time.time()
output = macronizer.macronize(input)
time_end = time.time()

output_split = [sentence for sentence in re.findall(r'[^.\n;\u037e]+[.\n;\u037e]?', output) if sentence]
for line in output_split[:500]:
    print(colour_dichrona_in_open_syllables(line))

print(f"Time taken: {time_end - time_start:.2f} seconds")