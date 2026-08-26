#!/usr/bin/env python3
"""Build a release manifest and assets for complete packs only."""
import hashlib, json, pathlib, shutil, sys

def release_file(path):
    return path.is_file() and not path.name.startswith("._") and path.name != ".DS_Store"

def neural_metadata(code, source, lexicons):
    vocab = lexicons / f"{code}.bpevocab"
    model = lexicons / f"{code}.mlmodelc"
    if not model.is_dir() or not vocab.is_file(): return None
    lines = vocab.read_text(encoding="utf-8").splitlines()
    if len(lines) < 3 or lines[0] != "BPE1": raise SystemExit(f"{code}: invalid BPE vocabulary")
    vocabulary_size = int(lines[1]); merge_index = 2 + vocabulary_size
    if merge_index >= len(lines): raise SystemExit(f"{code}: truncated BPE vocabulary")
    sentence_path = source / f"{code}_sentences.tsv"
    # Historical packs predate this manifest field and may not retain their raw
    # training corpus in the release checkout. They remain publishable; new wave
    # packs always carry reviewed sources and therefore get self-describing data.
    if not sentence_path.is_file(): return None
    return {"format": "bpe", "sentenceCount": sum(1 for _ in sentence_path.open(encoding="utf-8")), "vocabularySize": vocabulary_size, "bpeMerges": int(lines[merge_index]), "modelVersion": "1"}

if len(sys.argv) != 4: raise SystemExit("usage: build-release-manifest.py VERSION OWNER/REPO OUT")
version, repository, out = sys.argv[1:]
root = pathlib.Path(__file__).resolve().parents[1]; lexicons = root / "Lexicons"; source = root / "source"; output = pathlib.Path(out); assets = output / "assets"
catalogue = json.loads((root / "catalog/language-wave.json").read_text())
blocked = {x["code"] for x in catalogue["packs"] + catalogue["imes"] if x["status"] == "blocked"}
packs = []
for clex in sorted(path for path in lexicons.glob("*.clex") if not path.name.startswith("._")):
    code = clex.stem
    if code in blocked: raise SystemExit(f"blocked language {code} has release asset")
    entries = []
    for path in sorted(lexicons.glob(code + ".*")):
        for file in (path.rglob("*") if path.is_dir() else [path]):
            if not release_file(file): continue
            relative = file.relative_to(lexicons).as_posix(); name = code + "--" + relative.replace("/", "--")
            target = assets / name; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(file, target)
            data = target.read_bytes(); entries.append({"path": relative, "url": f"https://github.com/{repository}/releases/download/{version}/{name}", "sha256": hashlib.sha256(data).hexdigest(), "byteCount": len(data)})
    pack = {"code": code, "version": version, "assets": entries}
    if neural := neural_metadata(code, source, lexicons): pack["neural"] = neural
    packs.append(pack)
output.mkdir(parents=True, exist_ok=True)
(output / "manifest.json").write_text(json.dumps({"version": version, "packs": packs}, separators=(",", ":")), encoding="utf-8")
