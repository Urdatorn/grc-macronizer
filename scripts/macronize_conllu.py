from grc_macronizer import Macronizer
from grc_utils import colour_dichrona_in_open_syllables

def extract_text_from_conllu_file(file_path):
    sentences = []
    current_sentence = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                if current_sentence:
                    sentences.append(" ".join(current_sentence))
                    current_sentence = []
                continue
            if line.startswith("#") or '\t' not in line:
                continue
            cols = line.split('\t')
            if '-' in cols[0] or '.' in cols[0]:  # skip multiword or empty tokens
                continue
            current_sentence.append(cols[1])  # FORM field
        # final sentence if file doesn’t end in blank line
        if current_sentence:
            sentences.append(" ".join(current_sentence))
    return sentences

conllu_file_path = "scripts/test.conllu"

macronizer = Macronizer(no_hypotactic=True, conllu_file_path=conllu_file_path)

input = "".join(extract_text_from_conllu_file(conllu_file_path))

output = macronizer.macronize(input)

print(colour_dichrona_in_open_syllables(output))