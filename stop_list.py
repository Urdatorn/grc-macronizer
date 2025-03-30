'''
List of words that in any genre and period will most likely yield incorrect disambiguations.

Whether to use the stop list or not in a given production situation comes down to whether a wrong disambiguation is worse than a lacking disambiguation.

'''

stop_list = [
    'ἂν' # perhaps THE most notorious dichronon. To disambiguate it, we require knowing whether or not (1) the present clause contains εἰ already (2) the main verb is in the indicative or subjunctive mood.
    'ἄν'
]