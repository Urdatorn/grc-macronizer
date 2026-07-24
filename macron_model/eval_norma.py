"""
eval_norma.py

Evaluation harness for the "Norma Syllabarum Graecarum" (NSG) benchmark:
manually annotated Ancient Greek excerpts used to score automatic
vowel-length (macron) annotation of the three "dichrona" (ambiguous-length)
letters alpha, iota and upsilon.

The benchmark is loaded from HuggingFace by default
(https://huggingface.co/datasets/Urdatorn/norma, source="hf"), or from a
local git clone of https://github.com/Urdatorn/norma-syllabarum-graecarum
(source="git"). These are NOT the same benchmark: the HF version
deliberately excludes two works (insolem, pindar) that also appear in a
separate training corpus, to avoid train/test contamination -- so scores
from the two sources are not directly comparable. Pick one source and
stick with it for any given comparison.

------------------------------------------------------------------------
Benchmark layout
------------------------------------------------------------------------
Either source ships the same texts twice, in two parallel directories:

  norma_syllabify/<work>.txt   syllable brackets only, e.g.
      [Ἥ]{λι}{ο}[ν ὑμ][νεῖ][ν αὖ]{τε }{Δι}[ὸς ]{τέ}{κο}[ς ἄρ]{χε}{ο }[Μοῦ]{σα}
      ([...] = "heavy" syllable, {...} = "light" syllable -- but see below,
      "open" is re-derived from content, not from the bracket colour)

  norma_macronize/<work>.txt   macron marks only, e.g.
      Ἥλι^ον ὑμνεῖν αὖτε Δι^ὸς τέκος ἄρχεο Μοῦσα^
      (^ after a short dichronon, _ after a long one, nothing if the
      annotator left it undetermined)

The two files for a given work are line-for-line parallel (same underlying
edited text), but are NOT guaranteed to be byte-identical once brackets/marks
are stripped -- there can be tiny whitespace differences right at a bracket
boundary. This module therefore never assumes index correspondence between
the two gold files; it always re-aligns them with difflib.SequenceMatcher.

The benchmark's own methodology (see its README / the paper this evaluates)
is to score ONLY open (light) syllables: closed-syllable marks are only
sporadically supplied by the annotator and are therefore excluded from
scoring. The "evaluation set" is: every dichronon in an OPEN gold syllable
that also carries a gold mark (^ or _) in the macronize file.

------------------------------------------------------------------------
Usage
------------------------------------------------------------------------
    from eval_norma import evaluate, format_report

    def my_macronize_fn(line: str) -> str:
        ...  # return line with ^/_ added after ambiguous vowels

    results = evaluate(my_macronize_fn)
    print(format_report(results))

`macronize_fn` must be a callable `str -> str`: given a plain line (no
brackets, no marks) it must return the same text with ^/_ markup added
(using the identical convention as the gold files). It does not need to
leave every dichronon marked -- unmarked positions are simply scored as
"no prediction" (wrong for raw accuracy; treated as an implicit "short"
guess for the "defaults-to-short" metric).

For performance, `evaluate()` calls `macronize_fn` ONCE PER WORK (all of a
work's lines joined with "\n"), then splits the result back into lines by
"\n" -- this matters a great deal for the bundled rule-based macronizer,
whose per-call overhead (~3-4s, dominated by pipeline/model invocation, not
input length) would make ~950 individual per-line calls take the better
part of an hour. If the returned text does not split back into the expected
number of lines (e.g. a model that swallows/adds newlines), this module
transparently falls back to calling `macronize_fn` once per line for that
work, with a warning. Set `batch_by_work=False` to always call per line.
"""

from __future__ import annotations

import difflib
import glob
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

# grc_utils ships in the grc-macronizer venv (pip -e installed there).
from grc_utils import DICHRONA, vowel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))

# "git" source: a local clone of norma-syllabarum-graecarum, either given
# directly via NORMA_ROOT or assumed to sit as a sibling directory of this
# script (the layout used while the benchmark lived only on GitHub).
GIT_NORMA_ROOT = os.environ.get(
    "NORMA_ROOT", os.path.join(_HERE, "norma-syllabarum-graecarum")
)

