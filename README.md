# Macronizing the TLG

A macronizer geared towards batch macronizing large corpora with machine-friendly markup, avoiding combining diacritics and everything that doesn't render in standard IDE and terminal fonts.

*Preparation:*
- Create a virtual environment with Python 3.12.
- After having initialized your venv, install the right version of spaCy, the dependency of odyCy, with `pip install spacy>=3.7.4,<3.8.0`.
- Use the submodule, or download odyCy by running `huggingface-cli download chcaa/grc_odycy_joint_trf`.
- Then navigate to the `grc_odycy_joint_trf` folder and install odyCy locally with `pip install grc_odycy_joint_trf`, while making sure that you are in the venv with Python 3.12 you created earlier. 
- Install the submodule `grc-utils` with `cd grc-utils` and `pip install .`.

And that's it! Start macronizing by running the notebook [here](macronize.ipynb).

If you have a plain text file you want to macronize, you can run it with `python main.py input_file output_file`.