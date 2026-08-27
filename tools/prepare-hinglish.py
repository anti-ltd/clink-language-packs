#!/usr/bin/env python3
"""Fetch the reviewed PHINC corpus and derive Clink's Hinglish train inputs.

PHINC is a CC BY 4.0 corpus of human-annotated, Romanized Hindi-English social
media sentences.  The revision is pinned so the generated source receipt is
reproducible even if the dataset's main branch changes.
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

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "source"
REVISION = "44b5471df75e508b9d6fcdbcc93df04bb1e84056"
URL = f"https://huggingface.co/datasets/LingoIITGN/PHINC/resolve/{REVISION}/PHINC.csv"
# Roman Hindi is non-standard, but Hinglish is typed with Latin letters.  Keep
# apostrophes inside English contractions and discard handles, URLs, emoji,
# hashtags, and numeric-only fragments rather than teaching them as words.
TOKEN = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*")


def main() -> None:
    SOURCE.mkdir(exist_ok=True)
    with urllib.request.urlopen(URL) as response:
        raw = response.read()
    source_hash = hashlib.sha256(raw).hexdigest()

    sentences: list[str] = []
    counts: collections.Counter[str] = collections.Counter()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if "Sentence" not in (reader.fieldnames or []):
        raise SystemExit("PHINC revision has no Sentence column")
    for row in reader:
        text = unicodedata.normalize("NFC", row["Sentence"] or "").lower()
        tokens = [token.replace("’", "'") for token in TOKEN.findall(text)]
        if not tokens:
            continue
        sentences.append(" ".join(tokens))
        counts.update(tokens)
    if len(sentences) < 1_000:
        raise SystemExit(f"PHINC produced only {len(sentences)} usable sentences")

    (SOURCE / "hi_latn_sentences.tsv").write_text(
        "\n".join(sentences) + "\n", encoding="utf-8")
    (SOURCE / "hi_latn.txt").write_text(
        "".join(f"{word}\t{count}\n" for word, count in counts.most_common(50_000)),
        encoding="utf-8")
    (SOURCE / "hi_latn.sources.json").write_text(json.dumps({
        "corpus": {
            "name": "PHINC: Parallel Hinglish Social Media Code-Mixed Corpus",
            "url": URL,
            "revision": REVISION,
            "license": "CC-BY-4.0",
            "sha256": source_hash,
        },
        "derived": {
            "sentences": len(sentences),
            "words": len(counts),
            "normalization": "Latin words plus internal apostrophes; handles, URLs, emoji, hashtags, and numeric fragments removed",
        },
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(sentences):,} Hinglish sentences and {len(counts):,} words from PHINC.")


if __name__ == "__main__":
    main()
