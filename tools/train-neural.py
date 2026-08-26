#!/usr/bin/env python3
"""
train_lm.py — train the on-device neural language model and export it to a
quantized Core ML model the keyboard loads through `NeuralLM.swift`.

See docs/16-neural-lm.md for the architecture and the memory budget this stays
under. Offline tool only — never runs in the app.

TWO TOKENIZERS, AND `--bpe` PICKS BETWEEN THEM. Everything shipping is subword:
every bundled model has a `.bpevocab`, trained with `--bpe 12000` (el/vi:
8000). The word-level path is legacy — kept for `--export-only` on old
checkpoints — but it is still the DEFAULT (`--bpe 0`), so a bare
`python3 Tools/train_lm.py --lang en` silently trains the wrong kind of model
and writes a `.lmvocab` beside a stale `.bpevocab`. `NeuralLM.bundled` prefers
`.bpevocab` and never checks its token count against the model's logit count, so
the mismatch does not crash or fall back to the bigram — it just scores the
wrong token. Always pass `--bpe`, or go through `make lm`, which now supplies it.

Pipeline:
  1. vocab  = BPE: `--bpe N` merges learned from <lang>_sentences.tsv + specials
              word-level (legacy): top `--vocab` from <lang>_50k.txt + specials
  2. train  = a 2-layer GRU LM over source/<lang>_sentences.tsv (PyTorch)
  3. export = Core ML, int8-quantized weights, compute units .all
  4. emit   = Lexicons/<lang>.mlmodelc  +  <lang>.bpevocab (or .lmvocab)

IO contract (must match NeuralLM.run):
  input  "tokens"   : Int32  MLMultiArray, shape [1, T]   (context token ids)
  output "logProbs" : Float32 MLMultiArray, shape [1, V]  (log-softmax, NEXT token)

Deps:  pip install torch coremltools
Usage: python3 Tools/train_lm.py --lang en --bpe 12000
       python3 Tools/train_lm.py --lang en --bpe 12000 --epochs 1 --max-lines 2000000
"""
import argparse
import os
import pathlib
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.normpath(os.path.join(HERE, "..", "source"))
LEXICONS = os.path.normpath(os.path.join(HERE, "..", "Lexicons"))

UNK, BOS, EOS = "<unk>", "<bos>", "<eos>"


def canonicalize(lang, word):
    """Normalize legacy corpus spellings to the characters the keyboard emits."""
    if lang == "ro":
        return word.replace("ş", "ș").replace("ţ", "ț")
    return word


def build_vocab(lang, cap):
    """Top-`cap` words by frequency (merging <lang>_50k.txt + the optional
    <lang>_supplement.tsv), then the special tokens appended at the end.
    Returns the ordered list; index = model logit column.

    LEGACY WORD-LEVEL PATH ONLY — reached from main() when `--bpe` is 0, which
    no shipped model uses. This is the sole reader of <lang>_supplement.tsv in
    this file, so on the BPE path the supplement is unreachable: `build_bpe_vocab`
    derives its tokens from the corpus alone. Editing a supplement therefore
    changes the compiled .clex (GenerateLexicons.swift reads it too) and nothing
    about the neural model. Adding words to one is a `make lexicons` job; it is
    never a reason to retrain.

    On this path the supplement (Phase 5.1) boosts modern/tech/UI words
    OpenSubtitles 2018 underweights ("apps", "dm", "wifi") so they clear the
    literal-reality floor in the compiled .clex AND appear in the LM vocab at a
    realistic frequency rank; without it they map to <unk>. BPE has no <unk>
    problem to solve — an unknown word decomposes into subwords instead.
    """
    path = os.path.join(SOURCE, f"{lang}_50k.txt")
    if not os.path.exists(path):
        sys.exit(f"missing {path} — create it from your frequency word list first")
    # Read the base wordlist as (word, count) pairs so we can merge the
    # supplement by count and re-sort by frequency.
    counts = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2:
                continue
            w = clean_word(parts[0], lang)
            if not w:
                continue
            try:
                c = float(parts[1])
            except ValueError:
                continue
            counts[w] = counts.get(w, 0) + c
    # Merge the supplement (word<TAB>count, # comments, space-sep also accepted).
    supp_path = os.path.join(SOURCE, f"{lang}_supplement.tsv")
    if os.path.exists(supp_path):
        with open(supp_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t") if "\t" in line else line.split()
                if len(parts) < 2:
                    continue
                w = clean_word(parts[0], lang)
                if not w:
                    continue
                try:
                    c = float(parts[1])
                except ValueError:
                    continue
                counts[w] = counts.get(w, 0) + c
    # Sort by count descending (frequency order), take the top `cap`.
    words = [w for w, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:cap]]
    # Specials last, so real-word ids line up with frequency rank.
    return words + [UNK, BOS, EOS]


