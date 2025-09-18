# A Macronizer for Ancient Greek

![PyPI](https://img.shields.io/pypi/v/grc-macronizer?color=blue&label=PyPI&logo=python&logoColor=white)

<img src="docs/media/macronizer.gif" width="300">

This is the first software to automatically mark the vowel length of alphas, iotas and ypsilons in Ancient Greek text, a crucial task for any research on Greek prosody and verse. Developed by me, Albin Thörn Cleland, as part of my doctoral research at Lund university, it is geared towards batch macronizing corpora with machine-friendly markup, avoiding combining diacritics and everything that doesn't render in standard IDE and terminal fonts unless specifically asked for.

A quick and superficial presentation of the method and the results is included in [these slides](docs/Makroniserare_Filologkonferensen_25.pdf) (in Swedish).

# Installation

- Create a virtual environment with Python 3.12. Nothing will work if you don't get this step right!
- After having initialized your venv, activate it and install the right version of spaCy, the dependency of odyCy, with `pip install spacy==3.7.5`.
- Navigate to `external/grc_odycy_joint_trf` and install odyCy locally with `pip install grc_odycy_joint_trf-0.7.0-py3-none-any.whl`, while making sure that you are still in the venv with Python 3.12 you created earlier. 
- Install the submodule `grc-utils` with `cd grc-utils` and `pip install .`.

# How to use

Start macronizing by running the notebook [here](macronize.ipynb), or by modifying this minimal script:

```
import re

from grc_macronizer import Macronizer

macronizer = Macronizer(make_prints=False)

input = "Δαρείου καὶ Παρυσάτιδος γίγνονται παῖδες δύο, πρεσβύτερος μὲν Ἀρταξέρξης, νεώτερος δὲ Κῦρος"

output = macronizer.macronize(input)

output_split = [sentence for sentence in re.findall(r'[^.\n;\u037e]+[.\n;\u037e]?', output) if sentence]
for line in output_split[:500]:
    print(line)
```

Note that if you have a newer spaCy pipeline for Ancient Greek, it is easy to substitute it for odyCy. Indeed, the rest of the software has no legacy dependencies and should run with the latest python. 

# License

(C) Albin Thörn Cleland

This repository is under the copyleft GNU GPL 3 license (compatible with the MIT license), which means you are more than welcome to fork and build on this software for your own open-science research, as long as your code retains an equally generous licensing. If you have found this repository useful, please cite it in the following way:

> Thörn Cleland, Albin and Eric Cullhed (2025). Automatic Annotation of Ancient Greek Vowel Length. Forthcoming.
