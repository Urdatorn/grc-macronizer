import sys

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
