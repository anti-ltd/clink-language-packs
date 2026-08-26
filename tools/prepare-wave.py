#!/usr/bin/env python3
"""Fetch catalogue-approved language-wave sources and record SHA-256 receipts."""
import bz2, collections, hashlib, json, os, pathlib, re, shutil, sys, unicodedata, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]; SOURCE = ROOT / "source"
catalogue = json.loads((ROOT / "catalog/language-wave.json").read_text())
requested = set(sys.argv[1:] or [x["code"] for x in catalogue["packs"]])

def fetch(url, output):
    with urllib.request.urlopen(url) as response, output.open("wb") as target: shutil.copyfileobj(response, target)
    return hashlib.sha256(output.read_bytes()).hexdigest()

def derive_frequency(sentences, output):
    counts = collections.Counter()
    for raw in sentences.read_text(encoding="utf-8").splitlines():
        text = raw.rsplit("\t", 1)[-1].lower()
        for token in re.findall(r"[^\s.,!?;:\"“”‘’()\[\]{}]+", text):
            token = unicodedata.normalize("NFC", token.strip("'’-"))
            if any(ch.isalpha() for ch in token): counts[token] += 1
    if not counts: raise ValueError("sentence corpus produced no lexical tokens")
    output.write_text("".join(f"{word}\t{count}\n" for word, count in counts.most_common(50_000)), encoding="utf-8")

failures = []
for item in catalogue["packs"]:
    code = item["code"]
    if code not in requested: continue
    if item["status"] != "blocked": continue
    if not item["sources"]: print(f"{code}: blocked: {item['next']}", file=sys.stderr); continue
    SOURCE.mkdir(exist_ok=True)
    word, compressed = SOURCE / f"{code}.txt", SOURCE / f".{code}.tsv.bz2"
    try:
        sentence_url = item["sources"][-1]
        sentence_hash = fetch(sentence_url, compressed)
        with bz2.open(compressed, "rb") as raw, (SOURCE / f"{code}_sentences.tsv").open("wb") as out: shutil.copyfileobj(raw, out)
        compressed.unlink()
        try:
            if os.environ.get("DERIVE_FREQUENCY") == "1": raise ValueError("forced derivation")
            if len(item["sources"]) < 2: raise ValueError("no standalone frequency source")
            word_hash = fetch(item["sources"][0], word)
            word_source = item["sources"][0]
        except Exception:
            derive_frequency(SOURCE / f"{code}_sentences.tsv", word)
            word_hash = hashlib.sha256(word.read_bytes()).hexdigest()
            word_source = sentence_url + " (derived frequency list)"
        (SOURCE / f"{code}.sources.json").write_text(json.dumps({"wordlist": {"url": word_source, "sha256": word_hash}, "sentences": {"url": sentence_url, "sha256": sentence_hash}}, indent=2) + "\n")
        print(f"{code}: acquired; review the corpus then set catalogue status complete")
    except Exception as error:
        word.unlink(missing_ok=True); compressed.unlink(missing_ok=True)
        failures.append(f"{code}: {error}")
if failures:
    print("\n".join(failures), file=sys.stderr)
    raise SystemExit(1)
