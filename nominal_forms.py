'''
ALGORITHMIC MACRONIZING PART 2

See page 38 in CGCG for endings of nominal forms.

RULES OF NOMINAL FORMS

#1D
Nom and ac and voc sing can be either, depending on whether or not it comes from ionian -η. Tricky...
Acc pl => long ας; however acc pl fem of 3D are short: so if lemma is clearly 1D, ending is long

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
import grc_odycy_joint_trf

warnings.filterwarnings('ignore', category=FutureWarning)

### THE 3 ALGORITHMS RE NOMINAL FORMS
# long_fem_alpha(token, tag, lemma)
# short_masc_neut_alpha(token, tag)
# short_dat(token, tag)

nlp = grc_odycy_joint_trf.load()

def macronize_nominal_forms(word):
    doc = nlp(word)

    lemma = None
    pos = None
    morph = None

    for token in doc:
        lemma = token.lemma_
        pos = token.pos_
        morph = token.morph

    def long_acc_pl_fem(word, lemma, pos, morph):
        '''
        for nouns in accusative plural feminine and lemma ending with η or α, 
        ending -ας is long.
        E.g. ἐπιθυμίας
        '''
        if pos != "NOUN":
            return None
        
