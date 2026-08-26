#!/usr/bin/env python3
"""Build a Clink .cngm next-word model from a plain sentence corpus.

Usage: python3 tools/build-next-word.py tok source/tok.txt source/tok.sentences.txt

The word list must be the same one used with build-pack.py. Put one complete
sentence per line in the corpus file. The result is Lexicons/tok.cngm.
"""
import collections
import math
import pathlib
import re
import struct
import sys
import unicodedata

if len(sys.argv) != 4:
    raise SystemExit("Usage: python3 tools/build-next-word.py <code> <word-list.txt> <sentences.txt>")
code, word_path, corpus_path = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
if not code or not code.replace("_", "").replace("-", "").isalnum():
    raise SystemExit("Use a short language code such as tok or pt_br.")

def word(value):
    value = unicodedata.normalize("NFC", value.strip().lower())
    return value if value and not any(char.isspace() for char in value) and any(char.isalpha() for char in value) else None

# This is the same bytewise word order build-pack.py writes into the CLEX file.
words = set()
for raw in word_path.read_text(encoding="utf-8").splitlines():
    if raw.strip() and not raw.lstrip().startswith("#"):
        candidate = word(raw.rsplit(maxsplit=1)[0])
        if candidate: words.add(candidate)
ordered = sorted(words, key=lambda value: value.encode("utf-8"))
if not ordered: raise SystemExit("The word list contains no usable words.")
ids = {value: index for index, value in enumerate(ordered)}

pairs = collections.Counter()
for raw in corpus_path.read_text(encoding="utf-8").splitlines():
    # A Tatoeba export has id, language, sentence columns. A normal corpus line
    # has no tabs. In either case, the final field is the sentence text.
    sentence = raw.rsplit("\t", 1)[-1]
    tokens = [word(token) for token in re.findall(r'[^\s.,!?;:"“”‘’()\[\]{}]+', sentence)]
    tokens = [token for token in tokens if token in ids]
    pairs.update(zip(tokens, tokens[1:]))
if not pairs:
    raise SystemExit("No word pairs matched the word list. Check that the corpus and word list use the same spelling.")

totals = collections.Counter()
for (previous, _), count in pairs.items(): totals[previous] += count
# Pair groups must be previous-id ascending, then most frequent first.
ranked = sorted(pairs.items(), key=lambda item: (ids[item[0][0]], -item[1], ids[item[0][1]]))
blob = bytearray(b"CNGM" + struct.pack("<II", 1, len(ranked)))
for (previous, _), _count in ranked: blob += struct.pack("<I", ids[previous])
for (_, following), _count in ranked: blob += struct.pack("<I", ids[following])
for (previous, _), count in ranked:
    probability = count / totals[previous]
    blob.append(max(0, min(255, round((math.log10(probability) + 6) * 42))))

destination = pathlib.Path("Lexicons") / f"{code}.cngm"
destination.parent.mkdir(exist_ok=True)
destination.write_bytes(blob)
print(f"Built {destination} with {len(ranked):,} next-word pairs.")
