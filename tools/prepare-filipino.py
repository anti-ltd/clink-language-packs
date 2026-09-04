#!/usr/bin/env python3
"""Fetch the licensed Tagalog sources used to train the Filipino (`fil`) pack.

Filipino is standardized from Tagalog. Tatoeba labels its sentence export `tgl`,
so the source receipt makes that relationship explicit instead of mislabelling
the corpus as a separate language. The compiled pack remains `fil`.
"""
import bz2
import collections
import hashlib
import json
import pathlib
import re
import unicodedata
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
SENTENCE_URL = "https://downloads.tatoeba.org/exports/per_language/tgl/tgl_sentences.tsv.bz2"
TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


def tokens(text: str) -> list[str]:
    return [token.replace("’", "'") for token in TOKEN.findall(unicodedata.normalize("NFC", text).lower())]


def main() -> None:
    SOURCE.mkdir(exist_ok=True)
    with urllib.request.urlopen(SENTENCE_URL) as response:
        sentence_compressed = response.read()

    counts: collections.Counter[str] = collections.Counter()
    sentences: list[str] = []
    for line in bz2.decompress(sentence_compressed).decode("utf-8").splitlines():
        line_tokens = tokens(line.rsplit("\t", 1)[-1])
        if line_tokens:
            sentences.append(" ".join(line_tokens))
            counts.update(line_tokens)
    if len(counts) < 1_000 or len(sentences) < 1_000:
        raise SystemExit(f"Filipino sources are unexpectedly thin ({len(counts)} words, {len(sentences)} sentences)")

    (SOURCE / "fil.txt").write_text(
        "".join(f"{word}\t{count:g}\n" for word, count in counts.most_common(50_000)), encoding="utf-8")
    (SOURCE / "fil_sentences.tsv").write_text("\n".join(sentences) + "\n", encoding="utf-8")
    (SOURCE / "fil.sources.json").write_text(json.dumps({
        "wordlist": {"name": "Frequency list derived from the Tatoeba Tagalog export", "url": SENTENCE_URL,
                     "license": "CC-BY-2.0-FR", "sha256": hashlib.sha256(sentence_compressed).hexdigest()},
        "sentences": {"name": "Tatoeba Tagalog sentence export (Filipino's grammatical base)", "url": SENTENCE_URL,
                      "license": "CC-BY-2.0-FR", "sha256": hashlib.sha256(sentence_compressed).hexdigest()},
        "derived": {"sentences": len(sentences), "words": len(counts),
                    "normalization": "Unicode letters plus internal apostrophes; punctuation, handles, URLs, emoji, and numbers removed"},
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(sentences):,} Filipino sentences and {len(counts):,} words from reviewed Tagalog sources.")


if __name__ == "__main__":
    main()
