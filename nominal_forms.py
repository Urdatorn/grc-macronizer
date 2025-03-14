'''
ALGORITHMIC MACRONIZING PART 2

See page 38 in CGCG for endings of nominal forms.

RULES OF NOMINAL FORMS

#1D (fem)
- Nom and ac and voc sing -α are LONG if they come from a lemma which has an Ionian -η counterpart (needs to search lexica).
- Gen sing -ας is always long
- Acc pl => long ας if lemma is clearly 1D, i.e. is on -α or -η (because acc pl fem of 3D are short).

#2D
Nom and acc pl (neut): => short α (the only dichronon; Same as neuter pl 3D.)

#3D
Dat sing: short ι (all datives on iota are short)
Acc sing (masc) => short α
Nom and acc pl (neut) => short α, i.e. if noun is masc or neut and ends on -α, that α is short***
Dat pl: short ι; see dat sing.
Acc pl (masc) => short α. Cf. 1D acc pl.

***NB: Note that some *dual* forms (1D on -ης) can be masculine on long -α, e.g. τὼ προφήτᾱ, ὁπλῑ́τᾱ (cf. voc. sing. ὠ προφῆτα)
Probably hyper rare/inexistent in the corpus and not the case for 2D/3D and the most common masc duals like χεροῖν, χεῖρε.

This yields the following three fully generalizable rules:
    (1) for tokens with tag Acc pl fem (^n.p...fa.$) and lemma ending with η or α, ending -ας is long
    (2) for tokens with tag masc and neutre nouns (^n.....[mn]..$), ending -α is short regardless of case
    (3) for dat (^n......d.$), then ending -ι is short

    
Make a function long_acc_pl_fem(token, tag, lemma): 
if the last two characters of only_bases(token) is ας, tag passes ^n.p...fa.$, and the last character of lemma is η or α,
then let macron = f"_{ordinal_last_vowel(token)}" and return macron

Make a function short_masc_alpha(token, tag):
if the last character of only_bases(token) is α, and tag passes ^n.....[mn]..$,
then let breve = f"^{ordinal_last_vowel(token)}" and return breve

Make a function short_dat(token, tag):
if the last character of only_bases(token) is ι, and tag passes ^n......d.$, 
then let breve = f"^{ordinal_last_vowel(token)}"
'''

import warnings
import grc_odycy_joint_trf # type: ignore
from db.ionic import ionic

from grc_utils import only_bases

warnings.filterwarnings('ignore', category=FutureWarning)

### THE 3 ALGORITHMS RE NOMINAL FORMS
# long_fem_alpha(token, tag, lemma)
# short_masc_neut_alpha(token, tag)
# short_dat(token, tag)

nlp = grc_odycy_joint_trf.load()

def macronize_nominal_forms(word):
    '''
    This function should only be called if ultima or penultima is not yet macronized.
    It is slow and because of its complexity, bug prone.
    A large chunk of its use cases should be covered by the accent-rule method.
    It is primarily useful for *oxytones*.
    '''

    word = word.strip('^').strip('_')
    doc = nlp(word)

    lemma = None
    pos = None
    morph = None

    for token in doc: # makes sure we don't accidentally get several words
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

        if pos != "NOUN":
            return None

    print(f'{word}: {lemma}, {pos}, {morph}')

    def first_declination(word, lemma, morph):
        '''
        Nominal-form algorithms for 1st declension endings.
        '''

        # -α_ for 1D nouns in nominative/vocative singular feminine
        if only_bases(word)[-1:] == "α" and word == lemma and ('Nom' in morph.get("Case") or 'Voc' in morph.get("Case")) and 'Sing' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            etacist_version = word[:-1] + "η"
            if any(etacist_version[:-1] == ionic_word[:-1] and etacist_version[-1] == only_bases(ionic_word[-1]) for ionic_word in ionic):
                print(f'{word}: 1D case 1')
                return word + "_"

        # -α_ν for 1D nouns in accusative singular feminine
        elif only_bases(word)[-2:] == "αν" and 'Acc' in morph.get("Case") and 'Sing' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            if lemma[-1] in ["η", "α"]:
                etacist_lemma = lemma[:-1] + "η"
                if any(etacist_lemma[:-1] == ionic_word[:-1] and etacist_lemma[-1] == only_bases(ionic_word[-1]) for ionic_word in ionic):
                    print(f'{word}: 1D case 2')
                    return word + "_"

        # -α_ς for 1D nouns in genitive singular feminine
        elif only_bases(word)[-2:] == "ας" and 'Gen' in morph.get("Case") and 'Sing' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            print(f'{word}: 1D case 3')
            return word[:-1] + "_" + word[-1]
        
        # -α_ς for 1D nouns in accusative plural feminine
        elif only_bases(word)[-2:] == "ας" and 'Acc' in morph.get("Case") and 'Plur' in morph.get("Number") and 'Fem' in morph.get("Gender"):
            if lemma[-1] in ["η", "α"]:
                print(f'{word}: 1D case 4')
                return word[:-1] + "_" + word[-1]
        
        return None
    
    def masc_and_neutre_short_alpha(word, morph):
        if only_bases(word)[-1:] == "α" and ('Masc' in morph.get("Gender") or 'Neut' in morph.get("Gender")):
            print(f'{word}: Masc/Neut short alpha')
            return word + "^"
        
        return None
    
    def dative_short_iota(word, morph):
        '''
        Note optional ny ephelkystikon!
        '''
        if 'Dat' in morph.get("Case"):  # Check if 'Dat' is in the list
            if only_bases(word)[-1:] == "ι":
                print(f'{word}: Dat short iota')
                return word + "^"
            elif only_bases(word)[-2:] == "ιν":
                print(f'{word}: Dat short iota')
                return word[:-1] + "^" + word[-1]
        return None
    
    # Call the first_declination function
    result = first_declination(word, lemma, morph)
    if result:
        return result
    
    # Call the masc_and_neutre_short_alpha function
    result = masc_and_neutre_short_alpha(word, morph)
    if result:
        return result
    
    # Call the dative_short_iota function
    result = dative_short_iota(word, morph)
    if result:
        return result
    
    return word


#test
input = "κιθάρα"
input = "μάχαιρα"
print(macronize_nominal_forms(input))

input = "γυναιξί" #γυναιξί: γυνή, NOUN, Case=Dat|Gender=Fem|Number=Plur; why is it not returning γυναιξί^?
print(macronize_nominal_forms(input)) # output = input. fuck