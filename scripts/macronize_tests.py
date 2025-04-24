import re
import time

from grc_macronizer import Macronizer
from grc_macronizer.tests.hiketides import hiketides # "Supplices" av Sofokles
from grc_macronizer.tests.anabasis import anabasis # "Anabasis" av Xenofon

from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer()

input = anabasis

time_start = time.time()
output = macronizer.macronize(input)
time_end = time.time()

output_split = [sentence for sentence in re.findall(r'([^.\n;\u037e]+[.;\u037e]?)\n?', output) if sentence]
for line in output_split[:10]:
    print(colour_dichrona_in_open_syllables(line))

print(f"Time taken: {time_end - time_start:.2f} seconds")