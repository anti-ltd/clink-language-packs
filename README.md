<p align="center">
  <img src="https://raw.githubusercontent.com/anti-ltd/clink-language-packs/main/icon-1024.png" width="96" alt="Clink app icon">
</p>

<h1 align="center">Clink language packs</h1>

<p align="center">Open language resources for Clink keyboards.</p>

Clink ships English in the app, then downloads the languages you choose. A pack contains its lexicon, prediction data, optional emoji metadata, and where available its neural model or input-method tables. Everything stays on the device once installed.

## Official Clink repositories

[Language packs](https://github.com/anti-ltd/clink-language-packs) · [Layouts](https://github.com/anti-ltd/clink-layouts) · [Profiles](https://github.com/anti-ltd/clink-profiles) · [Themes](https://github.com/anti-ltd/clink-themes) · [Panels](https://github.com/anti-ltd/clink-panels) · [Actions](https://github.com/anti-ltd/clink-actions) · [Fonts](https://github.com/anti-ltd/clink-fonts) · [Sounds](https://github.com/anti-ltd/clink-sounds)

## Included languages

| | | |
|---|---|---|
| 🇿🇦 Afrikaans ★★★★★ | 🇸🇦 Arabic ★★★★★ | 🇦🇲 Armenian ★★★★★ |
| 🇧🇬 Bulgarian ★★★★★ | 🇨🇳 Chinese ★★★★★ | 🇭🇷 Croatian ★★★★★ |
| 🇨🇿 Czech ★★★★★ | 🇳🇱 Dutch ★★★★★ | 🇺🇸 English ★★★★★ |
| 🇪🇪 Estonian ★★★★★ | 🇫🇷 French ★★★★★ | 🇩🇪 German ★★★★★ |
| 🇬🇷 Greek ★★★★★ | 🇮🇳 Hindi ★★★★★ | 🇭🇺 Hungarian ★★★★★ |
| 🇮🇩 Indonesian ★★★★★ | 🇮🇹 Italian ★★★★★ | 🇯🇵 Japanese ★★★★★ |
| 🇰🇷 Korean ★★★★★ | 🇱🇺 Luxembourgish ★★★★★ | 🇱🇹 Lithuanian ★★★★★ |
| 🇲🇾 Malay ★★★★★ | 🇲🇽 Mexican Spanish ★★★★★ | 🇳🇵 Nepali ★★★★★ |
| 🇨🇼 Papiamento ★★★★★ | 🇵🇱 Polish ★★★★★ | 🇵🇹 Portuguese ★★★★★ |
| 🇧🇷 Brazilian Portuguese ★★★★★ | 🇷🇴 Romanian ★★★★★ | 🇷🇺 Russian ★★★★★ |
| 🇷🇸 Serbian ★★★★★ | 🇪🇸 Spanish ★★★★★ | 🇹🇷 Turkish ★★★★★ |
| 🇺🇦 Ukrainian ★★★★★ | 🇻🇳 Vietnamese ★★★★★ | 🇦🇱 Albanian ★★★★★ |
| 🇦🇲 Amharic ★★★ | 🇦🇿 Azerbaijani ★★★ | 🇧🇦 Bosnian ★★★ |
| 🇧🇩 Bengali ★★★★★ | 🇧🇾 Belarusian ★★★ | 🇨🇦 Catalan ★★★★★ |
| 🇩🇰 Danish ★★★★★ | 🇪🇸 Basque ★★★★★ | 🇫🇮 Finnish ★★★★★ |
| 🇬🇪 Georgian ★★★ | 🇬🇱 Galician ★★★★★ | 🇬🇹 Gujarati ★★★ |
| 🇮🇱 Hebrew ★★★★★ | 🇮🇳 Kannada ★★★ | 🇮🇳 Marathi ★★★ |
| 🇰🇭 Khmer ★★ | 🇰🇿 Kazakh ★★★ | 🇱🇦 Lao ★★ |
| 🇱🇻 Latvian ★★★★★ | 🇮🇳 Malayalam ★★★ | 🇲🇲 Burmese ★★ |
| 🇲🇰 Macedonian ★★★★★ | 🇳🇴 Norwegian Bokmål ★★★★★ | 🇳🇴 Norwegian Nynorsk ★★★ |
| 🇮🇷 Persian ★★★★★ | 🇮🇳 Punjabi (Gurmukhi) ★★★ | 🇸🇮 Sinhala ★★★ |
| 🇸🇮 Slovenian ★★★★★ | 🇸🇰 Slovak ★★★★★ | 🇸🇪 Swedish ★★★★★ |
| 🇹🇭 Thai ★★★★ | 🇮🇳 Tamil ★★★ | 🇮🇳 Telugu ★★★ |
| 🇵🇭 Tagalog ★★★★★ | 🇹🇿 Swahili ★★★ | 🇵🇰 Urdu ★★★ |

**Pack-depth key:** ★★★★★ dictionary + next-word model + neural model; ★★★★ dictionary + neural model; ★★★ dictionary + next-word model; ★★ dictionary only. Ratings describe shipped on-device assets, not the importance, quality, or fluency of a language.

Emoji metadata is optional for every pack, including the language wave, but recommended because it lets the predictive bar recognize local words and phrases such as animal names, feelings, and country names.

## Make your first pack

You do **not** need to understand machine learning, binary files, or GitHub releases to publish a useful language. Start with the dictionary. It is the only required asset.

1. Fork this repository. Name your copy something clear, such as `toki-pona-clink`.
2. Create `source/tok.txt`. `tok` is the language code used everywhere below. Use short lowercase codes. Regional variants use an underscore, such as `pt_br`.
3. Put one word on each line. This is a complete, valid starting list:

   ```text
   jan
   pona
   suli
   toki
   ```

4. In the repository folder on your Mac, run:

   ```sh
   python3 build-pack.py tok source/tok.txt
   python3 tools/validate-pack.py tok
   ```

   You now have `Lexicons/tok.clex`. That is Clink's compact dictionary. You never write a `.clex` file yourself.
5. Run `./update.sh` when you are ready to publish. It commits your changes, creates a version tag, and pushes it. GitHub Actions builds the release manifest, calculates every SHA-256 hash and file size, then publishes the files.
6. In Clink, open **General → Repositories**, add your public GitHub URL, then visit **Languages**. Your language appears under **Community**.

That is enough to ship. Add the optional assets below when you have the data and a reason to use them.

## Which files do I need?

| File | What it gives people | Do I need it? |
|---|---|---|
| `<code>.clex` | Dictionary words, completions, spelling help | Yes |
| `<code>.emoji.json` | Localized emoji aliases and phrase stopwords | Recommended |
| `<code>.cngm` | Better next-word suggestions from real sentences | Recommended when you have a sentence corpus |
| `<code>.bpevocab` + `<code>.mlmodelc` | Neural ranking that uses more of the sentence context | Optional and advanced |
| `<code>.cime` | Reading-to-character conversion, such as Pinyin → Hanzi | Only for an IME language |

Everything lives in `Lexicons/`. The filename must begin with the same code: a Japanese pack uses `ja.clex`, `ja.emoji.json`, `ja.cngm`, and, if applicable, `ja.cime`.

## Language-wave catalogue

`catalog/language-wave.json` is the release authority for the pending language
wave. It records the source URL, licence, required source files, and next action
for every pack and IME. A `blocked` entry is intentionally absent from releases;
it becomes `complete` only after its checked source inputs have been reviewed and
the generated assets pass `tools/validate-pack.py`. Validate the catalogue with:

```sh
python3 tools/validate-catalog.py
```

`tools/prepare-wave.py <code>` records source SHA-256 receipts under `source/`.
Those downloads are ignored because they are reproducible raw inputs, not release
assets. `tools/build-wave.py --train` builds reviewed entries and preserves an
existing neural model unless `FORCE_RETRAIN=1` is set.

The current wave has 37 completed direct-language packs. Five IME entries remain
intentionally blocked: `zh_hant_pinyin`, `zh_hant_zhuyin`, `zh_hant_wubi`,
`yue_jyutping`, and `ja_romaji`. They require a redistributable reading/code to
candidate source *and* an input-composition recipe that preserves the intended
writing system; a generic word list, Simplified-Chinese table, or neighbouring
language table is not an acceptable substitute. Their exact source and
implementation requirements live in the catalogue. Do not publish a placeholder
`.cime` table simply to make an IME appear available.

## Add emoji metadata

Emoji metadata is language-pack data, not Clink application code. Add it at:

```text
Lexicons/<code>.emoji.json
```

Clink merges the metadata with Unicode emoji names and its built-in CLDR keyword tables. The same file works for bundled development resources and downloaded releases. Adding aliases for a language must not require a Swift change in Clink.

The file uses version 1 of this schema:

```json
{
  "version": 1,
  "aliases": {
    "🐔": ["chicken", "hen"],
    "🐦": ["bird"],
    "🇻🇳": ["việt nam", "vietnam"]
  },
  "stopwords": ["the", "and", "with"]
}
```

### `aliases`

`aliases` maps a neutral emoji glyph to the words users type in that language. Use the actual emoji character as the key. Do not use skin-tone variants or variation-selector variants as separate keys; Clink normalizes those forms to the neutral glyph.

Include common local words first, then useful international synonyms when they are genuinely used by speakers. Multi-word aliases are supported. Keep aliases focused on the emoji's meaning rather than adding broad or ambiguous words that would make the predictive bar noisy.

Country names can be included as aliases for their flag. This is especially useful when the system locale does not provide the localized country name through `Locale`.

### `stopwords`

`stopwords` contains language function words that should not trigger emoji suggestions on their own or dominate short phrases. Examples include articles, conjunctions, pronouns, and common prepositions.

These values are normalized for case and diacritics before matching. Store the natural language spelling in the file, including accents or tone marks where appropriate.

### Authoring guidance

Start with a small, high-confidence set:

- smile, laugh, love, fire, and a few common reactions
- dog, cat, bird, chicken, fish, and other everyday animals
- the language's main country or region names
- the most common function words as stopwords

Expand the list from real language usage and review every alias for ambiguity. Do not copy machine-generated translations into a release without checking them with a native speaker or a trusted linguistic source. State the source and licence in the pack's change description when the data comes from a third-party corpus.

Validate the metadata together with the dictionary:

```sh
python3 tools/validate-pack.py vi
```

The validator checks the required `.clex`, optional binary resources, neural-model pairing, JSON encoding, metadata version, alias shape, and stopword shape. Run it once for every language code you add or change.

## Add next-word prediction

A dictionary knows individual words. A next-word model learns that after “thank” people often type “you”. It needs real sentences, not a list of isolated words.

1. Create `source/tok.sentences.txt` and put one complete sentence on each line. Punctuation is fine.

   ```text
   jan li toki.
   mi toki e toki pona.
   sina pona.
   ```

2. Run this exact command:

   ```sh
   python3 tools/build-next-word.py tok source/tok.txt source/tok.sentences.txt
   python3 tools/validate-pack.py tok
   ```

It makes `Lexicons/tok.cngm`. The tool only includes pairs made from words already in `source/tok.txt`, which keeps the model matched to its dictionary. Use a corpus you are allowed to redistribute or process. More varied, natural sentences make better suggestions.

## Add an input method table

Use this only when people type a phonetic reading and choose a different written form. Japanese kana-to-Kanji and Chinese Pinyin-to-Hanzi are the common examples. It is not needed for ordinary alphabetic languages.

1. Create `source/ja-ime.tsv`. Each line is a reading, followed by one or more choices. Press the **Tab** key between columns, not spaces. Put the most likely choice first.

   ```text
   とうきょう	東京
   かんじ	漢字	感じ
   ```

2. Build it:

   ```sh
   python3 tools/build-ime-table.py ja source/ja-ime.tsv
   python3 tools/validate-pack.py ja
   ```

This makes `Lexicons/ja.cime`. Clink shows at most the first 16 choices per reading, in the order you give them.

## Add a neural model

This is optional. Do it only after the dictionary, emoji metadata, and `.cngm` model feel good. Training needs a Mac, Xcode command-line tools, Python 3, a large sentence corpus, free disk space, and usually hours of processing. The output is two matching assets: the compiled Core ML model folder and its vocabulary. Never copy a vocabulary from one training run beside a model from another.

1. Put one sentence per line in `source/tok_sentences.tsv`. The filename has an underscore here because it is the neural trainer's convention. The file can be plain sentences; a Tatoeba-style tab-separated export also works because the final column is treated as the sentence.
2. Install the training requirements once:

   ```sh
   python3 -m pip install torch coremltools
   ```

3. Train a small test model first. This checks your setup without waiting for the entire corpus:

   ```sh
   python3 tools/train-neural.py --lang tok --bpe 8000 --epochs 1 --max-lines 10000
   ```

4. When that succeeds, train the real model. `12000` is a sensible choice for a large corpus; `8000` is safer for a small one.

   ```sh
   python3 tools/train-neural.py --lang tok --bpe 12000 --epochs 3
   python3 tools/validate-pack.py tok
   ```

The tool writes `Lexicons/tok.mlmodelc/` and `Lexicons/tok.bpevocab`. Keep both. Do not rename, edit, or mix them. If the training step is too much for your project, skip it: Clink still works with the dictionary, emoji metadata, and next-word model.

## Add your repository to Clink

After the GitHub Action publishes your first release, open **General → Repositories** in Clink and enter `owner/repository`, for example `your-name/toki-pona-clink`. Then open **Languages**. Your packs appear in **Community**, separate from Clink's own packs. Clink never bundles, recommends, or silently adds community repositories.

## Make a language pack with an AI agent

[`PROMPT.md`](PROMPT.md) is a ready-to-use brief for an AI coding agent. Fork the repository, open the fork in your agent, and say:

```text
Read PROMPT.md and create a language pack for [language and locale], starting with this word-list source: [describe or provide it].
```

The prompt starts with a generated dictionary—the only required asset—and adds emoji metadata, prediction, IME, or neural assets only when the requested language and licensed source data warrant them. Review the language data, quality, and licensing before publishing.

## What Clink verifies

Clink only accepts public HTTPS GitHub release manifests. It derives the manifest address from the repository URL, so a repository cannot point the app at an unrelated host. Every download must come from that same GitHub repository's release, use an approved language-pack file type, stay within size limits, match the manifest's byte count, and match its SHA-256 hash.

Files are downloaded into a staging directory. Clink activates a pack only after every file has passed verification and the required `.clex` file exists. If a release fails at any point, the previous verified pack remains active.

Emoji metadata is optional at install time. A pack without `<code>.emoji.json` still works with Unicode names and Clink's built-in CLDR tables; a pack with it adds language-specific aliases and phrase filtering at runtime.

Adding a repository is still a trust decision. Only add repositories run by people or communities you trust to publish language data.

## Publishing is automatic

Keep `Lexicons/`, `tools/`, and `.github/workflows/` in your fork. Build or update a language pack, add or update `<code>.emoji.json` with the same code prefix as the dictionary, run the validation tools, and push to `main`. GitHub Actions includes every `Lexicons/<code>.*` asset in the release manifest, calculates its SHA-256 hash and byte count, and publishes the verified files.
