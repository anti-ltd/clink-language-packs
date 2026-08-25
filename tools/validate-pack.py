#!/usr/bin/env python3
"""Check that a language pack has the files Clink can understand.

Usage: python3 tools/validate-pack.py tok
"""
import json
import pathlib
import struct
import sys

if len(sys.argv) != 2: raise SystemExit("Usage: python3 tools/validate-pack.py <code>")
code = sys.argv[1]
root = pathlib.Path("Lexicons")
lexicon, ngram = root / f"{code}.clex", root / f"{code}.cngm"
errors = []
if not lexicon.exists(): errors.append(f"Missing required {lexicon}.")
else:
    data = lexicon.read_bytes()
    if len(data) < 16 or data[:4] != b"CLEX" or struct.unpack_from("<I", data, 4)[0] != 1:
        errors.append(f"{lexicon} is not a CLEX version 1 dictionary.")
if ngram.exists():
    data = ngram.read_bytes()
    if len(data) < 12 or data[:4] != b"CNGM" or struct.unpack_from("<I", data, 4)[0] != 1:
        errors.append(f"{ngram} is not a CNGM version 1 next-word model.")
for suffix in ("bpevocab", "lmvocab", "cime"):
    path = root / f"{code}.{suffix}"
    if path.exists() and not path.read_bytes().strip(): errors.append(f"{path} is empty.")
emoji = root / f"{code}.emoji.json"
if emoji.exists():
    try:
        metadata = json.loads(emoji.read_text(encoding="utf-8"))
        if metadata.get("version") != 1: errors.append(f"{emoji} must use metadata version 1.")
        aliases = metadata.get("aliases")
        stopwords = metadata.get("stopwords")
        if not isinstance(aliases, dict) or not all(isinstance(k, str) and isinstance(v, list) and v and all(isinstance(w, str) and w.strip() for w in v) for k, v in aliases.items()):
            errors.append(f"{emoji} aliases must map emoji strings to non-empty string arrays.")
        if not isinstance(stopwords, list) or not all(isinstance(w, str) and w.strip() for w in stopwords):
            errors.append(f"{emoji} stopwords must be a string array.")
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{emoji} is not valid UTF-8 JSON: {error}")
model = root / f"{code}.mlmodelc"
if model.exists() and not model.is_dir(): errors.append(f"{model} must be a directory, not a single file.")
if model.exists() and not ((root / f"{code}.bpevocab").exists() or (root / f"{code}.lmvocab").exists()):
    errors.append("A neural model needs a matching .bpevocab or .lmvocab file.")
if errors:
    raise SystemExit("\n".join("ERROR: " + error for error in errors))
print(f"{code}: looks ready for release.")
