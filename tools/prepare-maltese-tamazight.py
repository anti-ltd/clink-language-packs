#!/usr/bin/env python3
"""Derive Maltese and Standard Moroccan Tamazight inputs from licensed sources."""
import bz2, collections, hashlib, io, json, pathlib, re, unicodedata, urllib.request
import zstandard
ROOT = pathlib.Path(__file__).resolve().parents[1]; SOURCE = ROOT / "source"
LANGUAGES = {"mt": ("mlt", "Maltese"), "zgh": ("zgh", "Standard Moroccan Tamazight")}
TOKEN = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)

HPLT_MALTESE = "https://data.hplt-project.org/three/sorted/mlt_Latn/10_1.jsonl.zst"

def words(text):
    return [x.replace("’", "'") for x in TOKEN.findall(unicodedata.normalize("NFC", text).lower())]

def hplt_maltese_sentences():
    """Read HPLT's top-quality Maltese shard without retaining the corpus."""
    compressed = urllib.request.urlopen(HPLT_MALTESE).read()
    decoded = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(compressed)).read().decode("utf-8")
    sentences = []
    for row in decoded.splitlines():
        text = json.loads(row).get("text", "")
        sentences.extend(" ".join(words(line)) for line in text.splitlines() if words(line))
    return compressed, sentences
def main():
    SOURCE.mkdir(exist_ok=True)
    for code, (tag, name) in LANGUAGES.items():
        url = f"https://downloads.tatoeba.org/exports/per_language/{tag}/{tag}_sentences.tsv.bz2"
        with urllib.request.urlopen(url) as r: compressed = r.read()
        counts, sentences = collections.Counter(), []
        for row in bz2.decompress(compressed).decode("utf-8").splitlines():
            tokens = words(row.rsplit("\t", 1)[-1])
            if tokens: sentences.append(" ".join(tokens)); counts.update(tokens)
        sources = [{"name":f"Tatoeba {name} sentence export", "url":url, "license":"CC-BY-2.0-FR", "sha256":hashlib.sha256(compressed).hexdigest()}]
        if code == "mt":
            hplt, additional = hplt_maltese_sentences()
            sentences.extend(additional)
            for sentence in additional: counts.update(sentence.split())
            sources.append({"name":"HPLT 3.0 Maltese top-quality shard", "url":HPLT_MALTESE, "license":"CC0-1.0", "sha256":hashlib.sha256(hplt).hexdigest()})
        (SOURCE / f"{code}.txt").write_text("".join(f"{w}\t{n}\n" for w,n in counts.most_common(50_000)), encoding="utf-8")
        (SOURCE / f"{code}_sentences.tsv").write_text("\n".join(sentences)+"\n", encoding="utf-8")
        (SOURCE / f"{code}.sources.json").write_text(json.dumps({"corpora":sources,"derived":{"sentences":len(sentences),"words":len(counts)}},indent=2)+"\n",encoding="utf-8")
        print(f"Prepared {len(sentences):,} {name} sentences and {len(counts):,} words.")
if __name__ == "__main__": main()