# Strip surrounding punctuation/quotes, lowercase, keep only letter tokens (internal
# apostrophes allowed, so "don't"/"i'm" survive). Returns None for anything that
# isn't a clean word — digits, hyphenates, symbols, emoji — so the vocab and the
# training tokens are real words, not corpus artefacts.
_STRIP = ".,!?;:\"'()[]{}…—–-«»¿¡*_/\\|@#"


def clean_word(w, lang=None):
    w = canonicalize(lang, w.strip().lower()).strip(_STRIP)
    if not w:
        return None
    for c in w:
        # Indic and several other scripts use combining vowel/sign marks inside
        # ordinary words.  `str.isalpha()` is false for those marks, so accept
        # Unicode mark categories while still rejecting punctuation and digits.
        if not (c.isalpha() or unicodedata.category(c).startswith("M") or c == "'"):
            return None
    return w


def iter_sentences(lang, max_lines):
    """Yield cleaned, tokenized lowercased sentences from <lang>_sentences.tsv. The
    file is `id<TAB>sentence`; we take the text column and clean each token so the
    training distribution matches the cleaned vocab (no "you." vs "you" split)."""
    path = os.path.join(SOURCE, f"{lang}_sentences.tsv")
    if not os.path.exists(path):
        sys.exit(f"missing {path} — create it from your sentence corpus first")
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if max_lines and n >= max_lines:
                break
            text = line.split("\t", 1)[-1].strip().lower()
            if text:
                toks = [t for t in (clean_word(x, lang) for x in text.split()) if t]
                if toks:
                    yield toks
                    n += 1


# ─── BPE subword tokenizer (Phase 4) ───────────────────────────────────────
#
# A compact from-scratch byte-pair-encoding trainer (no external dependency).
# Learns `num_merges` merge operations from the training corpus, then encodes
# any word into a sequence of subword tokens. OOV words ("haptics", "rizz")
# decompose into learnable subwords instead of collapsing to <unk>.
#
# Vocabulary layout (model output index = position in the list):
#   0 .. M-1     BPE tokens (individual chars + learned merges, incl word-end)
#   M            <unk>   (present for compatibility; rarely used in BPE mode)
#   M+1          <bos>
#   M+2          <eos>
#
# Word-boundary scheme: the LAST subword of each word carries a trailing
# "</w>" marker (e.g. "hello" → "hel" + "lo</w>"). This lets the model learn
# word boundaries without a separate delimiter token. Characters that end a
# word are "c</w>", merges that end a word are "ab</w>", etc.

WORD_END = "</w>"


