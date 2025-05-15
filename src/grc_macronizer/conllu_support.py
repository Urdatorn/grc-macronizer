'''
Helper functions to parse CoNLL-U files and convert UD morphological features
to spaCy-style morphological features.

Contents from higher to lower level:
- parse_conllu_file: Function to parse a CoNLL-U file and return a list of sentences, where each sentence is a list of token dictionaries.
    - convert_ud_morph_to_spacy_morph: Function to convert UD morphological features string to a spaCy-style morph dictionary.
        - convert_ud_morph_value_to_spacy: Function to convert UD feature values to spaCy values.
            - UD_VALUE_TO_SPACY: A dictionary mapping UD feature values to spaCy values.

'''

from conllu import parse
import spacy
from spacy.tokens import Doc

class Morph:
    def __init__(self, morph_str: str):
        # Initialize with a string representing the morphological features
        self.morph_str = morph_str
        self.features = self._parse_morphology(morph_str)
    
    def _parse_morphology(self, morph_str: str) -> dict:
        # Parse the morph string into a dictionary like 'key=value'
        features = {}
        for feature in morph_str.split('|'):
            if '=' in feature:
                key, value = feature.split('=')
                features[key] = value
        return features
    
    def get(self, feature: str) -> str:
        # Mimic SpaCy's morph.get method to return a feature value
        return self.features.get(feature, '')

    def to_dict(self) -> dict:
        # Return the features as a dictionary
        return self.features
    
    def __repr__(self):
        return f"Morph({self.morph_str})"

UD_VALUE_TO_SPACY = {
    "Case": {
        "n": "Nom",    # Nominative
        "g": "Gen",    # Genitive
        "d": "Dat",    # Dative
        "a": "Acc",    # Accusative
        "v": "Voc",    # Vocative
        "l": "Loc",    # Locative (if used)
        "i": "Ins",    # Instrumental (if used)
        "nom": "Nom",  # Alternative notation
        "acc": "Acc",  # Alternative notation
    },
    "Number": {
        "s": "Sing",   # Singular
        "p": "Plur",   # Plural
        "d": "Dual",   # Dual
    },
    "Gender": {
        "m": "Masc",   # Masculine
        "f": "Fem",    # Feminine
        "n": "Neut",   # Neuter
    },
    "Mood": {
        "i": "Ind",    # Indicative
        "s": "Sub",    # Subjunctive
        "o": "Opt",    # Optative (specific to Ancient Greek)
        "m": "Imp",    # Imperative
        "p": "Part",   # Participle
        "n": "Inf",    # Infinitive
        "subj": "Sub", # Alternative notation
    },
    "Tense": {
        "p": "Pres",   # Present
        "i": "Imperf", # Imperfect
        "a": "Aor",    # Aorist (specific to Ancient Greek)
        "r": "Perf",   # Perfect
        "l": "Plup",   # Pluperfect
        "f": "Fut",    # Future
    },
    "Voice": {
        "a": "Act",    # Active
        "m": "Mid",    # Middle
        "p": "Pass",   # Passive
        "e": "MidPass", # Middle-Passive
    },
    "Person": {
        "1": "1",      # First person
        "2": "2",      # Second person
        "3": "3",      # Third person
    },
    "Aspect": {
        "i": "Imp",    # Imperfective
        "p": "Perf",   # Perfective
    },
    "Degree": {
        "p": "Pos",    # Positive
        "c": "Cmp",    # Comparative
        "s": "Sup",    # Superlative
    },
    # Add more as needed
}

def convert_ud_morph_value_to_spacy(feature: str, value: str) -> str:
    """Convert UD morph feature values to SpaCy-friendly values."""
    if feature in UD_VALUE_TO_SPACY and value in UD_VALUE_TO_SPACY[feature]:
        return UD_VALUE_TO_SPACY[feature][value]
    return value

def convert_ud_morph_to_spacy_morph(ud_feats: str) -> str:
    """Convert UD features to SpaCy morphological features format."""
    if ud_feats == '_' or not ud_feats:
        return ''
    spacy_feats = []
    for feat in ud_feats.split('|'):
        if '=' not in feat:
            continue
        key, value = feat.split('=')
        spacy_value = convert_ud_morph_value_to_spacy(key, value)
        spacy_feats.append(f"{key}={spacy_value}")
    return '|'.join(spacy_feats)

def parse_conllu_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    parsed_sentences = parse(content)
    result = []

    for sentence in parsed_sentences:
        tokens = []
        for token in sentence:
            if isinstance(token, dict) and token.get("form") and token.get("upostag"):
                tokens.append({
                    "text": token["form"],
                    "lemma": token.get("lemma", ""),
                    "pos": token["upostag"],
                    # Use Morph class here
                    "morph": Morph(token.get("feats", "")) if token.get("feats") else Morph("")
                })
        result.append(tokens)

    return result

def create_spacy_doc_from_conllu(conllu_file_path: str, nlp: spacy.language.Language):
    """Convert CONLL-U data into SpaCy Doc objects."""
    sentences = parse_conllu_file(conllu_file_path)
    docs = []

    for sentence in sentences:
        # Token texts (forms) of the sentence
        words = [token['text'] for token in sentence]
        
        # SpaCy Doc object creation
        doc = Doc(nlp.vocab, words=words)
        
        # Add the morph, pos, and lemma attributes to each token
        for i, token in enumerate(doc):
            spacy_token = doc[i]
            spacy_token.lemma_ = sentence[i]['lemma']
            spacy_token.pos_ = sentence[i]['pos']
            spacy_token.morph = sentence[i]['morph']  # This is where you set the morph value
            spacy_token.tag_ = sentence[i]['pos']  # Assuming POS as tag for simplicity

        docs.append(doc)

    return docs
