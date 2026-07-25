'''
Paired significance test (McNemar) between the rule-based macronizer and the
trained transformer on Norma, on the "defaults-to-short" metric (the paper's
primary reported number). Reuses eval_norma.py's own alignment/parsing logic
rather than reimplementing it, so results are guaranteed consistent with the
numbers reported in the paper.

Usage:
    python paired_norma_test.py --model_dir Ericu950/oga-macronizer-char --source git
'''

import argparse
import sys

from eval_norma import (
    load_corpus,
    _parse_marked_line,
    _map_output_onto_reference,
)


def per_position_correctness(macronize_fn, corpus, use_stoplist=True, verbose=True):
    '''Returns {(work, line_idx, j): bool} -- defaults-to-short correctness
    per evaluated position, mirroring evaluate()'s own scoring loop exactly.'''
    out = {}
    for work, records in corpus.items():
        if verbose:
            print(f"Scoring {work} ({len(records)} lines)...", file=sys.stderr)
        joined = "\n".join(r.plain for r in records)
        try:
            batched_out = macronize_fn(joined)
            outputs = batched_out.split("\n")
            if len(outputs) != len(records):
                raise ValueError("line count mismatch")
        except Exception as e:
            if verbose:
                print(f"  batched call failed ({e}); falling back to per-line", file=sys.stderr)
            outputs = [macronize_fn(r.plain) for r in records]

        for record, output in zip(records, outputs):
            out_plain, out_marks = _parse_marked_line(output)
            ref_to_out = _map_output_onto_reference(out_plain, record.plain)
            for j in range(len(record.plain)):
                if not record.is_open[j]:
                    continue
                gold_mark = record.gold_marks[j]
                if gold_mark is None:
                    continue
                if use_stoplist and record.in_stoplist[j]:
                    continue
                out_idx = ref_to_out[j]
                predicted_mark = out_marks[out_idx] if out_idx is not None else None
                default_mark = predicted_mark if predicted_mark is not None else "^"
                out[(work, record.line_idx, j)] = (default_mark == gold_mark)
    return out


def mcnemar(rb_correct, tf_correct):
    '''2x2 contingency + McNemar's test (with continuity correction) on the
    discordant pairs. Returns (b, c, chi2, p_value) where b = rb-right/tf-wrong,
    c = rb-wrong/tf-right.'''
    keys = set(rb_correct) & set(tf_correct)
    both, rb_only, tf_only, neither = 0, 0, 0, 0
    for k in keys:
        r, t = rb_correct[k], tf_correct[k]
        if r and t:
            both += 1
        elif r and not t:
            rb_only += 1
        elif t and not r:
            tf_only += 1
        else:
            neither += 1

    b, c = rb_only, tf_only  # standard McNemar notation
    n = b + c
    if n == 0:
        return b, c, 0.0, 1.0
    chi2 = (abs(b - c) - 1) ** 2 / n  # continuity-corrected
    # chi-square with 1 df -> p-value via regularized incomplete gamma,
    # implemented by hand to avoid a scipy dependency
    p_value = _chi2_sf_1df(chi2)
    return b, c, chi2, p_value


def _chi2_sf_1df(x):
    '''Survival function of chi-square with 1 df = erfc(sqrt(x/2)).'''
    import math
    return math.erfc(math.sqrt(x / 2)) if x >= 0 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", default="Ericu950/oga-macronizer-char")
    ap.add_argument("--device", default=None)
    ap.add_argument("--source", choices=["hf", "git"], default="git")
    ap.add_argument("--norma_repo", default="Urdatorn/norma")
    ap.add_argument("--norma_root", default=None)
    args = ap.parse_args()

    print("Loading rule-based macronizer...", file=sys.stderr)
    from grc_macronizer import Macronizer
    rb_macronizer = Macronizer(no_hypotactic=True, make_prints=False, lowercase=True)

    print("Loading transformer...", file=sys.stderr)
    sys.path.insert(0, "macron_model")
    from predict import MacronPredictor
    predictor = MacronPredictor(args.model_dir, device=args.device)

    corpus = load_corpus(source=args.source, repo_id=args.norma_repo, norma_root=args.norma_root)

    print("Scoring rule-based...", file=sys.stderr)
    rb_correct = per_position_correctness(rb_macronizer.macronize, corpus)
    print("Scoring transformer...", file=sys.stderr)
    tf_correct = per_position_correctness(predictor.macronize, corpus)

    b, c, chi2, p = mcnemar(rb_correct, tf_correct)
    n_total = len(set(rb_correct) & set(tf_correct))
    n_both = sum(1 for k in rb_correct if rb_correct[k] and tf_correct.get(k))

    print(f"\nPaired positions: {n_total}")
    print(f"Both correct: {n_both}")
    print(f"Rule-based correct, transformer wrong (b): {b}")
    print(f"Transformer correct, rule-based wrong (c): {c}")
    print(f"McNemar chi2 (continuity-corrected, 1 df): {chi2:.4f}")
    print(f"p-value: {p:.6g}")
    print(f"Significant at alpha=0.05: {p < 0.05}")


if __name__ == "__main__":
    main()
