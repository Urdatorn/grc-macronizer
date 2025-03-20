'''
i want a new Text method integrate(self) that takes the word list self.macronized_words that contains a list of words form self.text, and for each macronized_word in the list it chronologically searches for the n+1:th text_word such that macronized_word.strip('_').strip('^') == text_word.strip('_').strip('^') (where is is the number of times macronized_word.strip('_').strip('^') has already been searched for; this ensures chronological one-to-one proceedure) , and then substitutes in merge_or_overwrite_markup(macronized_word, text_word) for text.word. at the end, the resulting new text is saved as self.macronized_text. Note (1): every search is expected to go through; if a single does not, raise error. Note (2): at the very end we need to assert that self.text == self.macronized_text to make sure nothing got corrupted and no changes except carets and underscores were undergone
'''

import os
from tqdm import tqdm
import xxhash
import warnings
import re
warnings.filterwarnings('ignore', category=FutureWarning)

from epic_stop_words import epic_stop_words
from tests.anabasis import anabasis
from nominal_forms import macronize_nominal_forms
from format_macrons import merge_or_overwrite_markup
from grc_utils import normalize_word, make_only_greek

from spacy.tokens import DocBin
import grc_odycy_joint_trf # type: ignore

class Text:
    '''
    Container for text and metadata during macronization.
    Firstly, it stores the odyCy tokenization metadata so it can be used with the nominal_forms method.
    Secondly, it stores the list of words to be macronized, together with their odyCy tokenization metadata.
    Thirdly, it stores the macronized text.

    Essentially, this means that we trust odyCy to create the tokens list, instead of creating it ourselves in the Macronizer class as before.
    This is a necessary step towards a more modular design, where the Text class is responsible for the text and its metadata, and the Macronizer class is responsible for the macronization.

    NB: The user shouldn't have to deal with this class; it is to be used *internally* by the interfacing Macronizer class.
    '''
    def __init__(self, text, genre='prose', doc_from_file=True, debug=False):

        to_remove = {'^', '_', '<', '>', '[', ']', '«', '»', '†'}
        translation_table = str.maketrans("", "", "".join(to_remove))
        before_odycy = text.translate(translation_table)

        sentence_list = [sentence for sentence in re.findall(r'[^.]+\.?', before_odycy) if sentence] # then split the input into sentences, to enable using spaCy pipe batch processing and tqdm
        if debug:
            print(f'Split input into {len(sentence_list)} sentences.')
            for i, sentence in enumerate(sentence_list):
                print(f"{i}: {sentence}")

        # odyCy tokenization
        hash_value = xxhash.xxh3_64_hexdigest(before_odycy)
        if debug:
            print(f"Hash value: {hash_value}")
        output_file_name = f"odycy_docs/{"-".join(sentence_list[0].split()[i] for i in (0, 1)) + '-' + hash_value}.spacy"
        docs = []
        if doc_from_file and os.path.exists(output_file_name):
            doc_bin = DocBin().from_disk(output_file_name)
            nlp = grc_odycy_joint_trf.load()
            docs = list(doc_bin.get_docs(nlp.vocab))
        else:
            nlp = grc_odycy_joint_trf.load()
            docs = list(tqdm(nlp.pipe(sentence_list), total=len(sentence_list)))
            doc_bin = DocBin()
            for doc in docs:
                doc_bin.add(doc)
            print(f"Saving odyCy doc bin to disc as {output_file_name}")
            doc_bin.to_disk(output_file_name)

        token_lemma_pos_morph = []
        macronized_nominal_forms = [] # this will store all the words of all sentences, in the right order. this list will form the basis for the list in the macronize_text method of the Macronizer class
        for doc in docs: # don't worry, pipe() returns docs in the right order
            for token in doc:
                if token.orth_ and token.lemma_ and token.pos_ and token.morph:
                    orth = token.orth_.replace('\u0387', '').replace('\u037e', '') # remove ano teleia and Greek question mark
                    if genre == 'epic':
                        if orth in epic_stop_words:
                            continue
                    token_lemma_pos_morph.append([orth, token.lemma_, token.pos_, token.morph])
                    macronized_nominal_forms.append(macronize_nominal_forms(orth, token.lemma_, token.pos_, token.morph, debug=False))

        self.text = text
        self.genre = genre
        self.docs = docs
        self.token_lemma_pos_morph = token_lemma_pos_morph
        self.macronized_nominal_forms = macronized_nominal_forms
        self.macronized_words = [] # for now; this will contain the results of merging macronized_nominal_forms with the results of all other macronization methods
        for sublist, macronized_nominal_form in zip(token_lemma_pos_morph, macronized_nominal_forms):
            token = sublist[0]
            merge = merge_or_overwrite_markup(token, macronized_nominal_form)
            self.macronized_words.append(merge)
        self.macronized_text = ''
        self.debug = debug

    def integrate(self):
        """
        Integrates the macronized words back into the original text.
        
        For each macronized word in self.macronized_words, it chronologically searches for the n+1:th
        occurrence of the corresponding word in the original text (where n is the number of times
        this word has already been processed). It then substitutes a new 
        merged version (of the macronized word and the original word) for the original word.
        
        Raises:
            ValueError: If a macronized word cannot be found in the original text.
        """
        result_text = self.text
        macronized_words = [word for word in self.macronized_words if word is not None and any(macron in word for macron in ['_', '^'])]
        
        word_counts = {}
        
        # Build a list of all replacements we need to make
        replacements = []
        
        for macronized_word in tqdm(macronized_words, desc="Finding replacements"):
            normalized_word = normalize_word(macronized_word.replace('_', '').replace('^', ''))
            #normalized_word = make_only_greek(normalized_word)
            
            if not normalized_word:
                continue
            
            current_count = word_counts.get(normalized_word, 0)  # default to 0
            
            if self.debug:
                print(f"Processing: {macronized_word} (Current count: {current_count})")
            
            # Find all matches in the original text
            matches = list(re.finditer(fr"\b{normalized_word}\b", self.text))
            
            if current_count >= len(matches):
                raise ValueError(f"Could not find occurrence {current_count + 1} of word '{normalized_word}'")
                
            # Get the position and length of the target occurrence
            target_match = matches[current_count]
            start_pos = target_match.start()
            end_pos = target_match.end()
            
            # Store the replacement information
            replacements.append((start_pos, end_pos, macronized_word))
            
            word_counts[normalized_word] = current_count + 1
        
        # Sort replacements by position (to apply them from end to beginning)
        replacements.sort(reverse=True, key=lambda x: x[0])
        
        # Apply all replacements (from end to beginning to avoid position shifts)
        for start_pos, end_pos, replacement in tqdm(replacements, desc="Applying replacements"):
            result_text = result_text[:start_pos] + replacement + result_text[end_pos:]
            
        self.macronized_text = result_text
        
        # Verify that only macrons have been changed
        original_no_macrons = self.text.replace('_', '').replace('^', '')
        result_no_macrons = self.macronized_text.replace('_', '').replace('^', '')
        
        if original_no_macrons != result_no_macrons:
            print("Original (no macrons):", repr(original_no_macrons[:100]), "...")
            print("Result (no macrons):", repr(result_no_macrons[:100]), "...")
            
            # Find the first difference
            for i, (orig_char, result_char) in enumerate(zip(original_no_macrons, result_no_macrons)):
                if orig_char != result_char:
                    print(f"First difference at position {i}: '{orig_char}' vs '{result_char}'")
                    print(f"Context: '{original_no_macrons[max(0, i-10):i+10]}' vs '{result_no_macrons[max(0, i-10):i+10]}'")
                    break
            
            if len(original_no_macrons) != len(result_no_macrons):
                print(f"Length difference: original={len(original_no_macrons)}, result={len(result_no_macrons)}")
            
            raise ValueError("Integration corrupted the text: changes other than macrons were made.")
        
        return self.macronized_text


if __name__ == "__main__":
    input = "ἔχω κιθάρας ἀγαθάς. νεανίας δ' εἰμὶ ἀάατος. κιθάρας ἀγαθάς ἔχω."
    input = anabasis
    text = Text(input, doc_from_file=True, debug=True)
    #print(text.macronized_nominal_forms)
    
    # Test the integrate method
    text.macronized_text = text.integrate()
    #print("Macronized text:", text.macronized_text)
    length_of_docs = 0
    for doc in text.docs:
        for token in doc:
            length_of_docs += 1

    print(f'Len of docs: {length_of_docs}')
    print(f'Len of macronized_words: {len(text.macronized_words)}')