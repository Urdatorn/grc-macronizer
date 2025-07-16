import logging
from pathlib import Path
import re
from tqdm import tqdm
import warnings

import grc_odycy_joint_trf
from spacy.tokens import DocBin
import xxhash

from grc_utils import ACCENTS, ACUTES, count_dichrona_in_open_syllables, GRAVES, is_greek_numeral, lower_grc, normalize_word, ROUGHS, syllabifier

from .stop_list import stop_list
from .stop_list_epic import epic_stop_words

warnings.filterwarnings('ignore', category=FutureWarning)

greek_ano_teleia = "\u0387"
greek_question_mark = "\u037e"
middle_dot = "\u00b7"
apostrophes = "'’‘´΄\u02bc͵" # the last one is for thousands

def word_list(text):
    greek_punctuation = r'[\u0387\u037e\u00b7\.,!?;:\"()\[\]{}<>«»\-—…|⏑⏓†×]' # NOTE hyphens must be escaped (AI usually misses this)
    
    cleaned_text = re.sub(greek_punctuation, ' ', text)

    word_list = [word for word in cleaned_text.split() if word]
    
    logging.debug(f"Diagnostic word list: {word_list}")

    return word_list

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

    def __init__(self, text, genre='prose', doc_from_file=True, custom_doc="", debug=False, lowercase=False):
        
        # -- Prepare the text for odyCy --

        ### Clean non-Greek characters and punctuation

        chars_to_clean = r'[\^_()\[\]{}<>\"«»\-—…|⏑⏓†×]' # pipes actually appear in OGA

        before_odycy = text
        before_odycy = re.sub(chars_to_clean, '', before_odycy)

        ### Normalize

        before_odycy = normalize_word(before_odycy)

        ### Lower the case

        if lowercase:
            before_odycy = lower_grc(before_odycy)

        ### Normalize elisions

        before_odycy = before_odycy.replace('’', "'") # odyCy only understands apostrophe \u0027. Right single quote \u2019 => apostrophe \u0027
        before_odycy = before_odycy.replace('‘', "'")
        before_odycy = before_odycy.replace('\u02bc', "'") # "Modifier letter apostrophe"
        before_odycy = before_odycy.replace('´', "'") # "Acute accent"
        before_odycy = before_odycy.replace('΄', "'") # "Greek tonos"
        
        ### Preëmptive macronization of a few straightforward words that odyCy doesn't handle well

        before_odycy = re.sub(r'\sτἄλλα\s', 'τἄλλα^', before_odycy)
        before_odycy = re.sub(r'\sἁ\s', 'ἁ_', before_odycy)

        ### Create diagnostic word list

        if debug: 
            logging.debug(f"Text before odyCy but after clean-up: {before_odycy}")

        diagnostic_word_list = word_list(before_odycy) # this list serves as a standard for what constitutes a word in the present text

        ### Create sentence list

        sentence_list = [sentence for sentence in re.findall(r'[^.\n;\u037e]+[.\n;\u037e]?', before_odycy) if sentence and count_dichrona_in_open_syllables(sentence) > 0] # then split the input into sentences, to enable using spaCy pipe batch processing and tqdm
        
        logging.debug(f'Split input into {len(sentence_list)} sentences.')
        for i, sentence in enumerate(sentence_list):
            logging.debug(f"{i}: {sentence}")

        # -- odyCy tokenization and docbin saving --

        hash_value = xxhash.xxh3_64_hexdigest(before_odycy)
        if debug:
            logging.debug(f"Hash value: {hash_value}")
        
        project_root = Path(__file__).resolve().parents[2] # NOTE to self: pathlib for writing outside the src directory, importlib for reading inside (e.g. checking a pickled db)
        odycy_docs_dir = project_root / "odycy_docs"
        odycy_docs_dir.mkdir(parents=True, exist_ok=True)

        # Handle empty sentence_list case
        if not sentence_list:
            filename = f"empty-text-{hash_value}.spacy"
        elif len(sentence_list[0].split()) > 1:
            filename = f"{'-'.join(sentence_list[0].split()[i] for i in (0, 1))}-{hash_value}.spacy"
        else:
            filename = f"{sentence_list[0].split()[0]}-{hash_value}.spacy"

        output_file_name = odycy_docs_dir / filename

        docs = []
        if custom_doc != "":
            doc_bin = DocBin().from_disk(custom_doc)
            nlp = grc_odycy_joint_trf.load()
            docs = list(doc_bin.get_docs(nlp.vocab))
        elif doc_from_file and output_file_name.exists():  # pathlib-style check
            doc_bin = DocBin().from_disk(output_file_name)
            nlp = grc_odycy_joint_trf.load()
            docs = list(doc_bin.get_docs(nlp.vocab))
        else:
            nlp = grc_odycy_joint_trf.load()
            if sentence_list:  # Only process if we have sentences
                docs = list(tqdm(nlp.pipe(sentence_list), total=len(sentence_list), leave=False, desc="odyCy pipeline"))
                doc_bin = DocBin()
                for doc in docs:
                    doc_bin.add(doc)
                logging.info(f"Saving odyCy doc bin to disc as {output_file_name}")
                doc_bin.to_disk(output_file_name)
            else:
                docs = []  # Empty docs list for empty input
        
        #
        # -- Preparing the master list of words to be macronized (and handling ἄν) -- (NOTE often THE key step in analyzing nonplussing bugs)
        #

        an_list = []
        fail_counter = 0
        buggy_words_in_input = 0
        token_lemma_pos_morph = []
        for doc in tqdm(docs, desc="Extracting words to macronize from the odyCy docs", leave=False): # don't worry, pipe() returns docs in the right order
            for token in doc:
                logging.debug(f"Considering token: {token.text}\tLemma: {token.lemma_}\tPOS: {token.pos_}\tMorph: {token.morph}")
                if token.text == 'ἂν' or token.text == 'ἄν':
                    an = token.text
                    subjunctive_verb = False
                    no_ei = True
                    logging.debug(f"\t\tPROCESSING ἂν/ἄν: {token.text}")
                    for inner_token in doc:
                        if 'Sub' in inner_token.morph.get('Mood'):
                            subjunctive_verb = True
                        if inner_token.text == 'εἰ' or inner_token.text == 'εἴ':
                            no_ei = False
                            logging.debug(f"\t\tEi found: {inner_token.text}")
                    if subjunctive_verb and no_ei:
                        an_list.append(an[0] + '_' + an[1])
                        logging.debug(f"\t\tLong ἂν macronized")
                    else: 
                        an_list.append(an[0] + '^' + an[1])
                        logging.debug(f"\t\tShort ἂν macronized")

                if token.text and token.pos_: # NOTE: .morph is empty for some tokens, such as prepositions like ἀπό, whence it is imperative not to filter out empty morphs. Some words have empty lemma too.
                    orth = token.text.replace('\u0387', '').replace('\u037e', '') # remove ano teleia and Greek question mark
                    logging.debug(f"\t'Token text: {orth}")
                    
                    # MAJOR FILTER FOR TOKENS NOT TO MACRONIZE

                    # 1 Numerals
                    if is_greek_numeral(orth):
                        logging.debug(f"\033Word '{orth}' is a Greek numeral. Skipping with 'continue'.")
                        continue

                    # 2 Stop words
                    if orth in stop_list:
                        logging.info(f"\033General stop word '{orth}' found. Skipping with 'continue'.")
                        continue
                    if genre == 'epic' and orth in epic_stop_words:
                        logging.info(f"\033Epic stop word '{orth}' found. Skipping with 'continue'.")
                        continue
                    
                    # 3 Formatting/OCR errors
                    if 'ς' in list(orth[:-1]):
                        logging.debug(f"\033Word '{orth}' contains a final sigma mid-word. Skipping with 'continue'.")
                        buggy_words_in_input += 1
                        continue
                    if sum(char in GRAVES for char in orth) > 1 or (any(char in GRAVES for char in orth) and any(char in ACUTES for char in orth)) or sum(char in ACCENTS for char in orth) > 2 or sum(char in ROUGHS for char in orth) > 2:
                        logging.debug(f"Pathological word '{orth}' contains more than one grave accent or both acute and grave or more than two accents or more than one spiritus. Skipping with 'continue'.")
                        buggy_words_in_input += 1
                        continue
                    if orth not in diagnostic_word_list and orth != 'ἂν' and orth != 'ἄν':
                        fail_counter += 1
                        logging.debug(f"\033Word '{orth}' not in diagnostic word list. odyCy messed up here. Skipping with 'continue'.")
                        continue

                    # For speed, let's not bother even sending words without dichrona to the macronizer
                    if count_dichrona_in_open_syllables(orth) == 0 and orth not in ['ἂν_', 'ἂν^', 'ἄν_', 'ἄν^']:
                        logging.debug(f"\033Word '{orth}' has no dichrona. Skipping with 'continue'.")
                        continue
                    if token.text == 'ἂν' or token.text == 'ἄν':
                        macronized_an = an_list.pop(0)
                        token_lemma_pos_morph.append([macronized_an, token.lemma_, token.pos_, token.morph])
                        logging.debug(f"\033Popping an {macronized_an}! {len(an_list)} left to pop")
                    else:
                        token_lemma_pos_morph.append([orth, token.lemma_, token.pos_, token.morph])
                    logging.debug(f"\tAppended: \tToken: {token.text}\tLemma: {token.lemma_}\tPOS: {token.pos_}\tMorph: {token.morph}")

        assert an_list == [], f"An list is not empty: {an_list}. This means that the ἂν macronization step failed. Please check the code."
        logging.debug(f'Len of token_lemma_pos_morph: {len(token_lemma_pos_morph)}')
        if len(token_lemma_pos_morph) == 1:
            logging.debug(f'Only element of token_lemma_pos_morph: {token_lemma_pos_morph[0]}')
        if len(token_lemma_pos_morph) > 1:
            logging.debug(f'First elements of token_lemma_pos_morph: {token_lemma_pos_morph[0]}, {token_lemma_pos_morph[1]}...')
        logging.info(f'odyCy fail count: {fail_counter}')

        self.text = before_odycy # important: this is the cleaned text, without [, ], etc. If we try to integrate into the original text, we will get a lot of silent bugs or errors.
        self.genre = genre
        self.docs = docs
        self.token_lemma_pos_morph = token_lemma_pos_morph
        self.macronized_words = [] # populated by class_macronizer
        self.macronized_text = ''
        self.debug = debug

    def integrate(self):
        """
        Integrates the macronized words back into the original text.
        """
        result_text = self.text # making a working copy
        macronized_words = [word for word in self.macronized_words if word is not None and any(macron in word for macron in ['_', '^'])]
        
        word_counts = {}
        
        replacements = [] # going to be a list of triples: (starting position, ending position, macronized word)
        
        for macronized_word in tqdm(macronized_words, desc="Finding replacements", leave=False):
            normalized_word = normalize_word(macronized_word.replace('_', '').replace('^', ''))
            
            if not normalized_word:
                continue
            
            current_count = word_counts.get(normalized_word, 0)  # how many times have we seen the present word before? default to 0
            
            if self.debug:
                logging.debug(f"Processing: {macronized_word} (Current count: {current_count})")
            
            '''
            NOTE re the regex: \b does not work for strings containing apostrophe!
            Hence we use negative lookbehind (?<!) and lookahead groups (?!) with explicit w to match word boundaries instead.
            '''
            matches = list(re.finditer(fr"(?<!\w){normalized_word}(?!\w)", self.text))
            matches = [m for m in matches if (m.group() != "ἂν" or m.group() != "ἄν" or m.group() != "ἀν")] # remove ἂν and ἄν from the list of matches, since they are already macronized

            if current_count >= len(matches):
                logging.debug(f"Current count: {current_count}, Matches: {matches}")
                print(f"Could not find occurrence {current_count + 1} of word '{normalized_word}'")
                continue
                #raise ValueError(f"Could not find occurrence {current_count + 1} of word '{normalized_word}'")
            
            target_match = matches[current_count]
            # .start() and .end() are methods of a regex Match object, giving the start and end indices of the match
            # NOTE TO SELF TO REMEMBER: .start() is inclusive, while .end() is *exclusive*, meaning .end() returns the index of the first character *just after* the match
            start_pos = target_match.start()
            end_pos = target_match.end()
            
            replacements.append((start_pos, end_pos, macronized_word))
            
            word_counts[normalized_word] = current_count + 1
        
        # NOTE USEFUL NLP TRICK: Reversing the replacements list. This is because when a ^ or _ is added to a word, the positions of all subsequent words change, but those of all previous words remain the same.
        replacements.sort(reverse=True, key=lambda x: x[0]) # the lambda means sorting by start_pos *only*: ties are left in their original order. I don't think this is necessary, because there shouldn't be two words with the identical start_pos.
        
        for start_pos, end_pos, replacement in tqdm(replacements, desc="Applying replacements", leave=False):
            result_text = result_text[:start_pos] + replacement + result_text[end_pos:] # remember, slicing (:) means "from and including" the start index and "up to but not including" the end index, so this line only works because .end() is exclusive, as noted above!
        
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
            
            print("Integration corrupted the text: changes other than macrons were made.")
            logging.debug("Integration corrupted the text: changes other than macrons were made.")
        
        return self.macronized_text
