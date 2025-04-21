'''
On my MacBook: 
1 core: 37.10 seconds
2 cores: 35.26 seconds
3 cores: 35.77 seconds
4 cores: 37.12 seconds

'''

import re
import time

from grc_macronizer import Macronizer
#from grc_macronizer.tests.hiketides import hiketides
from grc_macronizer.tests.anabasis import anabasis
from grc_utils import colour_dichrona_in_open_syllables


if __name__ == "__main__":
    macronizer = Macronizer(make_prints=False, cores=4, doc_from_file=False)

    input = anabasis

    time_start = time.time()
    output = macronizer.macronize(input)
    time_end = time.time()

    output_split = [sentence for sentence in re.findall(r'[^.\n;\u037e]+[.\n;\u037e]?', output) if sentence]
    for line in output_split[:500]:
        print(colour_dichrona_in_open_syllables(line))

    print(f"Time taken: {time_end - time_start:.2f} seconds")