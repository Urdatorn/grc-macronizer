import re

from class_macronizer import Macronizer
from tests.hiketides import hiketides
from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer(make_prints=False)

input = hiketides
output = macronizer.macronize(input)

output_split = re.split(r'[.\n]', output)
for line in output.split('.')[:10]:
    print(colour_dichrona_in_open_syllables(line))
