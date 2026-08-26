#!/usr/bin/env python3
import json, pathlib
root = pathlib.Path(__file__).resolve().parents[1]
data = json.loads((root / "catalog/language-wave.json").read_text())
blocked = [entry["code"] for group in ("packs", "imes") for entry in data[group] if entry["status"] == "blocked"]
print("blocked language-wave entries: " + ", ".join(blocked))
