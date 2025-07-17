'''
Here you can try the macronizer on the included test texts.
Just comment out the input with the text you want, and comment out everything else.

In general, Supplices (ἱκέτιδες in Greek) is in verse and 
a prosodically much more complex text than the straight-forward prose story Anabasis.
This is not a benchmark: I have added quite a few of the proper names of Anabasis to the custom db, 
as an example of the high results that can be achieved by manually "localizing" the macronizer to your target text.

A good work flow is to first run the macronizer as-is on your target text, inspect the list of un-disambiguated words in diagnostics/still_ambiguous, 
and then manually add the most common of them to the db/custom.py. 
Of course, "manually" could mean using a good LLM with research capabilities. 
'''

import re
import time

from grc_macronizer import Macronizer
from grc_macronizer.tests.hiketides import hiketides # "Supplices" by Sophocles
from grc_macronizer.tests.anabasis import anabasis, anabasis_medium, anabasis_short # "Anabasis" by Xenophon

from grc_utils import colour_dichrona_in_open_syllables, macronization_stats

macronizer = Macronizer(no_hypotactic=True, make_prints=True, lowercase=True)

#input = hiketides
#input = anabasis_short
#input = anabasis_medium
input = anabasis

time_start = time.time()
output = macronizer.macronize(input)
time_end = time.time()

numerator, denominator, ratio = macronization_stats(input, output) # use this if you want to use the stats
print(f"Total macronization = {numerator}/{denominator} = {ratio:.2%}")

output_split = [sentence for sentence in re.findall(r'([^.\n;\u037e]+[.;\u037e]?)\n?', output) if sentence]
for line in output_split[:10]:
    print(colour_dichrona_in_open_syllables(line))

print(f"Time taken: {time_end - time_start:.2f} seconds")