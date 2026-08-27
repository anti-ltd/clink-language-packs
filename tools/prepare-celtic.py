#!/usr/bin/env python3
"""Fetch licensed Tatoeba Celtic sentence exports and derive pack inputs."""
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
LANGUAGES = {
    "gd": ("gla", "Scottish Gaelic"),
    "cy": ("cym", "Welsh"),
}
# Unicode letters, with an optional internal straight/curly apostrophe. This
# intentionally strips names, URLs, emoji, numbers, and punctuation rather
# than letting social/export metadata leak into the lexicon.
TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)


def prepare(code: str, tatoeba_code: str, name: str) -> None:
    url = f"https://downloads.tatoeba.org/exports/per_language/{tatoeba_code}/{tatoeba_code}_sentences.tsv.bz2"
    with urllib.request.urlopen(url) as response:
        compressed = response.read()
    raw = bz2.decompress(compressed).decode("utf-8")
    sentences: list[str] = []
    counts: collections.Counter[str] = collections.Counter()
    for line in raw.splitlines():
        text = unicodedata.normalize("NFC", line.rsplit("\t", 1)[-1]).lower()
        tokens = [token.replace("’", "'") for token in TOKEN.findall(text)]
        if not tokens:
            continue
        sentences.append(" ".join(tokens))
        counts.update(tokens)
    if len(sentences) < 100:
        raise SystemExit(f"{name}: Tatoeba export produced only {len(sentences)} usable sentences")
    (SOURCE / f"{code}_sentences.tsv").write_text("\n".join(sentences) + "\n", encoding="utf-8")
    (SOURCE / f"{code}.txt").write_text(
        "".join(f"{word}\t{count}\n" for word, count in counts.most_common(50_000)), encoding="utf-8")
    (SOURCE / f"{code}.sources.json").write_text(json.dumps({
        "corpus": {"name": f"Tatoeba {name} sentence export", "url": url,
                   "license": "CC-BY-2.0-FR", "sha256": hashlib.sha256(compressed).hexdigest()},
        "derived": {"sentences": len(sentences), "words": len(counts),
                    "normalization": "Unicode letters plus internal apostrophes; URLs, handles, emoji, punctuation, and numbers removed"},
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(sentences):,} {name} sentences and {len(counts):,} words from Tatoeba.")


def main() -> None:
    SOURCE.mkdir(exist_ok=True)
    for code, (tatoeba_code, name) in LANGUAGES.items():
        prepare(code, tatoeba_code, name)


if __name__ == "__main__":
    main()
