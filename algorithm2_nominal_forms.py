# '''
# ALGORITHMIC MACRONIZING PART 2

# See page 38 in CGCG for endings of nominal forms.

# RULES OF NOMINAL FORMS

# #1D
# Nom and ac and voc sing can be either, depending on whether or not it comes from ionian -η. Tricky...
# Acc pl => long ας; however acc pl fem of 3D are short: so if lemma is clearly 1D, ending is long

# #2D
# Nom and acc pl (neut): => short α (the only dichronon; Same as neuter pl 3D.)

# #3D
# Dat sing: short ι (all datives on iota are short)
# Acc sing (masc) => short α
# Nom and acc pl (neut) => short α, i.e. if noun is masc or neut and ends on -α, that α is short***
# Dat pl: short ι; see dat sing.
# Acc pl (masc) => short α. Cf. 1D acc pl.

# ***NB: Note that some *dual* forms (1D on -ης) can be masculine on long -α, e.g. τὼ προφήτᾱ, ὁπλῑ́τᾱ (cf. voc. sing. ὠ προφῆτα)
# Probably hyper rare/inexistent in the corpus and not the case for 2D/3D and the most common masc duals like χεροῖν, χεῖρε.

# This yields the following three fully generalizable rules:
#     (1) for tokens with tag Acc pl fem (^n.p...fa.$) and lemma ending with η or α, ending -ας is long
#     (2) for tokens with tag masc and neutre nouns (^n.....[mn]..$), ending -α is short regardless of case
#     (3) for dat (^n......d.$), then ending -ι is short

    
# Make a function long_acc_pl_fem(token, tag, lemma): 
# if the last two characters of only_bases(token) is ας, tag passes ^n.p...fa.$, and the last character of lemma is η or α,
# then let macron = f"_{ordinal_last_vowel(token)}" and return macron

# Make a function short_masc_alpha(token, tag):
# if the last character of only_bases(token) is α, and tag passes ^n.....[mn]..$,
# then let breve = f"^{ordinal_last_vowel(token)}" and return breve

# Make a function short_dat(token, tag):
# if the last character of only_bases(token) is ι, and tag passes ^n......d.$, 
# then let breve = f"^{ordinal_last_vowel(token)}"

# May 8:
# Total forms updated by long_fem_alpha: 152
# Total forms updated by short_masc_neut_alpha: 98
# Total forms updated by short_dat: 82

# '''

# import re
# import csv
# import unicodedata

# from grc_utils import Colors, DICHRONA, only_bases, all_vowels, is_diphthong, has_iota_adscriptum, ordinal_last_vowel


# ### ALGORITHMS RE NOMINAL FORMS
# # long_fem_alpha(token, tag, lemma)
# # short_masc_neut_alpha(token, tag)
# # short_dat(token, tag)

# def long_fem_alpha(token, tag, lemma):
#     tag_pattern_acc = re.compile(r'^[na].p...fa.$')
#     tag_pattern_gen = re.compile(r'^[na].s...fg.$')
    
#     base_token = only_bases(token)
#     base_lemma = only_bases(lemma)
#     endings = ('η', 'α', 'ος') # 'ος' is to allow fem adj of 2D
    
#     if base_token.endswith('ας') and (tag_pattern_acc.match(tag) or tag_pattern_gen.match(tag)) and base_lemma.endswith(endings):
#         macron = f"_{ordinal_last_vowel(token)}"
#         return macron
    
#     return None

# print(long_fem_alpha('ὁπλίτας', 'n-p---ma-', 'ὁπλίτης'))
# print(long_fem_alpha('οὐρείας', 'a-p---fa-', 'οὐρεῖος'))
# print(long_fem_alpha('παιδείας', 'n-s---fg-', 'παιδεία'))
# print(long_fem_alpha('παιδείας', 'n-p---fa-', 'παιδεία'))


# def short_masc_neut_alpha(token, tag):
#     tag_pattern = re.compile(r'^n.....[mn]..$')

#     base_form = only_bases(token)

#     if base_form.endswith('α') and tag_pattern.match(tag):
#         last_vowel_position = ordinal_last_vowel(token)
#         breve = f"^{last_vowel_position}"
#         return breve

#     return None

