'''
ALGORITHMIC MACRONIZING: VERBAL FORMS

The main verbal forms that contain dichrona are:
- μι and νυμι
- thematic aorist
- perfect
- imperfect and imperative 2 & 3p sing of verba contracta on -αω
    - however, only imperative 3p sing (e.g. τιμάτω) is not covered by the σωτῆρα rule

'''
from grc_utils import only_bases

def macronize_verbal_forms(word, lemma, pos, morph, debug=False):
    '''
    Reference: morph.get takes keys and values from: 
    Mood=Imp|Number=Sing|Person=2|Tense=Pres|VerbForm=Fin|Voice=Act
    '''

    if not word or not lemma or not pos or not morph: # TODO: is this necessary?
        return word

    if pos != "VERB":
        if debug:
            print(f"{word} is not VERB but {pos}")
        return word
    
    def mi_verbs(word, lemma, morph):
        # Present active indicative (finite) conjugation of -νυμι (υ long in "Sing" and short in "Plur")
        if only_bases(lemma)[-4:] == "νυμι" and morph.get("Tense") == "Pres" and morph.get("Voice") == "Act" and morph.get("Mood") == "Ind" and morph.get("VerbForm") == "Fin":
            if morph.get("Number") == "Sing":
                # νυ_μι^
                if morph.get("Person") == "1":
                    return word[:-2] + "_" + word[-2:] + "^"
                # νυ_ς
                if morph.get("Person") == "2":
                    return word[:-1] + "_" + word[-1] + "^"
                # νυ_σι^
                if morph.get("Person") == "3" and word[-1] == "ι":
                    return word[:-2] + "_" + word[-2:] + "^"
                # νυ_σι^ν
                if morph.get("Person") == "3" and word[-1] == "ν":
                    return word[:-3] + "_" + word[-3:-1] + "^" + word[-1]
            if morph.get("Number") == "Plur":
                # νυ^μεν
                if morph.get("Person") == "1":
                    return word[:-3] + "^" + word[-3:]
                # νυ^τε
                if morph.get("Person") == "2":
                    return word[:-1] + "_" + word[-1] + "^"
                # νυ^α_σι^
                if morph.get("Person") == "3":
                    return word[:-3] + "^" + word[-3] + "_" + word[-2:] + "^"
                # νυ^α_σι^ν
                if morph.get("Person") == "3":
                    return word[:-4] + "^" + word[-3] + "_" + word[-3:-1] + "^" + word[-1]
        elif only_bases(word)[-2:] == "μι":
            return word + "^"

    result = mi_verbs(word, lemma, morph)
    if result:
        return result

    return word