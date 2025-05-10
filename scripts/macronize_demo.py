from grc_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

macronizer = Macronizer(no_hypotactic=True, custom_doc="/Users/albin/git/norma-syllabarum-graecarum/αὐτόματον-ἐκτετακὸς-cfb5386d67b46296.spacy")

input = "αὐτόματον ἐκτετακὸς καὶ συνεσταλκός" # "automat som förlänger och förkortar"

output = macronizer.macronize(input)

print(colour_dichrona_in_open_syllables(output))