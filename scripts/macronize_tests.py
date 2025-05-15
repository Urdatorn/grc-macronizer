import re
import time

from grc_macronizer import Macronizer
from grc_macronizer.tests.hiketides import hiketides # "Supplices" by Sophokles
from grc_macronizer.tests.anabasis import anabasis, anabasis_medium, anabasis_short # "Anabasis" av Xenophon

from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer(no_hypotactic=True)

input = anabasis

time_start = time.time()
output = macronizer.macronize(input)
time_end = time.time()

output_split = [sentence for sentence in re.findall(r'([^.\n;\u037e]+[.;\u037e]?)\n?', output) if sentence]
for line in output_split[:10]:
    print(colour_dichrona_in_open_syllables(line))

print(f"Time taken: {time_end - time_start:.2f} seconds")