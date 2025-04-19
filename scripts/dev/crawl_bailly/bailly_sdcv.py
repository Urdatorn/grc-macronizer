'''I want a script that for every entry in the tuple bailly_keys imported from bailly_keys.py runs the shell command 'sdcv -n -j "entry"', which outputs a json, e.g.

[22:28:37] ~/git/macronize-tlg% sdcv -n -j χειρίσοφος    
[{"dict": "Dictionnaire grec-français, Bailly (2020)","word":"χειρίσοφος","definition":"\n<b>Χειρί·σοφος, ου (ὁ)</b> <font color=\"brown\">[ῐ]</font> Kheirisophos, <i>général de Cyrus le Jeune,</i> XÉN. <i>An. 1, 4, 3, etc</i>.<p style=\"color:darkblue\"><b>Étym</b>. χείρ, σοφός."}]

I then want to parse the json for the first string inside square parentheses, e.g. [ῐ].
If there is such a string, that string e.g. ῐ, should be added to a dictionary as the value to the entry in the tuple bailly_keys.
Finally the dict should be written to a python file, one key-value pair per line.'''

import json
import re
import subprocess
from tqdm import tqdm

from crawl_bailly.bailly_keys import bailly_keys

def extract_brackets(s):
    match = re.search(r"\[([^]]+)\]", s)
    return match.group(1) if match else None

def main():
    bracket_dict = {}
    for entry in tqdm(bailly_keys):
        try:
            # Run sdcv and capture JSON output
            output = subprocess.check_output(["sdcv", "-n", "-j", entry], text=True)
            data = json.loads(output)
            # Each dict in data can have a 'definition' field
            if data and "definition" in data[0]:
                bracket_content = extract_brackets(data[0]["definition"])
                if bracket_content:
                    bracket_dict[entry] = bracket_content
        except Exception as e:
            print(f"Error processing {entry}: {e}")

    with open("bailly_brackets.py", "w", encoding="utf-8") as f:
        for k, v in bracket_dict.items():
            f.write(f"{k} = {v}\n")

if __name__ == "__main__":
    main()