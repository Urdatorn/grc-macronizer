'''
Helper functions to parse CoNLL-U files and convert UD morphological features
to spaCy-style morphological features.

Contents from higher to lower level:
- parse_conllu_file: Function to parse a CoNLL-U file and return a list of sentences, where each sentence is a list of token dictionaries.
    - convert_ud_morph_to_spacy_morph: Function to convert UD morphological features string to a spaCy-style morph dictionary.
        - convert_ud_morph_value_to_spacy: Function to convert UD feature values to spaCy values.
            - UD_VALUE_TO_SPACY: A dictionary mapping UD feature values to spaCy values.

'''

from typing import List, Dict, Any

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
    """
    Convert UD morphological feature values to spaCy style.
    UD typically uses lowercase abbreviations (n, m, s) while 
    spaCy uses longer forms with uppercase first letter (Nom, Masc, Sing).
    """
    
    # Use the class-level dictionary for default mappings
    if feature in UD_VALUE_TO_SPACY and value in UD_VALUE_TO_SPACY[feature]:
        return UD_VALUE_TO_SPACY[feature][value]
    
    return value  # Default to original value if no mapping exists

def convert_ud_morph_to_spacy_morph(ud_feats: str) -> str:
    """
    Convert UD morphological features string to a spaCy-style morph string.
    
    Args:
        ud_feats: The UD format features string (e.g. "Case=n|Gender=m|Number=s")
        
    Returns:
        A spaCy-style morphological features string (e.g. "Case=Nom|Gender=Masc|Number=Sing")
    """
    if ud_feats == '_':
        return ''
        
    spacy_feats = []
    for feat in ud_feats.split('|'):
        if '=' not in feat:
            continue
            
        key, value = feat.split('=')
        spacy_value = convert_ud_morph_value_to_spacy(key, value)
        spacy_feats.append(f"{key}={spacy_value}")
        
    return '|'.join(spacy_feats)

def parse_conllu_file(conllu_file_path: str) -> List[List[Dict[str, Any]]]:
    """
    Parse a CoNLL-U file and return a list of sentences, where each sentence
    is a list of token dictionaries.
    """
    sentences = []
    current_sentence = []
    
    with open(conllu_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                if current_sentence:
                    sentences.append(current_sentence)
                    current_sentence = []
                continue
            
            # Parse token fields
            fields = line.split('\t')
            if len(fields) != 10:
                continue  # Skip malformed lines
            
            # CoNLL-U fields
            token_id, form, lemma, upos, xpos, feats, head, deprel, deps, misc = fields
            
            # Skip range tokens (like 1-2)
            if '-' in token_id:
                continue
            
            # Parse morphological features
            morph_dict = convert_ud_morph_to_spacy_morph(feats)
            
            token = {
                'id': token_id,
                'text': form,
                'lemma': lemma if lemma != '_' else '',
                'pos': upos if upos != '_' else '',  # Use UPOS directly
                'morph': morph_dict
            }
            
            current_sentence.append(token)
        
        # Don't forget the last sentence
        if current_sentence:
            sentences.append(current_sentence)
    
    return sentences
