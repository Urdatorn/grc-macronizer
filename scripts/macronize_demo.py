from grc_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

# Example of custom doc with non-standard name
macronizer = Macronizer(no_hypotactic=True, custom_doc="/Users/albin/git/macronize-tlg/odycy_docs/αὐτόματον.spacy")

input = "αὐτόματον ἐκτετακὸς καὶ συνεσταλκός"

output = macronizer.macronize(input)

print(colour_dichrona_in_open_syllables(output))