# print(f"Short neut alpha: {short_masc_neut_alpha('ἀγάλματα', 'n-p---na-')}")

# def short_dat(token, tag):
#     '''
#     Avoiding brevizing the iota of e.g. ἁβροσύνηι
#     '''
#     tag_pattern = re.compile(r'^n......d.$')
#     base_form = only_bases(token)

#     if base_form.endswith('ι') and tag_pattern.match(tag):
#         # Find the position of the last vowel
#         last_vowel_position = ordinal_last_vowel(base_form)

#         # Check if the last 'ι' is part of a diphthong or has adscriptum
#         last_iota_index = base_form.rfind('ι')
#         prev_pair = base_form[last_iota_index - 1: last_iota_index + 1] if last_iota_index > 0 else ''
#         next_pair = base_form[last_iota_index: last_iota_index + 2] if last_iota_index < len(base_form) - 1 else ''

#         if not (is_diphthong(prev_pair) or is_diphthong(next_pair) or has_iota_adscriptum(prev_pair) or has_iota_adscriptum(next_pair)):
#             breve = f"^{last_vowel_position}"
#             return breve

#     return None

# print(f"Short dat iota: {short_dat('ἀγάλμασι', 'n-p---nd-')}")


# ### MACRONIZE


# def macronize_nominal_forms_in_tsv(input_tsv, output_tsv):
#     # Counters for each macronizing function
#     long_fem_alpha_count = 0
#     short_masc_neut_alpha_count = 0
#     short_dat_count = 0

#     first_line = True  # Flag to identify the header

#     with open(input_tsv, mode='r', encoding='utf-8', newline='') as infile, \
#          open(output_tsv, mode='w', encoding='utf-8', newline='') as outfile:
#         reader = csv.reader(infile, delimiter='\t')
#         writer = csv.writer(outfile, delimiter='\t')

#         for row in reader:
#             if first_line:
#                 # Write the header unchanged
#                 writer.writerow(row)
#                 first_line = False
#                 continue

#             if row and len(row) >= 4:
#                 token_in, tag_in, lemma_in, macron_in = row[:4]
#                 source_in = row[4] if len(row) > 4 else ''

#                 normalized_token = unicodedata.normalize('NFC', token_in)
#                 original_macron = macron_in

#                 # Apply the long_fem_alpha function
#                 new_macron = long_fem_alpha(normalized_token, tag_in, lemma_in)
#                 if new_macron:
#                     macron_in = collate_macrons(macron_in, new_macron)
#                     if macron_in != original_macron:
#                         long_fem_alpha_count += 1

#                 # Apply the short_masc_neut_alpha function
#                 new_macron = short_masc_neut_alpha(normalized_token, tag_in)
#                 if new_macron:
#                     macron_in = collate_macrons(macron_in, new_macron)
#                     if macron_in != original_macron:
#                         short_masc_neut_alpha_count += 1

#                 # Apply the short_dat function
#                 new_macron = short_dat(normalized_token, tag_in)
#                 if new_macron:
#                     macron_in = collate_macrons(macron_in, new_macron)
#                     if macron_in != original_macron:
#                         short_dat_count += 1

#                 # Update the source field only if the macron value changed
#                 if macron_in != original_macron:
#                     source_out = f"{source_in},nominal" if source_in else "nominal"
#                 else:
#                     source_out = source_in

#                 # Write the updated row to the output TSV
#                 output_row = [token_in, tag_in, lemma_in, macron_in, source_out]
#                 writer.writerow(output_row)

#     # Print statistics about how many updates were made by each function
#     print(f"{Colors.GREEN}Total forms updated by long_fem_alpha: {long_fem_alpha_count}{Colors.ENDC}")
#     print(f"{Colors.BLUE}Total forms updated by short_masc_neut_alpha: {short_masc_neut_alpha_count}{Colors.ENDC}")
#     print(f"{Colors.MAGENTA}Total forms updated by short_dat: {short_dat_count}{Colors.ENDC}")


# if __name__ == '__main__':
#     input_tsv = 'macrons_alg1_ultima.tsv'
#     output_tsv = 'macrons_alg2_nominal.tsv'
#     macronize_nominal_forms_in_tsv(input_tsv, output_tsv)