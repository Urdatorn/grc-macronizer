'''
ALGORITHMIC MACRONIZING: NOMINAL FORMS


See page 38 in CGCG for endings of nominal forms: ref/cgcg_nominal_forms.png

SUMMARY OF THE RELEVANT RULES OF NOMINAL FORMS

#1D (fem)
- Nom and ac and voc sing -α are LONG if they come from a lemma which has an Ionian -η counterpart (needs to search lexica).
- Gen sing -ας is always long
- Acc pl => long ας if lemma is clearly 1D, i.e. is on -α or -η (because acc pl fem of 3D are short).

#2D
- Nom and acc pl (neut): => short α (the only dichronon; Same as neuter pl 3D.)

#3D
- Dat sing: short ι (all datives on iota are short)
- Acc sing (masc) => short α
- Nom and acc pl (neut) => short α, i.e. if noun is masc or neut and ends on -α, that α is short***
- Dat pl: short ι; see dat sing.
- Acc pl (masc) => short α. Cf. 1D acc pl.

***NB: Note that some *dual* forms (1D on -ης) can be masculine on long -α, e.g. τὼ προφήτᾱ, ὁπλῑ́τᾱ (cf. voc. sing. ὠ προφῆτα)
While not the case for 2D/3D and the most common masculione duals like χεροῖν, χεῖρε,
duals like χεροῖν also break the dative rule. Hence all duals are to be excluded tout court.

This yields the following six fully generalizable rules:
    
    (1) -α_ for 1D nouns in nominative/vocative singular feminine
    (2) -α_ν for 1D nouns in accusative singular feminine
    (3) -α_ς for 1D nouns in genitive singular feminine
    (4) nouns in accusative plural feminine, and lemma ending with η or α, ending -ας is long
    (5) for all masculine and neutre nouns, the ending -α is short
    (6) for all datives, the ending -ι is short
        - e.g. γυναιξί(ν)

For reference, here are all possible POS types in spaCy: 
    spacy_pos_tags = {
        "ADJ", "ADP", "ADV", "AUX", "CCONJ", "DET", "INTJ", 
        "NOUN", "NUM", "PART", "PRON", "PROPN", "PUNCT", 
        "SCONJ", "SYM", "VERB", "X"
    }

The following have nominal forms in grc:
    nominal_pos_tags = {"NOUN", "PROPN", "PRON", "NUM", "ADJ"}
'''

from db.ionic import ionic
from grc_utils import only_bases

### THE 3 ALGORITHMS RE NOMINAL FORMS
# long_fem_alpha(token, tag, lemma)
# short_masc_neut_alpha(token, tag)
# short_dat(token, tag)

def macronize_nominal_stem_suffixes(word, lemma, pos, morph, debug=False):
    '''
    The idea is to try and catch some common ways to form words; primarily adjectives.
    We have to tread carefully, because the risk of accidentally including too much is super high here.
    '''
    if only_bases(lemma)[-4:] == "ικος":
        if only_bases(word)[-4:] == "ικος" or only_bases(word)[-4:] == "ικον":
            return word[:-3] + "^" + word[-3:]

