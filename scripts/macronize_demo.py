from grc_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer()

input = "αὐτόματον ἐκτετακὸς καὶ συνεσταλκός" # "automat som förlänger och förkortar"

output = macronizer.macronize(input)

print(colour_dichrona_in_open_syllables(output))