def train_bpe(sentences, num_merges):
    """Learn `num_merges` BPE merge operations from `sentences` (list of word lists).
    Returns (vocab_list, merges_list) where vocab_list is the full token vocabulary
    (chars + merges + specials) and merges_list is the ordered merge rules.
    """
    # Step 1: split each word into characters + word-end marker, count word freqs.
    word_freqs = {}
    for sent in sentences:
        for word in sent:
            tokens = tuple(list(word) + [WORD_END])
            word_freqs[tokens] = word_freqs.get(tokens, 0) + 1

    # Step 2: collect the initial vocabulary (all individual characters/tokens).
    vocab_set = set()
    for tokens in word_freqs:
        for t in tokens:
            vocab_set.add(t)
    merges = []
    print(f"[bpe] {len(word_freqs)} unique words, {len(vocab_set)} initial tokens")

    # Step 3: greedily merge the most frequent adjacent pair, repeat.
    for step in range(num_merges):
        pair_counts = {}
        for tokens, freq in word_freqs.items():
            for i in range(len(tokens) - 1):
                pair = (tokens[i], tokens[i + 1])
                pair_counts[pair] = pair_counts.get(pair, 0) + freq
        if not pair_counts:
            break
        best_pair = max(pair_counts, key=lambda p: (pair_counts[p], p))
        merged = best_pair[0] + best_pair[1]
        merges.append(best_pair)
        vocab_set.add(merged)
        new_word_freqs = {}
        for tokens, freq in word_freqs.items():
            new_tokens = []
            i = 0
            while i < len(tokens):
                if i < len(tokens) - 1 and tokens[i] == best_pair[0] and tokens[i + 1] == best_pair[1]:
                    new_tokens.append(merged)
                    i += 2
                else:
                    new_tokens.append(tokens[i])
                    i += 1
            key = tuple(new_tokens)
            new_word_freqs[key] = new_word_freqs.get(key, 0) + freq
        word_freqs = new_word_freqs
        if (step + 1) % 2000 == 0:
            print(f"[bpe] merge {step + 1}/{num_merges}: '{best_pair[0]}' + '{best_pair[1]}' -> '{merged}'")

    # Build the vocab list: single chars (no word-end) first, then multi-char
    # tokens, then word-end tokens, then specials. Sorted for determinism.
    chars = sorted(c for c in vocab_set if len(c) == 1)
    multi = sorted(c for c in vocab_set if len(c) > 1)
    seen = set()
    vocab_list = []
    for t in chars + multi:
        if t not in seen:
            seen.add(t)
            vocab_list.append(t)
    vocab_list += [UNK, BOS, EOS]
    print(f"[bpe] {len(vocab_list)} total tokens ({len(vocab_list) - 3} BPE + 3 specials)")
    return vocab_list, merges


def bpe_encode_word(word, merges_dict):
    """Encode a single word into BPE subword tokens using the learned merges.
    `merges_dict` maps (a, b) → rank (lower = applied earlier). Returns a list
    of token strings, the last carrying the WORD_END marker."""
    if not word:
        return [WORD_END]
    tokens = list(word) + [WORD_END]
    while len(tokens) > 1:
        best_rank = None
        best_idx = -1
        for i in range(len(tokens) - 1):
            rank = merges_dict.get((tokens[i], tokens[i + 1]))
            if rank is not None and (best_rank is None or rank < best_rank):
                best_rank = rank
                best_idx = i
        if best_idx < 0:
            break
        tokens[best_idx] = tokens[best_idx] + tokens[best_idx + 1]
        del tokens[best_idx + 1]
    return tokens


