#!/usr/bin/env python3
"""Validate the machine-readable language-wave release catalogue."""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "catalog/language-wave.json"
CODE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")

def main():
    data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
    errors, seen = [], set()
    for group in ("packs", "imes"):
        for item in data.get(group, []):
            code, status = item.get("code"), item.get("status")
            if not isinstance(code, str) or not CODE.fullmatch(code) or code in seen: errors.append(f"invalid or duplicate code: {code!r}")
            seen.add(code)
            if status not in {"complete", "blocked"}: errors.append(f"{code}: status must be complete or blocked")
            if status == "blocked" and (not item.get("missing") or not item.get("next")): errors.append(f"{code}: blocked entry needs missing and next")
            if status == "complete":
                required = ROOT / "Lexicons" / f"{code}.clex"
                if group == "packs" and not required.exists(): errors.append(f"{code}: complete pack lacks {required.relative_to(ROOT)}")
                if group == "imes" and not (ROOT / "Lexicons" / f"{code}.cime").exists(): errors.append(f"{code}: complete IME lacks cime")
    if errors: raise SystemExit("\n".join(errors))
    complete = sum(x["status"] == "complete" for x in data["packs"] + data["imes"])
    blocked = sum(x["status"] == "blocked" for x in data["packs"] + data["imes"])
    print(f"catalogue valid: {complete} complete, {blocked} blocked")
if __name__ == "__main__": main()