# "hf" source (default): the benchmark also ships as a HuggingFace dataset
# repo, using the identical norma_macronize/*.txt + norma_syllabify/*.txt
# layout (no new parsing logic needed, just a download step). This is the
# canonical evaluation set going forward: it deliberately excludes two
# works present in the git clone (insolem, pindar) that also appear in a
# separate training corpus, to avoid train/test contamination. Numbers
# from source="hf" and source="git" are therefore NOT directly comparable
# (different work counts) -- pick one source and stick with it.
DEFAULT_NORMA_HF_REPO = "Urdatorn/norma"


def resolve_norma_dirs(source: str = "hf", repo_id: str = DEFAULT_NORMA_HF_REPO,
                        norma_root: Optional[str] = None):
    """Returns (syllabify_dir, macronize_dir, stoplist_path) for the chosen
    source. `norma_root`, if given, always wins and is used verbatim (both
    sources share the same on-disk layout, so this works for either)."""
    if norma_root is None:
        if source == "git":
            norma_root = GIT_NORMA_ROOT
        elif source == "hf":
            from huggingface_hub import snapshot_download

            norma_root = snapshot_download(
                repo_id=repo_id,
                repo_type="dataset",
                allow_patterns=["norma_macronize/*", "norma_syllabify/*", "stoplist.txt"],
            )
        else:
            raise ValueError(f"Unknown source {source!r}, expected 'git' or 'hf'")

    return (
        os.path.join(norma_root, "norma_syllabify"),
        os.path.join(norma_root, "norma_macronize"),
        os.path.join(norma_root, "stoplist.txt"),
    )

MARK_CHARS = "^_"

# ---------------------------------------------------------------------------
# Bracket-tiling helpers (syllabify files sometimes have stray punctuation
# living between/after/before bracket pairs, e.g. "...][καρ]{δί}[αν],"
# -- the trailing comma is outside any bracket. We fold such stray text into
# the neighbouring bracket so that brackets fully tile the line and every
# character can be assigned to exactly one gold syllable. This is a clean,
# self-contained re-implementation of the same idea as
# grc-macronizer/scripts/move_text_into_brackets.py.)
# ---------------------------------------------------------------------------

_BETWEEN_BRACKETS_RE = re.compile(r'([\]\}])([^\[\]\{\}]+)([\[\{])')
_TRAILING_RE = re.compile(r'([\]\}])([^\[\]\{\}]+)$')
_LEADING_RE = re.compile(r'^([^\[\{]+)([\[\{])')
_BRACKET_RE = re.compile(r'([\[\{])([^\[\]\{\}]*)([\]\}])')


def _move_text_into_brackets(line: str) -> str:
    """Move any stray (non-bracketed) text into the neighbouring bracket so
    that the line is fully tiled by bracket pairs, with no gaps."""
    prev = None
    while prev != line:
        prev = line

        def _repl(m: "re.Match[str]") -> str:
            return m.group(1)[:-1] + m.group(2) + m.group(1)[-1] + m.group(3)

        line = _BETWEEN_BRACKETS_RE.sub(_repl, line)

    m = _TRAILING_RE.search(line)
    if m:
        line = line[: m.start()] + m.group(1)[:-1] + m.group(2) + m.group(1)[-1]

    m = _LEADING_RE.match(line)
    if m:
        leading, bracket = m.group(1), m.group(2)
        line = bracket + leading + line[m.end():]

    return line


def _syllable_is_open(content: str) -> bool:
    """A gold syllable is OPEN iff its content ends in a vowel, once trailing
    non-letter characters (spaces, punctuation, elision marks) are stripped.
    Deliberately independent of the [] vs {} bracket colour: a syllable
    marked heavy ([...]) can still be open, e.g. because it contains a long
    vowel or diphthong."""
    core = content
    while core and not core[-1].isalpha():
        core = core[:-1]
    if not core:
        return False
    return vowel(core[-1])


