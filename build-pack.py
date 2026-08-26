#!/usr/bin/env python3
"""Build a basic Clink .clex dictionary from a UTF-8 word list.

Usage: python3 build-pack.py tok source/tok.txt
Each line is either a word or word<TAB>frequency.
"""
import math, pathlib, struct, sys, unicodedata

if len(sys.argv) != 3:
    raise SystemExit("Usage: python3 build-pack.py <language-code> <word-list.txt>")
code, source = sys.argv[1], pathlib.Path(sys.argv[2])
if not code.replace("_", "").replace("-", "").isalnum() or not code:
    raise SystemExit("Use a short language code such as tok or pt_br.")

counts = {}
for raw in source.read_text(encoding="utf-8").splitlines():
    raw = raw.strip()
    if not raw or raw.startswith("#"): continue
    # FrequencyWords uses a single space; hand-authored pack lists conventionally
    # use a tab. Both forms are source data, never part of the word.
    fields = raw.rsplit(maxsplit=1)
    word, sep, amount = (fields[0], " ", fields[1]) if len(fields) == 2 else (raw, "", "")
    word = unicodedata.normalize("NFC", word.strip().lower())
    # Source frequency files sometimes include punctuation as a "word".  A
    # lexicon entry must contain at least one letter; this keeps punctuation
    # prediction in the keyboard layer instead of making it a candidate.
    if not word or any(ch.isspace() for ch in word) or not any(ch.isalpha() for ch in word): continue
    try: count = float(amount) if sep else 1.0
    except ValueError: count = 1.0
    if count > 0: counts[word] = counts.get(word, 0) + count
if not counts: raise SystemExit("No usable words found. Put one word on each line.")

total = sum(counts.values())
entries = sorted(((word, count / total) for word, count in counts.items()), key=lambda x: x[0].encode())
letters = {}
for word, probability in entries:
    for ch in word: letters[ch] = letters.get(ch, 0) + probability
alphabet = [ch for ch, _ in sorted(letters.items(), key=lambda x: -x[1])][:48]
index = {ch: i for i, ch in enumerate(alphabet)}; n = len(alphabet)
rows = [[0.0] * n for _ in range(n + 1)]
for word, probability in entries:
    chars = list(word)
    if chars and chars[0] in index: rows[0][index[chars[0]]] += probability
    for a, b in zip(chars, chars[1:]):
        if a in index and b in index: rows[index[a] + 1][index[b]] += probability
data = bytearray(b"CLEX" + struct.pack("<III", 1, len(entries), n))
for ch in alphabet: data += struct.pack("<I", ord(ch))
for row in rows:
    maximum = max(row, default=0)
    data += bytes(round(255 * value / maximum) if maximum else 0 for value in row)
offset = 0
for word, _ in entries:
    data += struct.pack("<I", offset); offset += len(word.encode())
data += struct.pack("<I", offset)
for _, probability in entries: data.append(max(0, min(255, round((math.log10(probability) + 9) * 28))))
for word, _ in entries: data.append(min(255, len(word)))
for word, _ in entries: data += word.encode()
output = pathlib.Path("Lexicons") / f"{code}.clex"; output.parent.mkdir(exist_ok=True)
output.write_bytes(data)
print(f"Built {output} with {len(entries):,} words.")
