#!/usr/bin/env python3
"""Expand language-pack emoji metadata from official Unicode CLDR annotations.

Usage:
  python3 tools/expand-emoji-aliases.py /path/to/cldr/common

The supplied directory must contain ``annotations/`` and optionally
``annotationsDerived/``. Existing aliases stay first in each list, so any
carefully chosen pack-specific terms remain the preferred editorial wording.
CLDR's Unicode-3.0 licence applies to the source annotation data.
"""
import json
import pathlib
import sys
import xml.etree.ElementTree as etree

if len(sys.argv) != 2:
    raise SystemExit("Usage: python3 tools/expand-emoji-aliases.py /path/to/cldr/common")

common = pathlib.Path(sys.argv[1])
annotations = common / "annotations"
derived = common / "annotationsDerived"
root = pathlib.Path(__file__).resolve().parent.parent / "Lexicons"

# These pack codes deliberately share CLDR's base-language annotations.
cldr_code = {"es_mx": "es", "pt_br": "pt"}
tone_modifiers = set(range(0x1F3FB, 0x1F400))

def neutral(emoji):
    return "".join(c for c in emoji if ord(c) != 0xFE0F and ord(c) not in tone_modifiers)

def keyboard_emoji():
    # Restrict metadata to Clink's neutral keyboard glyphs. This mirrors the
    # generator used by the app, including its exclusion of skin-tone variants.
    source = pathlib.Path(__file__).resolve().parents[3] / "Tools" / "emoji-test.txt"
    glyphs = set()
    for line in source.read_text(encoding="utf-8").splitlines():
        if "; fully-qualified" not in line or "#" not in line:
            continue
        points = [int(point, 16) for point in line.split(";", 1)[0].strip().split()]
        if any(point in tone_modifiers for point in points):
            continue
        glyph = "".join(chr(point) for point in points)
        glyphs.add(neutral(glyph))
    return glyphs

allowed = keyboard_emoji()

def annotations_for(code):
    values = {}
    for directory in (annotations, derived):
        path = directory / f"{code}.xml"
        if not path.exists():
            continue
        document = etree.parse(path)
        for element in document.findall(".//annotation"):
            if element.get("type") == "tts":
                continue
            emoji = neutral(element.get("cp", ""))
            if emoji not in allowed or not element.text:
                continue
            words = [word.strip() for word in element.text.split("|") if word.strip()]
            values.setdefault(emoji, []).extend(words)
    return values

changed = 0
for path in sorted(root.glob("*.emoji.json")):
    # macOS may leave AppleDouble sidecars beside copied assets. They are ignored
    # by Git and are never release inputs.
    if path.name.startswith("._"):
        continue
    pack = json.loads(path.read_text(encoding="utf-8"))
    source_code = cldr_code.get(path.stem.removesuffix(".emoji"), path.stem.removesuffix(".emoji"))
    cldr = annotations_for(source_code)
    if not cldr:
        raise SystemExit(f"No CLDR annotations found for {path.stem} ({source_code}).")
    aliases = pack["aliases"]
    expanded = {}
    for emoji in sorted(set(aliases) | set(cldr)):
        # Keep the pack's hand-written choices first, followed by official CLDR
        # terms. De-duplicate without changing the source's natural spelling.
        words = aliases.get(emoji, []) + cldr.get(emoji, [])
        expanded[emoji] = list(dict.fromkeys(word for word in words if word.strip()))
    pack["aliases"] = expanded
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{path.name}: {len(expanded)} emoji aliases")
    changed += 1

print(f"Expanded {changed} emoji metadata files from Unicode CLDR annotations.")