def _parse_syllabify_line(line: str):
    """Returns (plain_text, opens) where plain_text is the concatenation of
    all bracket contents (in order) and opens[i] says whether plain_text[i]'s
    syllable is open."""
    tiled = _move_text_into_brackets(line)
    chars: List[str] = []
    opens: List[bool] = []
    for m in _BRACKET_RE.finditer(tiled):
        content = m.group(2)
        is_open = _syllable_is_open(content)
        chars.extend(content)
        opens.extend([is_open] * len(content))
    return "".join(chars), opens


def _parse_marked_line(line: str):
    """Strips ^/_ marks from `line`, returning (plain_text, marks) where
    marks[i] is '^', '_' or None -- the gold/predicted mark immediately
    following plain_text[i] in the original string. Works equally on gold
    macronize-file lines and on a macronize_fn's output."""
    plain: List[str] = []
    marks: List[Optional[str]] = []
    i, n = 0, len(line)
    while i < n:
        ch = line[i]
        if ch in MARK_CHARS:
            # Stray leading mark with no preceding base char; drop it.
            i += 1
            continue
        nxt = line[i + 1] if i + 1 < n else ""
        if nxt and nxt in MARK_CHARS:
            plain.append(ch)
            marks.append(nxt)
            i += 2
        else:
            plain.append(ch)
            marks.append(None)
            i += 1
    return "".join(plain), marks


def _align_open_flags(sp_text: str, sp_opens: List[bool], mp_text: str) -> List[Optional[bool]]:
    """Maps the per-character 'open' flags computed on the syllabify-gold
    plain text (sp_text) onto the macronize-gold plain text (mp_text),
    via difflib alignment. Positions that fall inside a non-'equal' opcode
    (i.e. exactly where the two gold files differ slightly) get None and are
    excluded from scoring, since we cannot reliably say which gold syllable
    they belong to."""
    open_for_mp: List[Optional[bool]] = [None] * len(mp_text)
    sm = difflib.SequenceMatcher(None, sp_text, mp_text, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                open_for_mp[j1 + k] = sp_opens[i1 + k]
    return open_for_mp


def _word_stoplist_flags(text: str, stoplist: set) -> List[bool]:
    """For each character position in `text`, whether it belongs to a
    whitespace-delimited token that (after stripping leading/trailing
    non-letter characters) exactly matches an entry in the stoplist."""
    flags = [False] * len(text)
    if not stoplist:
        return flags
    for m in re.finditer(r"\S+", text):
        token = m.group(0)
        core = token
        while core and not core[0].isalpha():
            core = core[1:]
        while core and not core[-1].isalpha():
            core = core[:-1]
        if token in stoplist or core in stoplist:
            for k in range(m.start(), m.end()):
                flags[k] = True
    return flags


def _load_stoplist(stoplist_path: str) -> set:
    if not os.path.exists(stoplist_path):
        return set()
    with open(stoplist_path, encoding="utf-8") as f:
        return {
            unicodedata.normalize("NFC", line.strip())
            for line in f
            if line.strip()
        }


# ---------------------------------------------------------------------------
# Corpus data structures
# ---------------------------------------------------------------------------

@dataclass
class LineRecord:
    work: str
    line_idx: int
    plain: str                       # marks/brackets-stripped reference text (fed to macronize_fn)
    gold_marks: List[Optional[str]]  # gold_marks[i] in {'^', '_', None}
    is_open: List[Optional[bool]]    # is_open[i]: syllable openness, or None if unalignable
    in_stoplist: List[bool]          # whether plain[i]'s word form is stoplisted


def _list_works(syllabify_dir: str, macronize_dir: str) -> List[str]:
    files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(syllabify_dir, "*.txt")))
    works = [os.path.splitext(f)[0] for f in files]
    missing = [
        w for w in works
        if not os.path.exists(os.path.join(macronize_dir, w + ".txt"))
    ]
    if missing:
        raise FileNotFoundError(
            f"norma_macronize/ is missing files for: {missing} "
            f"(present in norma_syllabify/)"
        )
    return works