def macronize_nominal_forms(word, lemma, pos, morph, debug=False):
    '''
    This function should only be called if ultima or penultima is not yet macronized.
    It is slow and because of its complexity, bug prone.
    A large chunk of its use cases should be covered by the accent-rule method.
    It is primarily useful for *oxytones*.
    '''

    if not word or not lemma or not pos or not morph: # TODO: is this necessary?
        return word

    nominal_pos_tags = {"NOUN", "PROPN", "PRON", "NUM", "ADJ"}

    # if pos not in nominal_pos_tags or (morph is not None and "Dual" in morph.get("Number", [])):
    #     if debug:
    #         print(f"{word} is {pos} which is not NOUN or ADJ; or is DUAL")
    #     return word

    if debug:
        print(f'odyCy on {word}: \n\tLemma {lemma}, \n\tPOS: {pos}, \n\tMorphology: {morph}')

    def first_declination(word, lemma, morph):
        '''
        Nominal-form algorithms for 1st declension endings.
        '''

        # -α_ for 1D nouns in nominative/vocative singular feminine
        if only_bases(word)[-1:] == "α" and word == lemma and ('Nom' in morph.get("Case") or 'Voc' in morph.get("Case")) and 'Sing' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            etacist_version = word[:-1] + "η"
            if any(etacist_version[:-1] == ionic_word[:-1] and etacist_version[-1] == only_bases(ionic_word[-1]) for ionic_word in ionic):
                if debug:
                    print(f'\033[1;32m{word}: 1D case 1\033[0m')
                return word + "_"

        # -α_ν for 1D nouns in accusative singular feminine
        elif only_bases(word)[-2:] == "αν" and 'Acc' in morph.get("Case") and 'Sing' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            if debug:
                print('pass 1')
            if lemma[-1] in ["η", "α"]:
                etacist_lemma = lemma[:-1] + "η"
                if debug:
                    print(f'Etacist lemma: {etacist_lemma}')
                if any(etacist_lemma[:-1] == ionic_word[:-1] and etacist_lemma[-1] == only_bases(ionic_word[-1]) for ionic_word in ionic):
                    if debug:
                        print(f'\033[1;32m{word}: 1D case 2\033[0m')
                    return word[:-1] + "_" + word[-1]

        # -α_ς for 1D nouns in genitive singular feminine
        elif only_bases(word)[-2:] == "ας" and 'Gen' in morph.get("Case") and 'Sing' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            if debug:
                print(f'\033[1;32m{word}: 1D case 3\033[0m')
            return word[:-1] + "_" + word[-1]
        
        # -α_ς for 1D nouns in accusative plural feminine
        elif only_bases(word)[-2:] == "ας" and 'Acc' in morph.get("Case") and 'Plur' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            if pos in ["NOUN", "PROPN"]: # words with one gender
                if lemma[-1] in ["η", "α"]:
                    if debug:
                        print(f'\033[1;32m{word}: 1D case 4 for NOUN\033[0m')
                    return word[:-1] + "_" + word[-1]
            elif pos in ["ADJ", "NUM", "PRON"]: # words whose lemma is probably in masculine
                if debug:
                    print(f'\033[1;32m{word}: 1D case 4 for ADJ\033[0m')
                return word[:-1] + "_" + word[-1]
        
        else:
            return word
    
    def masc_and_neutre_short_alpha(word, morph):
        if only_bases(word)[-1:] == "α" and ('Masc' in morph.get("Gender") or 'Neut' in morph.get("Gender")):
            if debug:
                print(f'\033[1;32m{word}: Masc/Neut short alpha\033[0m')
            return word + "^"
        
        return word
    
    def dative_short_iota(word, morph):
        '''
        Note optional ny ephelkystikon!
        '''
        if 'Dat' in morph.get("Case"):
            if only_bases(word)[-1:] == "ι":
                if debug:
                    print(f'\033[1;32m{word}: Dat short iota\033[0m')
                return word + "^"
            elif only_bases(word)[-2:] == "ιν":
                if debug:
                    print(f'\033[1;32m{word}: Dat short iota (with ny ephelkystikon)\033[0m')
                return word[:-1] + "^" + word[-1]
        return word
    
    result = first_declination(word, lemma, morph)
    if result:
        return result
    
    result = masc_and_neutre_short_alpha(word, morph)
    if result:
        return result
    
    result = dative_short_iota(word, morph)
    if result:
        return result
    
    return word

#
# Asserts for all the rules and sub-rules
# NB: Uncomment after every change to macronize_nominal_forms
#

if __name__ == "__main__":
    print("Running asserts for macronize_nominal_forms...")

    import warnings
    import grc_odycy_joint_trf

    warnings.filterwarnings('ignore', category=FutureWarning)

    nlp = grc_odycy_joint_trf.load()

    try:
        # (1) -α_ for 1D nouns in nominative/vocative singular feminine
        output = nlp("κιθάρα")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "κιθάρα_"

        # (2) -α_ν for 1D nouns in accusative singular feminine
        output = nlp("κιθάραν")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph
        
        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "κιθάρα_ν"

        # (3) -α_ς for 1D nouns in genitive singular feminine
        output = nlp("κιθάρας")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "κιθάρα_ς"

        # (4) nouns in accusative plural feminine, and lemma ending with η or α, ending -ας is long
        output = nlp("καλάς")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "καλά_ς"

        # (5) for all masculine and neutre nouns, the ending -α is short
        output = nlp("ὁπλίτα")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        #assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "ὁπλίτα^" 

        # (6) for all datives, the ending -ι is short
        output = nlp("γυναιξί")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "γυναιξί^"

        output = nlp("γυναιξίν")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == "γυναιξί^ν"

        # (Extra) No duals
        output = nlp("χεροῖν")
        token = output[0]
        word = token.orth_
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        assert macronize_nominal_forms(word, lemma, pos, morph, debug=True) == None

    except AssertionError:
        print(f"Assertion failed for input: {input}")