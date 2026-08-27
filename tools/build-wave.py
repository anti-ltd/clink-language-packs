#!/usr/bin/env python3
"""Build only reviewed, complete language-wave packs from checked source inputs."""
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]; catalog = json.loads((ROOT / "catalog/language-wave.json").read_text())
train = "--train" in sys.argv
for item in catalog["packs"]:
    if item["status"] != "complete": continue
    code = item["code"]; words = ROOT / "source" / f"{code}.txt"; sentences = ROOT / "source" / f"{code}_sentences.tsv"
    if not words.exists() or not sentences.exists(): raise SystemExit(f"{code}: complete catalogue entry is missing reviewed source inputs")
    subprocess.run([sys.executable, "build-pack.py", code, str(words)], cwd=ROOT, check=True)
    if item.get("nextWordModel", True):
        subprocess.run([sys.executable, "tools/build-next-word.py", code, str(words), str(sentences)], cwd=ROOT, check=True)
    else:
        (ROOT / "Lexicons" / f"{code}.cngm").unlink(missing_ok=True)
    model = ROOT / "Lexicons" / f"{code}.mlmodelc"
    vocab = ROOT / "Lexicons" / f"{code}.bpevocab"
    # Complete wave packs train neural ranking by default.  An explicit false is
    # reserved for a deliberately lexicon-only pack; using model.is_dir() here
    # would silently skip a missing model forever.
    if train and item.get("neural", True) and (os.environ.get("FORCE_RETRAIN") == "1" or not model.is_dir() or not vocab.exists()):
        # BPE is explicit so a model can never be paired with a legacy word vocab.
        subprocess.run([sys.executable, "tools/train-neural.py", "--lang", code, "--bpe", "12000"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "tools/validate-pack.py", code], cwd=ROOT, check=True)
