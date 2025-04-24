# A Macronizer for Ancient Greek

![cast](docs/media/macronizer.gif)

A macronizer geared towards batch macronizing corpora with machine-friendly markup, avoiding combining diacritics and everything that doesn't render in standard IDE and terminal fonts unless specifically asked for.

*Installation:*
- Create a virtual environment with Python 3.12. Nothing will work if you don't get this step right!
- After having initialized your venv, activate it and install the right version of spaCy, the dependency of odyCy, with `pip install spacy>=3.7.4,<3.8.0`.
- Navigate to `external/grc_odycy_joint_trf` and install odyCy locally with `pip install grc_odycy_joint_trf`, while making sure that you are still in the venv with Python 3.12 you created earlier. 
- Install the submodule `grc-utils` with `cd grc-utils` and `pip install .`.

And that's it! Start macronizing by running the notebook [here](macronize.ipynb).

If you have a plain text file you want to macronize, you can run it with `python main.py input_file output_file`.