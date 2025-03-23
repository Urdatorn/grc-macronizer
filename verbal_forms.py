'''
ALGORITHMIC MACRONIZING: VERBAL FORMS

'''
from grc_utils import only_bases

def macronize_verbal_forms(word, lemma, pos, morph, debug=False):
    '''
    '''

    if not word or not lemma or not pos or not morph: # TODO: is this necessary?
        return word

    if pos != "VERB":
        if debug:
            print(f"{word} is not VERB but {pos}")
        return word
    
    def vumi(word, lemma):
        if only_bases(word)[-2:] == "μι":
            return word + "^"

    result = vumi(word, lemma)
    if result:
        return result

    return word