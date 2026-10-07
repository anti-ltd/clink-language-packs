#!/usr/bin/env python3
"""Derive Roman Urdu typing data from Sharf's CC BY 4.0 UCI corpus.

The archive digest is pinned; a changed upstream download requires review.
Sentiment labels are never training input. Spellings remain corpus spellings,
including English code-switching, rather than transliterations of Urdu script.
"""
import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import unicodedata
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
URL = "https://archive.ics.uci.edu/static/public/458/roman%2Burdu%2Bdata%2Bset.zip"
SHA256 = "78e7cd1d7b0dc8e960a52c9151fc3114c70a3809111d3421581bbad931a6f5a8"
TOKEN = re.compile(r"(?<![\w@])[a-z]+(?:'[a-z]+)*(?!\w)")
WEB = re.compile(r"https?://\S+|www\.\S+|\S+@\S+|[@#]\w+", re.I)


def main():
    source = ROOT / "source"
    source.mkdir(exist_ok=True)
    with urllib.request.urlopen(URL, timeout=60) as response:
        raw = response.read()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise SystemExit("UCI archive changed; review the source before updating its digest")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        rows = csv.reader(io.StringIO(archive.read("Roman Urdu DataSet.csv").decode("utf-8-sig")))
        sentences = dict.fromkeys(
            " ".join(TOKEN.findall(WEB.sub(" ", unicodedata.normalize("NFC", row[0]).lower().replace("’", "'"))))
            for row in rows if row and row[0].strip()
        )
    sentences = [line for line in sentences if len(line.split()) >= 2]
    counts = collections.Counter(word for line in sentences for word in line.split())
    # Repeated observations provide a useful dictionary without promoting every
    # one-off social-media typo or name to a valid autocorrection candidate.
    words = [(word, count) for word, count in counts.most_common() if count >= 3 and (len(word) > 1 or word in {"a", "i"})]
    if len(sentences) < 10_000 or len(words) < 3_000:
        raise SystemExit("Unexpectedly small Roman Urdu corpus")
    (source / "ur_latn_sentences.tsv").write_text("\n".join(sentences) + "\n", encoding="utf-8")
    (source / "ur_latn.txt").write_text("".join(f"{word}\t{count}\n" for word, count in words), encoding="utf-8")
    receipt = {
        "corpus": {"name": "Roman Urdu Data Set", "author": "Zareen Sharf", "year": 2017,
                   "doi": "https://doi.org/10.24432/C58325", "url": URL,
                   "license": "CC-BY-4.0", "sha256": SHA256},
        "derived": {"sentences": len(sentences), "words": len(words), "tokens": sum(counts.values()),
                    "normalization": "Deduplicated Latin sentences; URLs, emails, handles, hashtags and numeric tokens removed; lowercase NFC; internal apostrophes preserved; dictionary minimum frequency 3"},
    }
    (source / "ur_latn.sources.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt["derived"], indent=2))


if __name__ == "__main__":
    main()