def build_bpe_vocab(lang, num_merges, max_lines):
    """Train a BPE tokenizer on the corpus and return (vocab_list, merges_dict).
    The merges_dict maps (token_a, token_b) → merge rank for `bpe_encode_word`."""
    print(f"[bpe] training {num_merges} merges on {lang} corpus ...")
    sentences = list(iter_sentences(lang, max_lines))
    vocab_list, merges = train_bpe(sentences, num_merges)
    merges_dict = {pair: i for i, pair in enumerate(merges)}
    return vocab_list, merges_dict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en")
    ap.add_argument("--vocab", type=int, default=30000)
    ap.add_argument("--dim", type=int, default=128)
    ap.add_argument("--hidden", type=int, default=256)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--window", type=int, default=12, help="max context length (must match NeuralLM.contextWindow)")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--max-lines", type=int, default=0, help="0 = whole corpus")
    ap.add_argument("--export-only", action="store_true",
                    help="skip training, load the saved checkpoint, just re-export Core ML")
    ap.add_argument("--bpe", type=int, default=0, metavar="NUM_MERGES",
                    help="use BPE subword tokenization with NUM_MERGES merges instead of "
                         "word-level vocab. OOV words decompose into subwords instead of "
                         "collapsing to <unk>. Writes <lang>.bpevocab instead of .lmvocab. "
                         "PASS THIS: every shipped model is BPE (12000; el/vi 8000), but the "
                         "default is still the legacy word-level path, and retraining a BPE "
                         "language without it leaves a .bpevocab that no longer matches the "
                         "model — silently, since nothing validates the two counts.")
    args = ap.parse_args()

    import torch
    import torch.nn as nn

    # ── Vocabulary ──────────────────────────────────────────────────────────
    # Word-level (default): top `--vocab` words from the frequency list.
    # BPE (--bpe N): N merge operations learned from the corpus; every word
    # decomposes into subword tokens, so OOV words are never <unk>.
    bpe_merges_dict = None
    if args.bpe > 0:
        vocab, bpe_merges_dict = build_bpe_vocab(args.lang, args.bpe, args.max_lines)
    else:
        vocab = build_vocab(args.lang, args.vocab)
    stoi = {w: i for i, w in enumerate(vocab)}
    unk, bos, eos = stoi[UNK], stoi[BOS], stoi[EOS]
    V = len(vocab)
    print(f"[vocab] {V} tokens (incl. specials){' [BPE]' if args.bpe > 0 else ''}")

    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[device] {device}")

    class GRULM(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(V, args.dim, padding_idx=eos)
            self.gru = nn.GRU(args.dim, args.hidden, args.layers, batch_first=True)
            # Tie output to the (projected) embedding: logits = h · Wp · Eᵀ.
            self.proj = nn.Linear(args.hidden, args.dim, bias=False)
            self.bias = nn.Parameter(torch.zeros(V))

        def forward(self, x):                      # x: [B, T] int
            e = self.emb(x)                        # [B, T, dim]
            _, h = self.gru(e)                     # h: [layers, B, hidden]
            last = self.proj(h[-1])                # [B, dim]
            logits = last @ self.emb.weight.t() + self.bias  # [B, V]
            return torch.log_softmax(logits, dim=-1)

    model = GRULM().to(device)
    # Checkpoint so re-running JUST the export (which iterates on Core ML / quant
    # settings) doesn't retrain from scratch. `--export-only` loads it and skips
    # straight to conversion.
    ckpt = os.path.join(HERE, f".lm_{args.lang}.pt")

    if args.export_only:
        if not os.path.exists(ckpt):
            sys.exit(f"--export-only but no checkpoint at {ckpt} — train first")
        model.load_state_dict(torch.load(ckpt, map_location=device))
        print(f"[train] loaded {ckpt} (skipping training)")
    else:
        # BPE mode: each word decomposes into subword tokens before encoding.
        # Word-level mode: each word is one token (or <unk> if OOV).
        if bpe_merges_dict is not None:
            def word_to_ids(word):
                return [stoi.get(t, unk) for t in bpe_encode_word(word, bpe_merges_dict)]
        else:
            def word_to_ids(word):
                return [stoi.get(word, unk)]

        def encode(tokens):
            ids = [bos]
            for word in tokens:
                ids.extend(word_to_ids(word))
            ids.append(eos)
            return ids

        # Fixed-length (context -> next) pairs, context capped to the window.
        # In BPE mode a "token" in the training pair is a subword; the window
        # still bounds the context length in model-tokens.
        print("[data] building training pairs ...")
        X, Y = [], []
        for toks in iter_sentences(args.lang, args.max_lines):
            ids = encode(toks)
            for i in range(1, len(ids)):
                X.append(ids[max(0, i - args.window):i]); Y.append(ids[i])
        if not X:
            sys.exit("no training pairs built")
        print(f"[data] {len(X)} pairs")

        opt = torch.optim.Adam(model.parameters(), lr=args.lr)
        loss_fn = nn.NLLLoss()

        def batches():
            order = torch.randperm(len(X))
            for s in range(0, len(X), args.batch):
                idx = order[s:s + args.batch]
                ctxs = [X[i] for i in idx]
                ys = torch.tensor([Y[i] for i in idx], device=device)
                T = max(len(c) for c in ctxs)
                # Left-pad with eos so the real context ends at the last timestep.
                padded = torch.full((len(ctxs), T), eos, dtype=torch.long)
                for j, c in enumerate(ctxs):
                    padded[j, T - len(c):] = torch.tensor(c)
                yield padded.to(device), ys

        print("[train] starting ...")
        model.train()
        for ep in range(args.epochs):
            total, count = 0.0, 0
            for bx, by in batches():
                opt.zero_grad()
                out = model(bx)
                loss = loss_fn(out, by)
                loss.backward()
                opt.step()
                total += loss.item(); count += 1
                if count % 200 == 0:
                    print(f"  epoch {ep} step {count} loss {total / count:.3f}")
            print(f"[train] epoch {ep} mean loss {total / max(count,1):.3f}")
        torch.save(model.state_dict(), ckpt)
        print(f"[train] saved checkpoint {ckpt}")

    # --- Export to Core ML (int8) -------------------------------------------------
    print("[export] tracing + converting ...")
    import coremltools as ct
    import numpy as np

    # Trace + convert on CPU: Core ML conversion runs on CPU, and mixing an
    # MPS-resident model with CPU example tensors trips "Placeholder storage has
    # not been allocated on MPS device". Move both to CPU first.
    model.eval()
    model.to("cpu")
    example = torch.full((1, args.window), eos, dtype=torch.long)   # CPU
    traced = torch.jit.trace(model, example)

    # Flexible sequence length 1..window so the keyboard can pass short contexts.
    seq = ct.RangeDim(lower_bound=1, upper_bound=args.window, default=args.window)
    mlmodel = ct.convert(
        traced,
        inputs=[ct.TensorType(name="tokens", shape=(1, seq), dtype=np.int32)],
        outputs=[ct.TensorType(name="logProbs")],
        compute_units=ct.ComputeUnit.ALL,
        minimum_deployment_target=ct.target.iOS17,
    )

    # 8-bit weight quantization — the budget lever (≈¼ of fp32). See docs/16.
    print("[export] int8 weight quantization ...")
    from coremltools.optimize.coreml import OpLinearQuantizerConfig, OptimizationConfig, linear_quantize_weights
    cfg = OptimizationConfig(global_config=OpLinearQuantizerConfig(mode="linear_symmetric", dtype="int8"))
    mlmodel = linear_quantize_weights(mlmodel, config=cfg)

    os.makedirs(LEXICONS, exist_ok=True)
    # Intermediate .mlpackage lives OUT of Resources/Lexicons — that folder is a
    # build resource phase, so a stray .mlpackage would double-bundle (and Xcode
    # would try to recompile it). Only the compiled .mlmodelc + .lmvocab ship.
    build_dir = os.path.join(HERE, ".lm_build")
    os.makedirs(build_dir, exist_ok=True)
    pkg = os.path.join(build_dir, f"{args.lang}.mlpackage")
    # Finder/backup services can leave AppleDouble sidecars in a previous
    # package.  coremltools removes the package before saving, but its cleanup
    # races on those sidecars; they are filesystem metadata, never model data.
    for sidecar in pathlib.Path(pkg).rglob("._*") if os.path.isdir(pkg) else []:
        sidecar.unlink(missing_ok=True)
    mlmodel.save(pkg)
    print(f"[export] wrote {pkg}")
    # A stale compiled model would make coremlcompiler refuse/duplicate; clear it.
    import shutil
    out_mlmodelc = os.path.join(LEXICONS, f"{args.lang}.mlmodelc")
    if os.path.isdir(out_mlmodelc):
        for sidecar in pathlib.Path(out_mlmodelc).rglob("._*"):
            sidecar.unlink(missing_ok=True)
        shutil.rmtree(out_mlmodelc)

    # Compile .mlpackage → .mlmodelc (what the bundle ships / NeuralLM loads).
    import subprocess
    out = subprocess.run(["xcrun", "coremlcompiler", "compile", pkg, LEXICONS],
                         capture_output=True, text=True)
    if out.returncode != 0:
        print(out.stdout, out.stderr)
        sys.exit("coremlcompiler failed")
    print(f"[export] compiled → {os.path.join(LEXICONS, args.lang + '.mlmodelc')}")

    if bpe_merges_dict is not None:
        # BPE vocab: format marker + merge count + tokens + merges for the
        # Swift decoder to reconstruct the tokenizer.
        vocab_path = os.path.join(LEXICONS, f"{args.lang}.bpevocab")
        with open(vocab_path, "w", encoding="utf-8") as f:
            f.write("BPE1\n")
            f.write(f"{len(vocab)}\n")
            for t in vocab:
                f.write(t + "\n")
            # Serialize the merges: one "a b" per line, in rank order.
            ranked = sorted(bpe_merges_dict, key=bpe_merges_dict.get)
            f.write(f"{len(ranked)}\n")
            for a, b in ranked:
                f.write(f"{a} {b}\n")
        print(f"[export] wrote {vocab_path}  ({len(vocab)} tokens, {len(ranked)} merges)")
        print("[done] add the .mlmodelc + .bpevocab to the Lexicons resource group.")
    else:
        vocab_path = os.path.join(LEXICONS, f"{args.lang}.lmvocab")
        with open(vocab_path, "w", encoding="utf-8") as f:
            f.write("\n".join(vocab))
        print(f"[export] wrote {vocab_path}  ({V} rows)")
        print("[done] add the .mlmodelc + .lmvocab to the Lexicons resource group, then "
              "enable NeuralLM in the engine.")


if __name__ == "__main__":
    main()
