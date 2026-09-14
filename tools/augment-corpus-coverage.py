#!/usr/bin/env python3
"""Add attested apostrophe words and sentence-start evidence to an existing pack.

Inputs are explicit frozen CLEX/CNGM files plus a licensed sentence corpus. All
existing unigram bytes, letter-model bytes, and bigram probabilities survive;
word IDs are remapped after adding byte-sorted dictionary entries. No replacement
map, guessed word frequency, model training, or publishing is involved.
"""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import re
import statistics
import struct
import unicodedata


def u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def read_lexicon(path):
    data = path.read_bytes()
    if len(data) < 16 or data[:4] != b"CLEX" or u32(data, 4) != 1:
        raise ValueError("Expected CLEX1 input")
    count, alphabet = u32(data, 8), u32(data, 12)
    offsets_start = 16 + 4 * alphabet + (alphabet + 1) * alphabet
    frequency_start = offsets_start + 4 * (count + 1)
    lengths_start = frequency_start + count
    blob_start = lengths_start + count
    offsets = struct.unpack_from(f"<{count + 1}I", data, offsets_start)
    if blob_start + offsets[-1] > len(data):
        raise ValueError("Truncated CLEX input")
    words = [data[blob_start + offsets[i]:blob_start + offsets[i + 1]].decode("utf-8")
             for i in range(count)]
    return data, words, dict(zip(words, data[frequency_start:frequency_start + count])), \
        dict(zip(words, data[lengths_start:lengths_start + count])), data[16:offsets_start]


def read_bigrams(path, words):
    data = path.read_bytes()
    if len(data) < 12 or data[:4] != b"CNGM" or u32(data, 4) != 1:
        raise ValueError("Expected CNGM1 input")
    count = u32(data, 8)
    if len(data) != 12 + count * 9:
        raise ValueError("Invalid CNGM length")
    result = {}
    for i in range(count):
        a, b = u32(data, 12 + i * 4), u32(data, 12 + count * 4 + i * 4)
        if a >= len(words) or b >= len(words):
            raise ValueError("CNGM word ID is outside the supplied CLEX")
        result[(words[a], words[b])] = (data[12 + count * 8 + i], i)
    return data, result


TOKEN = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)


def sentences(path):
    with path.open(encoding="utf-8") as source:
        for raw in source:
            # Tatoeba's final TSV field and a plain one-sentence-per-line file
            # have the same treatment. Quotation marks do not become letters.
            text = raw.rstrip("\r\n").rsplit("\t", 1)[-1]
            yield [unicodedata.normalize("NFC", token.lower().replace("’", "'"))
                   for token in TOKEN.findall(text)]


