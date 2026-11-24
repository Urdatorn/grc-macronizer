"""
Convert Opera Graeca Adnotata (OGA) CoNLL-U file(s) into spaCy DocBin(s),
bypassing odyCy's neural pipeline entirely (only its vocab/StringStore is
used). See grc_macronizer/oga_conllu.py for the full AGDT->UD mapping and
caveats.

Usage:
    python scripts/oga_conllu_to_docbin.py <input.conllu> [<input2.conllu> ...] --out-dir DIR
    python scripts/oga_conllu_to_docbin.py --glob 'conllu/*.conllu' --out-dir DIR

Each input file produces one <stem>.spacy DocBin in --out-dir, containing
one Doc per sentence in that file.

NOTE: this script deliberately does NOT parallelize / batch the full ~2000
file OGA corpus -- see the task brief. Point it at a handful of files to
validate, then wire it into a proper batch/array job separately.
"""

import argparse
import glob as globmod
import sys
import time
from pathlib import Path

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from grc_macronizer.oga_conllu import convert_file_to_docbin  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="*", help="CoNLL-U file paths")
    parser.add_argument("--glob", help="Glob pattern for CoNLL-U files (alternative to listing them)")
    parser.add_argument("--out-dir", required=True, help="Directory to write .spacy DocBin files into")
    args = parser.parse_args()

    files = list(args.inputs)
    if args.glob:
        files.extend(sorted(globmod.glob(args.glob)))
    if not files:
        parser.error("No input files given (use positional args and/or --glob)")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading grc_odycy_joint_trf vocab (no forward pass will be run)...")
    t0 = time.time()
    import grc_odycy_joint_trf
    nlp = grc_odycy_joint_trf.load()
    vocab = nlp.vocab
    print(f"  ...loaded in {time.time() - t0:.1f}s")

    total_sentences = 0
    for fn in files:
        stem = Path(fn).stem
        out_path = out_dir / f"{stem}.spacy"
        t0 = time.time()
        n = convert_file_to_docbin(vocab, fn, out_path)
        total_sentences += n
        print(f"{fn} -> {out_path}  ({n} sentences, {time.time() - t0:.1f}s)")

    print(f"\nDone. {len(files)} file(s), {total_sentences} sentences total.")


if __name__ == "__main__":
    main()
