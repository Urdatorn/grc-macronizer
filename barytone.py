'''
Barytones inherit their macra from oxytones

'''
import re
from grc_utils import acutes, graves, only_bases, syllabifier, ultima


def barytone(token):
    if re.search(graves, token):
        return True
    return False


def replace_grave_with_acute(token):
    '''
    >>> replace_grave_with_acute('ἱεὶς')
    >>> ἱείς
    '''
    def replace(match):
        char = match.group(0)
        pos = graves.index(char)
        return acutes[pos]
    
    return re.sub(graves, replace, token)
