'''
Macronize the full OGA corpus using its own pre-computed CoNLL-U annotation
(bypassing odyCy's neural inference entirely -- see grc_macronizer/oga_conllu.py),
producing plain macronized sentences as ML training data (one per line).

Parallelized across a multiprocessing.Pool, one conllu file per work item. Each
worker process loads the odyCy vocab once (cached at module level in
grc_macronizer.class_text) and reuses it for every chunk/file it processes.

Usage:
    python macronize_oga_corpus.py --conllu-glob '/path/to/conllu/*.conllu' \
        --out-dir out/ --workers 16 [--limit-files 5]
'''

import argparse
import glob as globmod
import os
import sys
import tempfile
import time
import warnings
from multiprocessing import Pool
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

REPO_ROOT = Path(__file__).resolve().parents[1] / "grc-macronizer"
sys.path.insert(0, str(REPO_ROOT))

CHUNK_SIZE = 500  # sentences per Macronizer() call / temp docbin

_worker_tmp_dir = None


def _init_worker():
    global _worker_tmp_dir
    import grc_odycy_joint_trf  # noqa: F401  -- trigger download/cache check once
    _worker_tmp_dir = tempfile.mkdtemp(prefix=f"oga_macronize_{os.getpid()}_")


def _process_file(conllu_path):
    from spacy.tokens import DocBin
    from grc_macronizer import Macronizer
    from grc_macronizer.class_text import _get_odycy_nlp
    from grc_macronizer.oga_conllu import parse_conllu, build_doc
    from grc_utils import count_dichrona_in_open_syllables

    nlp = _get_odycy_nlp()
    vocab = nlp.vocab

    sentences = parse_conllu(conllu_path)
    stem = Path(conllu_path).stem
    out_lines = []
    numerator = 0
    denominator = 0
    n_chunks = (len(sentences) + CHUNK_SIZE - 1) // CHUNK_SIZE

    for chunk_idx in range(n_chunks):
        chunk_sents = sentences[chunk_idx * CHUNK_SIZE:(chunk_idx + 1) * CHUNK_SIZE]
        chunk_sents = [s for s in chunk_sents if s]
        if not chunk_sents:
            continue

        doc_bin = DocBin(store_user_data=False)
        texts = []
        for sent in chunk_sents:
            doc = build_doc(vocab, sent)
            doc_bin.add(doc)
            texts.append(doc.text)

        docbin_path = os.path.join(_worker_tmp_dir, f"{stem}_{chunk_idx}.spacy")
        doc_bin.to_disk(docbin_path)

        chunk_text = "\n".join(texts) + "\n"

        try:
            macronizer = Macronizer(make_prints=False, doc_from_file=False,
                                     no_hypotactic=True, lowercase=True,
                                     custom_doc=docbin_path)
            output = macronizer.macronize(chunk_text)
        except Exception as e:
            sys.stderr.write(f"[{stem} chunk {chunk_idx}] ERROR: {e}\n")
            os.remove(docbin_path)
            continue

        os.remove(docbin_path)

        if output:
            before = count_dichrona_in_open_syllables(chunk_text)
            after = count_dichrona_in_open_syllables(output)
            numerator += max(0, before - after)
            denominator += before
            out_lines.extend(l for l in output.splitlines() if l.strip())

    return stem, out_lines, numerator, denominator


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conllu-glob", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit-files", type=int, default=None)
    args = ap.parse_args()

    files = sorted(globmod.glob(args.conllu_glob))
    if args.limit_files:
        files = files[:args.limit_files]
    if not files:
        print("No files matched the glob.", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    combined_path = out_dir / "oga_macronized.txt"
    stats_path = out_dir / "oga_macronized_stats.tsv"

    print(f"{len(files)} files, {args.workers} workers, chunk size {CHUNK_SIZE}")
    t0 = time.time()
    total_num, total_den = 0, 0
    n_done = 0

    with open(combined_path, "w", encoding="utf-8") as combined_f, \
         Pool(processes=args.workers, initializer=_init_worker) as pool:
        for stem, out_lines, numerator, denominator in pool.imap_unordered(_process_file, files):
            for line in out_lines:
                combined_f.write(line + "\n")
            combined_f.flush()
            total_num += numerator
            total_den += denominator
            n_done += 1
            elapsed = time.time() - t0
            rate = n_done / elapsed if elapsed > 0 else 0
            eta = (len(files) - n_done) / rate if rate > 0 else float("inf")
            ratio = total_num / total_den if total_den else 0
            print(f"[{n_done}/{len(files)}] {stem}: {len(out_lines)} lines "
                  f"(running ratio {ratio:.2%}, {elapsed:.0f}s elapsed, ETA {eta/60:.1f}min)",
                  flush=True)

    with open(stats_path, "w", encoding="utf-8") as f:
        f.write(f"numerator\t{total_num}\n")
        f.write(f"denominator\t{total_den}\n")
        f.write(f"ratio\t{total_num/total_den if total_den else 0:.4f}\n")

    print(f"\nDone in {(time.time()-t0)/60:.1f} min. "
          f"Overall macronization ratio: {total_num/total_den if total_den else 0:.2%}")
    print(f"Output: {combined_path}")


if __name__ == "__main__":
    main()
