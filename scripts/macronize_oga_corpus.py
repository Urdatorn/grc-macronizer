'''
Macronize the full OGA corpus using its own pre-computed CoNLL-U annotation
(bypassing odyCy's neural inference entirely -- see grc_macronizer/oga_conllu.py),
producing plain macronized sentences as ML training data (one per line).

Parallelized across a multiprocessing.Pool, one conllu file per work item. Each
worker process creates a blank spaCy vocab once (cached at module level in
grc_macronizer.class_text) and reuses it for every chunk/file it processes;
odyCy's weights are never loaded.

Each file is streamed in chunks of CHUNK_SIZE sentences, so a worker holds at
most one chunk in memory. After every chunk, its output is appended to
<out-dir>/parts/<stem>.txt and the chunk is recorded in <stem>.progress, both
flushed and fsynced; a finished file gets a <stem>.done marker. A killed run
loses at most the chunks in flight: rerunning the same command truncates any
half-written chunk, skips finished chunks and files, and continues. When every
file is done, the parts are joined in sorted file order into
oga_macronized.txt, with totals in oga_macronized_stats.tsv and, per module,
oga_macronized_modules.tsv: tokens_helped (success events at any recursion
depth, overlapping between modules), and top_level_tokens / top_level_dichrona
(the top-level credits, which add up to what the cascade resolved).

Diagnostics go to diagnostics/ in the working directory. Each worker logs to its
own file, diagnostics/logs/macronizer_<timestamp>_<pid>.log (every line also
carries the pid), with "CHUNK START" / "CHUNK END" lines around each chunk, and
the per-call diagnostics (module results, still-ambiguous tokens, per-token
traces) are named <stem>.<chunk>, e.g. tlg0012.tlg001...lemma.00003.

Usage:
    python scripts/macronize_oga_corpus.py --conllu-glob '/path/to/conllu/*.conllu' \
        --out-dir out/ --workers 16 [--limit-files 5]
'''

import argparse
import collections
import logging
import glob as globmod
import os
import shutil
import sys
import tempfile
import time
import warnings
from multiprocessing import Pool
from pathlib import Path

warnings.filterwarnings("ignore", category=FutureWarning)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CHUNK_SIZE = 500  # sentences per Macronizer() call / temp docbin

_worker_tmp_dir = None
_parts_dir = None


def _init_worker(parts_dir):
    global _worker_tmp_dir, _parts_dir
    _worker_tmp_dir = tempfile.mkdtemp(prefix=f"oga_macronize_{os.getpid()}_")
    _parts_dir = Path(parts_dir)
    # the forked worker inherited the parent's log file; give it its own
    from grc_macronizer.class_macronizer import configure_logging
    configure_logging()


def _sync(f):
    f.flush()
    os.fsync(f.fileno())


def _read_progress(progress_path):
    '''
    Returns (chunks_done, byte offset of the part file after the last
    recorded chunk, lines, numerator, denominator, module counts, top-level
    credits) from a progress file with one "chunk_idx offset n_lines numerator
    denominator module=count,... module=tokens:dichrona,..." row per finished
    chunk (rows written before the module and credit columns existed have five
    or six columns). A torn last row (killed mid-write) is ignored.
    '''
    done, offset, n_lines, numerator, denominator = 0, 0, 0, 0, 0
    modules = collections.Counter()
    credits = collections.Counter()  # (module, "tokens" | "dichrona") -> count
    if progress_path.exists():
        for row in progress_path.read_text(encoding="utf-8").splitlines():
            cols = row.split("\t")
            if len(cols) not in (5, 6, 7):
                continue
            idx, off, n, num, den = map(int, cols[:5])
            done, offset = idx + 1, off
            n_lines += n
            numerator += num
            denominator += den
            if len(cols) == 6 and cols[5]:
                for kv in cols[5].split(","):
                    name, count = kv.split("=")
                    modules[name] += int(count)
            if len(cols) == 7 and cols[6]:
                for kv in cols[6].split(","):
                    name, value = kv.split("=")
                    tokens, dichrona = value.split(":")
                    credits[(name, "tokens")] += int(tokens)
                    credits[(name, "dichrona")] += int(dichrona)
    return done, offset, n_lines, numerator, denominator, modules, credits


