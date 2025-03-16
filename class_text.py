'''
i want a new Text method integrate(self) that takes the word list self.macronized_words that contains a list of words form self.text, and for each macronized_word in the list it chronologically searches for the n+1:th text_word such that macronized_word.strip('_').strip('^') == text_word.strip('_').strip('^') (where is is the number of times macronized_word.strip('_').strip('^') has already been searched for; this ensures chronological one-to-one proceedure) , and then substitutes in merge_or_overwrite_markup(macronized_word, text_word) for text.word. at the end, the resulting new text is saved as self.macronized_text. Note (1): every search is expected to go through; if a single does not, raise error. Note (2): at the very end we need to assert that self.text == self.macronized_text to make sure nothing got corrupted and no changes except carets and underscores were undergone
'''

from concurrent.futures import ProcessPoolExecutor
import os
from tqdm import tqdm
import xxhash
import warnings
import re
warnings.filterwarnings('ignore', category=FutureWarning)

from tests.anabasis import anabasis
from nominal_forms import macronize_nominal_forms
from format_macrons import merge_or_overwrite_markup
from grc_utils import normalize_word, make_only_greek

from spacy.tokens import DocBin
import grc_odycy_joint_trf # type: ignore

def process_text(text):
    """Each worker loads its own spaCy model to avoid serialization issues."""
    nlp = grc_odycy_joint_trf.load()
    return nlp(text)



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
    def __init__(self, text, doc_from_file=True):

        before_odycy = text.strip('^').strip('_') # first remove previous markup if doing a "second run"
        sentence_list = before_odycy.split('.') # then split the input into sentences, to enable using spaCy pipe batch processing and tqdm
        print(f'Split input into {len(sentence_list)} sentences.')

        # odyCy tokenization
        hash_value = xxhash.xxh3_64_hexdigest("text")
        output_file_name = f"odycy_docs/{"-".join(sentence_list[0].split()[i] for i in (0, 1)) + '-' + hash_value}.spacy"
        docs = []
        if doc_from_file and os.path.exists(output_file_name):
            doc_bin = DocBin().from_disk(output_file_name)
            nlp = grc_odycy_joint_trf.load()
            docs = list(doc_bin.get_docs(nlp.vocab))
        else:
            #docs = list(tqdm(nlp.pipe(sentence_list), total=len(sentence_list)))
            # Use multiprocessing
            with ProcessPoolExecutor() as executor:
                docs = list(tqdm(executor.map(process_text, sentence_list), total=len(sentence_list)))

            doc_bin = DocBin()
            for doc in docs:
                doc_bin.add(doc)
            print(f"Saving odyCy doc bin to disc as {output_file_name}")
            doc_bin.to_disk(output_file_name)

        
        macronized_nominal_forms = [] # this will store all the words of all sentences, in the right order. this list will form the basis for the list in the macronize_text method of the Macronizer class
        for doc in docs: # don't worry, pipe() returns docs in the right order
            for token in doc:
                if token.orth_ and token.lemma_ and token.pos_ and token.morph:
                    macronized_nominal_forms.append(macronize_nominal_forms(token.orth_, token.lemma_, token.pos_, token.morph, debug=False))

        self.text = text
        self.docs = docs
        self.macronized_nominal_forms = macronized_nominal_forms
        self.macronized_words = macronized_nominal_forms # for now; this will contain the results of merging macronized_nominal_forms with the results of all other macronization methods
        self.macronized_text = ''
    
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
        
        # Keep track of how many times each normalized word has been processed
        word_counts = {}
        
        # Process each macronized word in order
        for macronized_word in tqdm(macronized_words, desc="Integrating macronized words"):
                
            # Normalize the macronized word (remove macrons)
            macronized_word = macronized_word.replace('_', '').replace('^', '')
            macronized_word = normalize_word(macronized_word)
            macronized_word = make_only_greek(macronized_word)
            
            # Get the current count for this normalized word (default to 0 if not seen before)
            current_count = word_counts.get(macronized_word, 0)
            
            # Split the text into 3 parts: before the word, the word itself, and after the word
            parts = result_text.replace('_', '').replace('^', '').split(macronized_word)
            
            # If we can't find the word or we don't have enough occurrences, raise an error
            if len(parts) <= current_count + 1:
                raise ValueError(f"Could not find occurrence {current_count + 1} of word '{macronized_word}' in the text.")
            
            # Reconstruct the text with the macronized word in the correct position
            result = parts[0]
            for i in range(1, len(parts)):
                if i - 1 == current_count:
                    # Find the original word in the text (with any existing macrons)
                    start_idx = len(result)
                    end_idx = start_idx + len(macronized_word)
                    original_word = result_text[start_idx:end_idx]
                    
                    # Merge the macronized word with the original word
                    merged_word = merge_or_overwrite_markup(macronized_word, original_word)
                    result += merged_word
                else:
                    result += macronized_word
                result += parts[i]
            
            # Update the result text
            result_text = result
            
            # Increment the count for this normalized word
            word_counts[macronized_word] = current_count + 1
        
        # Save the result
        self.macronized_text = result_text
        
        # Verify that only macrons have been changed
        original_macronized = self.text.replace('_', '').replace('^', '')
        result_macronized = self.macronized_text.replace('_', '').replace('^', '')
        
        if original_macronized != result_macronized:
            print("Original macronized:", repr(original_macronized[:100]), "...")
            print("Result macronized:", repr(result_macronized[:100]), "...")
            
            # Find the first difference
            for i, (orig_char, result_char) in enumerate(zip(original_macronized, result_macronized)):
                if orig_char != result_char:
                    print(f"First difference at position {i}: '{orig_char}' vs '{result_char}'")
                    print(f"Context: '{original_macronized[max(0, i-10):i+10]}' vs '{result_macronized[max(0, i-10):i+10]}'")
                    break
            
            if len(original_macronized) != len(result_macronized):
                print(f"Length difference: original={len(original_macronized)}, result={len(result_macronized)}")
            
            raise ValueError("Integration corrupted the text: changes other than macrons were made.")
        
        return self.macronized_text


if __name__ == "__main__":
    input = "ἔχω κιθάρας ἀγαθάς. νεανίας δ' εἰμὶ ἀάατος ὕδατι."
    #input = anabasis
    text = Text(input, doc_from_file=False)
    print(text.macronized_nominal_forms)
    
    # Test the integrate method
    text.macronized_text = text.integrate()
    print("Macronized text:", text.macronized_text)