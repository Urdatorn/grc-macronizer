import sys
from tqdm import tqdm as original_tqdm

class tqdm(original_tqdm):
    def __init__(self, *args, **kwargs):
        if 'position' not in kwargs:
            kwargs['position'] = 1  # Default to line 1 (0-based index)
        super().__init__(*args, **kwargs)

from halo import Halo

from class_macronizer import Macronizer

from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer(debug=False)

input = sys.argv[1]

spinner = Halo(text='Macronizing', spinner='dots')
spinner.start()
output = macronizer.macronize(text=input, genre="prose", stats=True)
spinner.stop()

for line in output.split('\n'):
    print(colour_dichrona_in_open_syllables(line))
