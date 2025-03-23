from format_macrons import macron_unicode_to_markup

spaCy_cases = {
    "Nom": "Nominative",
    "Acc": "Accusative",
    "Gen": "Genitive",
    "Dat": "Dative",
    "Abl": "Ablative",
    "Loc": "Locative",
    "Voc": "Vocative",
    "Ins": "Instrumental",
    "Part": "Partitive",
    "Ess": "Essive",
    "Trans": "Translative",
    "Com": "Comitative",
}

spaCy_tenses = {
    "Pres": "Present",
    "Past": "Past",
    "Fut": "Future",
    "Imp": "Imperfect",
    "Perf": "Perfect",
    "Plup": "Pluperfect",
}

def morph_disambiguator(word, lemma, pos, morph, token, tense, case_voice, mode, person, number):
    """
    input format:       [[unnormalized tokens with macrons],    [table names], [row headers 1],  row headers 2],  [column header 1],        [column header 2]]
    E.g.:   'ἀσφαλής':  [['ᾰ̓σφᾰλής'],                           ['Table 1'],   ['Nominative'],   [''],            ['Masculine / Feminine'], ['Singular']],
            'ἐαθῶσιν':  [['ἐᾱθῶσῐν'],                           ['Table 10'],  ['passive'],      ['subjunctive'], ['third'],                ['plural']],

    This is hardly more than a placeholder at the moment.
    """
    if morph.get("Tense"):
        tense = morph.get("Tense")[0]

    # Case
    if morph.get("Case"):
        tense = morph.get("Tense")[0]
    for i, case in enumerate(case_voice):
        if spaCy_cases[morph] == case: # let's not nitpick and simply choose the first case that matches
            disambiguated_word = macron_unicode_to_markup(token[i]) 
            return disambiguated_word if disambiguated_word.replace("^", "").replace("_", "") == word # make sure there's no fucking errors entering from ugly wiktionary entries, like missing accents
        
    return word