def quantize(probability, floor, scale):
    # Swift's positive .rounded() is half-away-from-zero, not Python's bankers rounding.
    return max(0, min(255, math.floor((math.log10(probability) - floor) * scale + 0.5)))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def existing_sentence_starts(data, words):
    """Read an optional CBOS row, preserving absent evidence as absent."""
    alphabet = u32(data, 12)
    offsets_start = 16 + 4 * alphabet + (alphabet + 1) * alphabet
    blob_start = offsets_start + 4 * (len(words) + 1) + 2 * len(words)
    blob_end = blob_start + u32(data, offsets_start + 4 * len(words))
    tail = data[blob_end:]
    if not tail:
        return None
    if (tail[:4] != b"CBOS" or len(tail) != 12 + 4 * len(words)
            or u32(tail, 4) != 1 or u32(tail, 8) != len(words)):
        raise ValueError("Cannot preserve an unknown CLEX trailing extension")
    return dict(zip(words, struct.unpack_from(f"<{len(words)}I", tail, 12)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", required=True)
    parser.add_argument("--base-lexicon", required=True, type=pathlib.Path)
    parser.add_argument("--base-bigrams", required=True, type=pathlib.Path)
    parser.add_argument("--sentences", required=True, type=pathlib.Path)
    parser.add_argument("--output-directory", required=True, type=pathlib.Path)
    parser.add_argument("--receipt", required=True, type=pathlib.Path)
    parser.add_argument("--preserve-sentence-start-evidence", action="store_true",
                        help="Keep existing CBOS counts/absence instead of adding sentence-start evidence")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", args.code):
        parser.error("Invalid language code")
    original, words, frequencies, lengths, letter_model = read_lexicon(args.base_lexicon)
    original_bigrams, pairs = read_bigrams(args.base_bigrams, words)
    observations, starts = collections.Counter(), collections.Counter()
    sentence_count = 0
    for tokens in sentences(args.sentences):
        observations.update(tokens)
        if tokens:
            starts[tokens[0]] += 1
            sentence_count += 1
    # Compare probabilities rather than corpus totals: many high-support shared
    # words calibrate the new corpus to the immutable pack's existing scale.
    ratios = [10 ** (frequencies[word] / 28 - 9) / count
              for word, count in observations.items()
              if count >= 1000 and "'" not in word and word in frequencies]
    if len(ratios) < 25:
        raise ValueError("Insufficient shared observations for corpus calibration")
    scale = statistics.median(ratios)
    additions = {word: count for word, count in observations.items()
                 if count >= 25 and "'" in word and len(word) <= 32 and word not in frequencies}
    for word, count in additions.items():
        frequencies[word] = quantize(count * scale, -9, 28)
        lengths[word] = min(255, len(word))
    ordered = sorted(frequencies, key=lambda value: value.encode("utf-8"))
    ids = {word: index for index, word in enumerate(ordered)}
    data = bytearray(b"CLEX" + struct.pack("<III", 1, len(ordered), u32(original, 12)))
    data += letter_model
    offset = 0
    for word in ordered:
        data += struct.pack("<I", offset)
        offset += len(word.encode("utf-8"))
    data += struct.pack("<I", offset)
    data += bytes(frequencies[word] for word in ordered)
    data += bytes(lengths[word] for word in ordered)
    for word in ordered:
        data += word.encode("utf-8")
    # A coverage-only repair must not silently change sentence casing or add an
    # all-word table unrelated to swipe. Existing CBOS counts are remapped by
    # word identity when present; absent evidence remains absent. The default
    # retains the historical English generator's corpus-derived CBOS behavior.
    output_starts = (existing_sentence_starts(original, words)
                     if args.preserve_sentence_start_evidence else starts)
    if output_starts is not None:
        data += b"CBOS" + struct.pack("<II", 1, len(ordered))
        for word in ordered:
            data += struct.pack("<I", min(0xFFFFFFFF, output_starts.get(word, 0)))

    new_pairs, previous_totals = collections.Counter(), collections.Counter()
    for tokens in sentences(args.sentences):
        for a, b in zip(tokens, tokens[1:]):
            if a not in ids or b not in ids:
                continue
            previous_totals[a] += 1
            if a in additions or b in additions:
                new_pairs[(a, b)] += 1
    old_rows = collections.defaultdict(list)
    for (a, b), (probability, rank) in pairs.items():
        old_rows[a].append((probability, rank))
    for row in old_rows.values():
        row.sort(key=lambda value: (-value[0], value[1]))
    eligible = collections.defaultdict(list)
    for pair, count in new_pairs.items():
        if count < 25:
            continue
        a, b = pair
        probability = quantize(count / previous_totals[a], -6, 42)
        row = old_rows.get(a, [])
        # Existing follower cutoffs never fall. For a large existing block a new
        # entry must also belong to its top-64 probability band. At most 32 new
        # entries join an existing block, and a new block has at most 64 entries.
        floor = row[min(63, len(row) - 1)][0] if row else 0
        if probability >= floor:
            eligible[a].append((pair, count, probability))
    accepted_pairs = []
    for a in sorted(eligible, key=lambda value: value.encode("utf-8")):
        ranked = sorted(eligible[a], key=lambda value: (-value[1], value[0][1].encode("utf-8")))
        for pair, count, probability in ranked[:32 if a in old_rows else 64]:
            pairs[pair] = (probability, len(pairs))
            accepted_pairs.append({"previous": pair[0], "next": pair[1], "count": count,
                                   "quantizedProbability": probability})
    ranked = sorted(pairs.items(), key=lambda item: (ids[item[0][0]], -item[1][0], item[1][1]))
    ngram = bytearray(b"CNGM" + struct.pack("<II", 1, len(ranked)))
    for (a, _), _value in ranked:
        ngram += struct.pack("<I", ids[a])
    for (_, b), _value in ranked:
        ngram += struct.pack("<I", ids[b])
    ngram += bytes(value[0] for _pair, value in ranked)
    args.output_directory.mkdir(parents=True, exist_ok=True)
    clex_path = args.output_directory / f"{args.code}.clex"
    cngm_path = args.output_directory / f"{args.code}.cngm"
    clex_path.write_bytes(data)
    cngm_path.write_bytes(ngram)
    receipt = {
        "format": "corpus-coverage-1", "code": args.code,
        "inputs": {"baseLexiconSHA256": sha(original), "baseBigramsSHA256": sha(original_bigrams),
                   "sentenceCorpusSHA256": sha(args.sentences.read_bytes())},
        "sentenceCount": sentence_count, "sharedCalibrationWords": len(ratios),
        "sentenceStartEvidence": "preserved" if args.preserve_sentence_start_evidence else "corpus",
        "probabilityPerCorpusCount": scale,
        "oldWords": len(words), "addedWords": len(additions), "finalWords": len(ordered),
        "oldPairs": u32(original_bigrams, 8), "addedPairs": len(accepted_pairs), "finalPairs": len(pairs),
        "wordEvidence": [{"word": word, "count": additions[word], "sentenceStarts": starts[word],
                          "quantizedFrequency": frequencies[word]} for word in sorted(additions)],
        "newPairEvidence": accepted_pairs,
        "outputs": {"lexiconSHA256": sha(data), "bigramsSHA256": sha(ngram)},
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{args.code}: preserved {len(words)} word priors and {u32(original_bigrams, 8)} pair probabilities; "
          f"added {len(additions)} words, {len(accepted_pairs)} pairs; "
          f"sentence-start evidence {receipt['sentenceStartEvidence']}")


if __name__ == "__main__":
    main()