def load_corpus(source: str = "hf", repo_id: str = DEFAULT_NORMA_HF_REPO,
                 norma_root: Optional[str] = None) -> Dict[str, List[LineRecord]]:
    """Parses every work in the benchmark into a list of LineRecord.

    source : "hf" (default) downloads/caches the benchmark from the
        HuggingFace dataset repo `repo_id` (Urdatorn/norma). "git" reads a
        local clone instead (NORMA_ROOT env var, or a norma-syllabarum-graecarum
        sibling directory of this script). `norma_root`, if given, overrides
        either source and is used directly.
    """
    syllabify_dir, macronize_dir, stoplist_path = resolve_norma_dirs(source, repo_id, norma_root)
    stoplist = _load_stoplist(stoplist_path)
    corpus: Dict[str, List[LineRecord]] = {}

    for work in _list_works(syllabify_dir, macronize_dir):
        syll_lines = (
            open(os.path.join(syllabify_dir, work + ".txt"), encoding="utf-8")
            .read()
            .splitlines()
        )
        macro_lines = (
            open(os.path.join(macronize_dir, work + ".txt"), encoding="utf-8")
            .read()
            .splitlines()
        )
        if len(syll_lines) != len(macro_lines):
            raise ValueError(
                f"{work}: line-count mismatch between norma_syllabify "
                f"({len(syll_lines)}) and norma_macronize ({len(macro_lines)})"
            )

        records: List[LineRecord] = []
        for idx, (sline, mline) in enumerate(zip(syll_lines, macro_lines)):
            sline = unicodedata.normalize("NFC", sline)
            mline = unicodedata.normalize("NFC", mline)
            if not sline.strip() and not mline.strip():
                continue

            sp_text, sp_opens = _parse_syllabify_line(sline)
            mp_text, mp_marks = _parse_marked_line(mline)
            open_for_mp = _align_open_flags(sp_text, sp_opens, mp_text)
            in_stoplist = _word_stoplist_flags(mp_text, stoplist)

            records.append(
                LineRecord(
                    work=work,
                    line_idx=idx,
                    plain=mp_text,
                    gold_marks=mp_marks,
                    is_open=open_for_mp,
                    in_stoplist=in_stoplist,
                )
            )
        corpus[work] = records

    return corpus


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _map_output_onto_reference(output_plain: str, ref_plain: str) -> List[Optional[int]]:
    """Aligns `output_plain` (a macronize_fn's de-marked output) onto
    `ref_plain` (the line's reference plain text that was fed to
    macronize_fn), returning ref_to_out[j] = the index in output_plain
    corresponding to ref_plain[j], or None if unalignable.

    Alignment is done case-insensitively, since e.g. the bundled rule-based
    macronizer lowercases its output by design; casing differences must not
    cause otherwise-identical text to be treated as non-corresponding."""
    ref_to_out: List[Optional[int]] = [None] * len(ref_plain)
    sm = difflib.SequenceMatcher(None, output_plain.lower(), ref_plain.lower(), autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                ref_to_out[j1 + k] = i1 + k
    return ref_to_out


@dataclass
class WorkResult:
    work: str
    n_eval: int = 0
    n_raw_correct: int = 0
    n_trivial_correct: int = 0
    n_default_correct: int = 0
    n_unpredicted: int = 0  # eval positions with no model mark at all

    @property
    def raw_accuracy(self) -> Optional[float]:
        return self.n_raw_correct / self.n_eval if self.n_eval else None

    @property
    def trivial_baseline_accuracy(self) -> Optional[float]:
        return self.n_trivial_correct / self.n_eval if self.n_eval else None

    @property
    def default_short_accuracy(self) -> Optional[float]:
        return self.n_default_correct / self.n_eval if self.n_eval else None

    @property
    def improvement_over_baseline(self) -> Optional[float]:
        if self.n_eval == 0:
            return None
        return self.default_short_accuracy - self.trivial_baseline_accuracy


def evaluate(
    macronize_fn: Callable[[str], str],
    use_stoplist: bool = True,
    batch_by_work: bool = True,
    works: Optional[List[str]] = None,
    verbose: bool = True,
    source: str = "hf",
    repo_id: str = DEFAULT_NORMA_HF_REPO,
    norma_root: Optional[str] = None,
) -> Dict[str, object]:
    """Runs `macronize_fn` over the Norma Syllabarum Graecarum benchmark and
    scores it against gold.

    Parameters
    ----------
    macronize_fn : callable str -> str
        Given a plain (brackets/marks-stripped) line, returns the same text
        with ^/_ macron markup added.
    use_stoplist : bool
        If True (default, matching the benchmark's own suggestion), gold
        word forms listed in stoplist.txt (rare proper names etc.) are
        excluded from scoring. Only the "git" source currently ships a
        stoplist.txt; with "hf" this is silently a no-op.
    batch_by_work : bool
        If True (default), all lines of a work are joined with "\\n" and
        passed to `macronize_fn` in a single call (falling back to one call
        per line if the returned text doesn't split back into the expected
        number of lines). This matters a lot for macronizers with high
        fixed per-call overhead. Set to False to always call line-by-line.
    works : list of str, optional
        Restrict evaluation to these work names (default: all 16).
    verbose : bool
        Print progress per work while running.
    source : "hf" (default) or "git" -- see load_corpus().
    repo_id : HuggingFace dataset repo to use when source="hf".
    norma_root : explicit local directory override for either source.

    Returns a dict: {"per_work": {work: WorkResult, ...}, "total": WorkResult}
    """
    corpus = load_corpus(source=source, repo_id=repo_id, norma_root=norma_root)
    if works is not None:
        unknown = set(works) - set(corpus)
        if unknown:
            raise ValueError(f"Unknown work(s): {sorted(unknown)}")
        corpus = {w: corpus[w] for w in works}

    per_work: Dict[str, WorkResult] = {}
    total = WorkResult(work="TOTAL")

    for work, records in corpus.items():
        if verbose:
            print(f"Evaluating {work} ({len(records)} lines)...", file=sys.stderr)

        outputs: List[str] = [None] * len(records)  # type: ignore[list-item]
        got_batch = False
        if batch_by_work and records:
            joined = "\n".join(r.plain for r in records)
            try:
                batched_out = macronize_fn(joined)
                split_out = batched_out.split("\n")
            except Exception as e:
                split_out = None
                if verbose:
                    print(f"  batched call failed ({e}); falling back to per-line", file=sys.stderr)
            if split_out is not None and len(split_out) == len(records):
                outputs = split_out
                got_batch = True
            elif verbose and split_out is not None:
                print(
                    f"  batched call returned {len(split_out)} lines, "
                    f"expected {len(records)}; falling back to per-line",
                    file=sys.stderr,
                )

        if not got_batch:
            for i, r in enumerate(records):
                try:
                    outputs[i] = macronize_fn(r.plain)
                except Exception as e:
                    if verbose:
                        print(f"  line {r.line_idx} raised {e}; treating as unmarked", file=sys.stderr)
                    outputs[i] = r.plain

        wr = WorkResult(work=work)
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

                wr.n_eval += 1

                out_idx = ref_to_out[j]
                predicted_mark = out_marks[out_idx] if out_idx is not None else None
                if predicted_mark is None:
                    wr.n_unpredicted += 1

                if predicted_mark == gold_mark:
                    wr.n_raw_correct += 1

                if gold_mark == "^":
                    wr.n_trivial_correct += 1

                default_mark = predicted_mark if predicted_mark is not None else "^"
                if default_mark == gold_mark:
                    wr.n_default_correct += 1

        per_work[work] = wr
        total.n_eval += wr.n_eval
        total.n_raw_correct += wr.n_raw_correct
        total.n_trivial_correct += wr.n_trivial_correct
        total.n_default_correct += wr.n_default_correct
        total.n_unpredicted += wr.n_unpredicted

    return {"per_work": per_work, "total": total}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _fmt_pct(x: Optional[float]) -> str:
    return f"{x:.2%}" if x is not None else "n/a"


def format_report(results: Dict[str, object]) -> str:
    per_work: Dict[str, WorkResult] = results["per_work"]
    total: WorkResult = results["total"]

    header = (
        f"{'work':<16}{'n_eval':>8}{'raw_acc':>10}{'trivial':>10}"
        f"{'defl_short':>12}{'improve':>10}{'unmarked':>10}"
    )
    lines = [header, "-" * len(header)]

    for work in sorted(per_work):
        wr = per_work[work]
        lines.append(
            f"{work:<16}{wr.n_eval:>8}{_fmt_pct(wr.raw_accuracy):>10}"
            f"{_fmt_pct(wr.trivial_baseline_accuracy):>10}"
            f"{_fmt_pct(wr.default_short_accuracy):>12}"
            f"{(_fmt_pct(wr.improvement_over_baseline) if wr.n_eval else 'n/a'):>10}"
            f"{wr.n_unpredicted:>10}"
        )

    lines.append("-" * len(header))
    lines.append(
        f"{'TOTAL':<16}{total.n_eval:>8}{_fmt_pct(total.raw_accuracy):>10}"
        f"{_fmt_pct(total.trivial_baseline_accuracy):>10}"
        f"{_fmt_pct(total.default_short_accuracy):>12}"
        f"{_fmt_pct(total.improvement_over_baseline):>10}"
        f"{total.n_unpredicted:>10}"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI: evaluate either the rule-based grc-macronizer (default) or a trained
# macron_model/ checkpoint (--model_dir) over the benchmark.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--model_dir", default=None,
                     help="Path to a trained macron_model/ checkpoint (e.g. runs/v1_gpu/best) "
                          "to evaluate instead of the rule-based macronizer.")
    ap.add_argument("--device", default=None, help="cuda / cpu, only used with --model_dir")
    ap.add_argument("--source", choices=["hf", "git"], default="hf",
                     help="Where to load Norma Syllabarum Graecarum from: the HuggingFace "
                          f"dataset repo (default, {DEFAULT_NORMA_HF_REPO!r}), or a local "
                          "git clone ('git' -- NORMA_ROOT env var, or a "
                          "norma-syllabarum-graecarum sibling directory of this script).")
    ap.add_argument("--norma_repo", default=DEFAULT_NORMA_HF_REPO,
                     help="HuggingFace dataset repo id, only used with --source hf.")
    ap.add_argument("--norma_root", default=None,
                     help="Explicit local directory override, bypassing --source entirely.")
    args = ap.parse_args()

    if args.model_dir:
        sys.path.insert(0, os.path.join(_HERE, "macron_model"))
        from predict import MacronPredictor

        predictor = MacronPredictor(args.model_dir, device=args.device)
        macronize_fn = predictor.macronize
        label = f"trained model at {args.model_dir}"
    else:
        from grc_macronizer import Macronizer

        macronizer = Macronizer(no_hypotactic=True, make_prints=False, lowercase=True)
        macronize_fn = macronizer.macronize
        label = "rule-based grc-macronizer"

    eval_kwargs = dict(source=args.source, repo_id=args.norma_repo, norma_root=args.norma_root)

    print(f"Running {label} over Norma Syllabarum Graecarum "
          f"(source={args.source})...\n", file=sys.stderr)
    results = evaluate(macronize_fn, use_stoplist=True, **eval_kwargs)
    print()
    print("=== WITH stoplist exclusion (default) ===")
    print(format_report(results))

    print(file=sys.stderr)
    print("Re-running with stoplist exclusion OFF for comparison...\n", file=sys.stderr)
    results_no_stop = evaluate(macronize_fn, use_stoplist=False, **eval_kwargs)
    print()
    print("=== WITHOUT stoplist exclusion ===")
    print(format_report(results_no_stop))