def _chunks(sentences, size):
    chunk = []
    for sent in sentences:
        chunk.append(sent)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _process_file(conllu_path):
    from spacy.tokens import DocBin
    from grc_macronizer import Macronizer
    from grc_macronizer.class_text import _get_blank_vocab
    from grc_macronizer.oga_conllu import iter_conllu, build_doc
    from grc_utils import count_dichrona_in_open_syllables

    vocab = _get_blank_vocab()

    stem = Path(conllu_path).stem
    part_path = _parts_dir / f"{stem}.txt"
    progress_path = _parts_dir / f"{stem}.progress"

    # resume: drop output of a chunk that was being written when the run died
    chunks_done, offset, n_lines, numerator, denominator, _, _ = _read_progress(progress_path)
    with open(part_path, "ab") as f:
        f.truncate(offset)

    with open(part_path, "a", encoding="utf-8") as part_f, \
         open(progress_path, "a", encoding="utf-8") as progress_f:
        for chunk_idx, chunk_sents in enumerate(_chunks(iter_conllu(conllu_path), CHUNK_SIZE)):
            if chunk_idx < chunks_done:
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

            chunk_lines, chunk_num, chunk_den, chunk_modules, chunk_credits = [], 0, 0, {}, {}
            tag = f"{stem}.{chunk_idx:05d}"
            logging.info(f"=== CHUNK START {tag} sentences={len(texts)} ===")
            try:
                macronizer = Macronizer(make_prints=False, doc_from_file=False,
                                         no_hypotactic=False, lowercase=False,
                                         custom_doc=docbin_path)
                output = macronizer.macronize(chunk_text, diagnostics_tag=tag)
                chunk_modules = macronizer.module_counts
                chunk_credits = {name: (macronizer.module_credit_tokens[name], macronizer.module_credit_dichrona[name])
                                 for name in macronizer.module_credit_tokens}
            except Exception as e:
                sys.stderr.write(f"[{stem} chunk {chunk_idx}] ERROR: {e}\n")
                logging.error(f"CHUNK ERROR {tag}: {e}")
                output = ""  # recorded as done with no lines, so a resume does not retry it
            finally:
                os.remove(docbin_path)

            if output:
                before = count_dichrona_in_open_syllables(chunk_text)
                after = count_dichrona_in_open_syllables(output)
                chunk_num = max(0, before - after)
                chunk_den = before
                chunk_lines = [l for l in output.splitlines() if l.strip()]

            for line in chunk_lines:
                part_f.write(line + "\n")
            _sync(part_f)
            module_col = ",".join(f"{name}={count}" for name, count in chunk_modules.items())
            credit_col = ",".join(f"{name}={t}:{d}" for name, (t, d) in chunk_credits.items())
            progress_f.write(f"{chunk_idx}\t{part_f.tell()}\t{len(chunk_lines)}\t{chunk_num}\t{chunk_den}\t{module_col}\t{credit_col}\n")
            _sync(progress_f)
            logging.info(f"=== CHUNK END {tag} lines={len(chunk_lines)} resolved={chunk_num}/{chunk_den} ===")

            n_lines += len(chunk_lines)
            numerator += chunk_num
            denominator += chunk_den

    with open(_parts_dir / f"{stem}.done", "w", encoding="utf-8") as f:
        f.write(f"{n_lines}\t{numerator}\t{denominator}\n")
        _sync(f)

    return stem, n_lines, numerator, denominator


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
    parts_dir = out_dir / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    combined_path = out_dir / "oga_macronized.txt"
    stats_path = out_dir / "oga_macronized_stats.tsv"
    modules_path = out_dir / "oga_macronized_modules.tsv"

    todo = [p for p in files if not (parts_dir / f"{Path(p).stem}.done").exists()]
    todo.sort(key=os.path.getsize, reverse=True)  # largest first, so no big file is left for the tail

    print(f"{len(files)} files ({len(files) - len(todo)} already done), "
          f"{args.workers} workers, chunk size {CHUNK_SIZE}", flush=True)
    t0 = time.time()
    n_done = 0

    # Import once in the parent: forked workers inherit the loaded databases instead of each
    # importing them, which on a fresh checkout also compiles proper_names.py (several GB per worker).
    import grc_macronizer  # noqa: F401

    with Pool(processes=args.workers, initializer=_init_worker, initargs=(str(parts_dir),)) as pool:
        for stem, n_lines, numerator, denominator in pool.imap_unordered(_process_file, todo):
            n_done += 1
            elapsed = time.time() - t0
            rate = n_done / elapsed if elapsed > 0 else 0
            eta = (len(todo) - n_done) / rate if rate > 0 else float("inf")
            ratio = numerator / denominator if denominator else 0
            print(f"[{n_done}/{len(todo)}] {stem}: {n_lines} lines, ratio {ratio:.2%} "
                  f"({elapsed:.0f}s elapsed, ETA {eta/60:.1f}min)", flush=True)

    total_num, total_den = 0, 0
    total_modules = collections.Counter()
    total_credits = collections.Counter()
    with open(combined_path, "w", encoding="utf-8") as combined_f:
        for p in files:
            stem = Path(p).stem
            n_lines, numerator, denominator = map(int, (parts_dir / f"{stem}.done").read_text().split("\t"))
            total_num += numerator
            total_den += denominator
            progress = _read_progress(parts_dir / f"{stem}.progress")
            total_modules.update(progress[5]) # update(), not +=, keeps modules with zero counts
            total_credits.update(progress[6])
            with open(parts_dir / f"{stem}.txt", encoding="utf-8") as part_f:
                shutil.copyfileobj(part_f, combined_f)

    with open(stats_path, "w", encoding="utf-8") as f:
        f.write(f"numerator\t{total_num}\n")
        f.write(f"denominator\t{total_den}\n")
        f.write(f"ratio\t{total_num/total_den if total_den else 0:.4f}\n")

    credit_names = [n for n, kind in total_credits if kind == "tokens"]
    with open(modules_path, "w", encoding="utf-8") as f:
        f.write("module\ttokens_helped\ttop_level_tokens\ttop_level_dichrona\n")
        for name in list(total_modules) + [n for n in dict.fromkeys(credit_names) if n not in total_modules]:
            f.write(f"{name}\t{total_modules.get(name, '')}\t{total_credits[(name, 'tokens')]}\t{total_credits[(name, 'dichrona')]}\n")

    print(f"\nDone in {(time.time()-t0)/60:.1f} min. "
          f"Overall macronization ratio: {total_num/total_den if total_den else 0:.2%}")
    print(f"Output: {combined_path}")


if __name__ == "__main__":
    main()
