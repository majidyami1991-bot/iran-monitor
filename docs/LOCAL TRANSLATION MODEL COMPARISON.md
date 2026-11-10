# Local translation model comparison — English → Persian (2026-10-09)

**Final status: `BLOCKED_MODEL_QUALITY`.** None of the four local models
meets the acceptance bar for publishing machine translations:

- TranslateGemma 4B (ردشده — rejected earlier)
- TranslateGemma 12B (ردشده — rejected earlier)
- MADLAD-400-3B-MT (new, **rejected**)
- NLLB-200-distilled-600M (new, **rejected**)

The acceptance bar is: no critical error, no invented information, and all
critical fixtures correct. No model was activated or approved, nothing was
written to the database, and Production, OpenCTI and Assistant v1.3.1 are
unchanged.

## 1. Models

| | TranslateGemma 4B | TranslateGemma 12B | **MADLAD-400-3B-MT** | **NLLB-200-distilled-600M** |
|---|---|---|---|---|
| Publisher / license | Google / Gemma Terms | Google / Gemma Terms | Google / **Apache-2.0** | Meta / **CC-BY-NC-4.0** (non-commercial; owner confirmed internal non-commercial use) |
| Architecture | Gemma 3 decoder (LLM) | Gemma 3 decoder (LLM) | T5 encoder-decoder (dedicated MT, 400+ languages) | M2M100 encoder-decoder (dedicated MT, 200 languages) |
| Persian code | prompt `fa-IR` | prompt `fa-IR` | `<2fa>` | `pes_Arab` |
| Runtime here | Ollama 0.40.1 / llama.cpp, Q4_K_M | Ollama 0.40.1 / llama.cpp, Q4_K_M | **CTranslate2 4.8.1, int8, beam 4, 8 threads** (Windows host) | **CTranslate2 4.8.1, int8, beam 4, 8 threads** (Windows host) |
| Can run in the current Ollama setup | yes | yes | no (encoder-decoder) | no (encoder-decoder) |
| Download | 3.3 GB | 8.1 GB | 11.76 GB safetensors | 2.46 GB `pytorch_model.bin` (pickle; loaded with `weights_only`) |
| Model executed | — | — | int8 `model.bin` 2.95 GB | int8 `model.bin` 0.62 GB |

### Identity of the new models (verified)

Both models were fetched once, from the official Hugging Face repositories
at pinned commits, by `scripts/nmt_fetch_models.py`. All 15 files were
downloaded. Every file with a published hash matched its pinned SHA-256, and
the hashes of the small configuration files were recorded
(`runtime/local-ai-evidence/phase6/nmt-fetch.json`). The MADLAD transfer
stalled once at 3.96 GB and was resumed once by hand from the partial file;
the final hash matched.

| Model | Commit | File | Bytes | SHA-256 |
|---|---|---|---|---|
| google/madlad400-3b-mt | `fa184c675da0b5c9e1c8694fccd4e12e2d422094` | model.safetensors | 11,761,587,872 | `66ff5f8fcaf92291da486fdfbd4d5233cec90e1359348a56e3172c978b3a76d4` ✔ |
| | | tokenizer.json | 16,629,031 | `a2799ccc696b752ba00c34f58726bfe253a04921ceb6cfc620400f560474790b` ✔ |
| | | spiece.model | 4,427,844 | `ef11ac9a22c7503492f56d48dce53be20e339b63605983e9f27d2cd0e0f3922c` ✔ |
| facebook/nllb-200-distilled-600M | `f8d333a098d19b4fd9a8b18f94170487ad3f821d` | pytorch_model.bin | 2,460,457,927 | `c266c2cfd19758b6d09c1fc31ecdf1e485509035f6b51dfe84f1ada83eefcc42` ✔ |
| | | tokenizer.json | 17,331,176 | `e316b82de11d0f951f370943b3c438311629547285129b0b81dadabd01bca665` ✔ |
| | | sentencepiece.bpe.model | 4,852,054 | `14bb8dfb35c0ffdea7bc01e56cea38b9e3d5efcdcb9c251d6b40538e1aab555a` ✔ |

Artifacts actually executed. They were converted by
`scripts/nmt_convert_models.py` with torch 2.7.1+cpu, transformers 4.57.6
and CTranslate2 4.8.1, in an isolated venv:

| Model | Converted `model.bin` SHA-256 | `tokenizer.json` |
|---|---|---|
| MADLAD int8 | `890ed3b7e4654dcf1b9e7f2ce6ce641447462e782881e81aac443568eb1ca702` | same as source |
| NLLB int8 | `398726640cc2a02cc6a35277fa3cf2159ce8a1a66b48aa1b6c8837a47e3dd00c` | same as source |

### Isolation

- **Gate script:** `scripts/translation_nmt_gate.py` uses synthetic fixtures
  only, with the Hugging Face and Transformers offline flags forced.
- **No database, by construction:** the script replaces `psycopg` with a
  stub whose `connect()` raises.
- **Output:** a single JSON file in the gitignored evidence folder.
- **Verified afterwards:**
  - the isolated DB counts are identical (news 2,146, translations 89,
    history 16);
  - the model contract is unchanged;
  - on 3003, translation and assistant are both disabled;
  - the 18 Production/OpenCTI container IDs are unchanged.

## 2. Test set and criteria (unchanged)

- **Fixtures:** the same 35 as the TranslateGemma 12B gate —
  `scripts/local_ai_quality_gate.py` FIXTURES (24, including the 8 permanent
  regressions) plus `scripts/translation_quality_gate_tg.py` TERMS (11).
  Persian-source and empty-text fixtures are rule cases.
- **Coverage:**
  - names, organisations, places, acronyms, equipment codes;
  - dates, time, percent, decimal, money, coordinates;
  - URL, mention, hashtag, emoji;
  - quotation, negation, uncertainty and attribution;
  - brigade, convoy, frigate, commission, launch, missile, deployment, strike/depot.
- **The same pipeline:** salted placeholder protection and exact restore
  (`translation_tg.protect/restore`), validator
  `translation-validator-v2.1.0`, glossary `defence-glossary-fa-v1.1.0`.
  Only the engine behind `translate_field` differs.
- **Sentence splitting:** both NMT models were trained on sentence pairs,
  so multi-sentence fields are split at sentence ends and the translations
  rejoined. The translation is still verbatim model output.
- **Validator self-check:** every run rejected the 16 simulated invalid
  outputs (16/16).
- **Known validator quirk, unchanged:** its own "good" control string fails
  (`latin_prose_residue`), exactly as in the TranslateGemma runs.
- **Severity review.** Every output of TranslateGemma 12B, MADLAD and NLLB
  was read in full and classified with one rule set:

  | Severity | Meaning |
  |---|---|
  | critical | wrong fact, number, entity or meaning; invented information; key fact dropped |
  | major | wrong military echelon or term, untranslated English, colloquial register, ungrammatical |
  | minor | spelling variant, Arabic letter forms, emoji dropped |

  **This review was done by Claude (AI), not by a human.** TranslateGemma 4B
  is compared on machine results only, because its run predates the 4 extra
  fixtures. Evidence: `runtime/local-ai-evidence/phase6/review-notes.py|json`.

## 3. Results

### 3.1 Summary

| Measure (35 fields) | TranslateGemma 4B¹ | **TranslateGemma 12B** | **MADLAD-400-3B** | **NLLB-200-600M** |
|---|---|---|---|---|
| Validator "available" (machine) | 20/32 | 21/35 | 19/35 | 19/35 |
| Regression fixtures failed (machine) | 4 | 4 | 4 | 4 |
| Invalid outputs rejected | 16/16 | 16/16 | 16/16 | 16/16 |
| Review: ok / minor / major / **critical** | — | 16 / 4 / 9 / **6** | 12 / 7 / 4 / **12** | 7 / 11 / 10 / **7** |
| **Invented information (additions)** | — | **4** | **4** (incl. 3 pure hallucinations) | **0** |
| Fields without a critical or major error | — | **20** | 19 | 18 |
| Gate result | rejected | rejected | **rejected** | **rejected** |

¹ 31 fixtures / 32 fields; machine results only.

### 3.2 Errors by class (number of fields; critical in bold, then critical + major)

| Class | TranslateGemma 12B | MADLAD-400-3B | NLLB-200-600M |
|---|---|---|---|
| **Numbers** | **3** / 5 — «آپاچی مدل 96», all numbers dropped in a summary, «[واحد پول]», stray «b» | **3** / 3 — 2.75 billion → "one billion"; 96 and 2,000 lost in hallucinations | **2** / 2 — 12% dropped; $10 billion → «میلیارد دلاری» |
| **Dates** | **2** / 2 — dates replaced by «[تاریخ شروع]»; date dropped | **0** / 0 | **1** / 2 — months left in English («12 March 2026», «August») |
| **Military terms** | **2** / 4 — live-fire → "simulated"; brigade → «گردان» (battalion); frigate → generic «ناو/کشتی جنگی» | **7** / 8 — brigade → «لشکر» (division); strike → «اعتصاب» (labour strike); frigate → "aircraft"; commission → "buy" | **3** / 6 — brigade → «گروه» or gibberish; strike → «اعتصاب»; frigate → «فرگات» |
| **Names / organisations** | **2** / 4 — invented titles for Austin and Gallant; "Rheinmetall CEO" garbled | **3** / 3 — minister → "president"; "Rheinmetall CEO" dropped; Kharkiv → «خرکف» | **1** / 2 — "Rheinmetall CEO" dropped; «یاو گالنت»; «Apache», «Saab» left in English |
| **Invented information** | **1** / 4 — Austin/Gallant titles; «ایستگاه»; «سازمان @IntelCrab»; Rafael rephrased as a description | **4** / 4 — «مشارکت‌کنندگان ویکی‌پدیا» (Wikipedia contributors); «وب‌گاه رسمی شرکت هواپیمایی زاگرس» for "Poland orders 96 Apache helicopters"; «سپاه پاسداران» for "deployment of 2,000 troops"; «آمریکا» added | **0** / 0 |
| Register (colloquial) / grammar | 0 / 0 | 1 / 4 | 0 / 5 |
| Meaning lost or reversed | 0 / 1 — the denial in the negation case is lost | 6 / 7 | 3 / 3 — "commissions" read as commanders; logistics → «لوازم جانبی» (accessories) |

### 3.3 Case by case

✅ ok · 🟢 minor · 🟠 major · 🔴 critical. **M✔ / M✘** = validator
available / needs_review. Several 🔴 items pass the validator: MADLAD
"minister → president" and 12B "model 96". A machine pass is therefore not
a quality verdict.

| # | Case:field | TranslateGemma 12B | MADLAD-400-3B | NLLB-200-600M |
|---|---|---|---|---|
| 1 | `simple_title:title` | ✅ ok (M✘) — «ناوچه جدید را به ناوگان خود اضافه کرد» (validator flag is a false positive) | 🔴 critical (M✘) — «فرماندهی نیروی دریایی نیروی دریایی»: meaning lost, frigate/commission gone, repetition | 🔴 critical (M✘) — «فرماندهان نیروی دریایی فرگات جدید»: "commissions" read as commanders |
| 2 | `multi_sentence_summary:title` | ✅ ok (M✔) | 🟠 major (M✔) — colloquial «رو تموم کرد» | ✅ ok (M✔) |
| 3 | `multi_sentence_summary:summary` | 🔴 critical (M✘) — brigades → «گردان» (battalion) | 🔴 critical (M✘) — brigades → «نیروهای ارتش»; "tested logistics" → "was held in cold conditions" (logistics dropped) | 🔴 critical (M✘) — brigades → «گروه»; logistics → «لوازم جانبی» (accessories) |
| 4 | `quotation:text` | ✅ ok (M✔) | 🔴 critical (M✔) — minister → «رئیس‌جمهور» (president): wrong speaker | 🟢 minor (M✔) — slightly ungrammatical |
| 5 | `person_names:text` | 🔴 critical (M✘) — adds «وزیر دفاع ایالات متحده» and «وزیر جنگ اسرائیل» | 🟢 minor (M✘) — names correct; Arabic letter forms (ي) | 🟢 minor (M✘) — Yoav Gallant → «یاو گالنت» |
| 6 | `organizations:text` | 🟠 major (M✔) — "Rafael Advanced Defense Systems" → "Rafael, specialising in advanced defence systems" | ✅ ok (M✔) | 🟠 major (M✘) — ungrammatical word order, Arabic letter forms |
| 7 | `places:text` | ✅ ok (M✘) | 🟢 minor (M✘) — Kharkiv → «خرکف» (Russian form) | 🟢 minor (M✘) — Kharkiv → «خارکیو» |
| 8 | `military_term:text` | 🔴 critical (M✘) — live-fire → «شبیه‌سازی‌شده» (simulated); brigade → «گردان» | 🔴 critical (M✘) — hallucination: «نیروی هوایی نیروی هوایی … مشارکت‌کنندگان ویکی‌پدیا» | 🟠 major (M✘) — brigade → «گروه»; live-fire correctly «شلیک واقعی» |
| 9 | `acronyms:text` | ✅ ok (M✔) | ✅ ok (M✔) | ✅ ok (M✔) |
| 10 | `date:text` | 🔴 critical (M✘) — dates replaced by «[تاریخ شروع]» / «[تاریخ پایان]» | ✅ ok (M✔) | 🟠 major (M✔) — month left in English: «12 March 2026» |
| 11 | `time:text` | 🟠 major (M✔) — adds «ایستگاه» (station) | ✅ ok (M✔) | 🟢 minor (M✔) — detected → «کشف شد» |
| 12 | `percent:text` | 🟢 minor (M✔) — «12% درصد» | ✅ ok (M✔) | 🔴 critical (M✘) — 12% dropped |
| 13 | `decimal:text` | 🟠 major (M✔) — stray «b» in «2.75 b میلیارد» | 🔴 critical (M✘) — 2.75 billion → «يک ميليارد» (one billion), colloquial | ✅ ok (M✔) |
| 14 | `coordinates:text` | ✅ ok (M✔) | ✅ ok (M✔) | ✅ ok (M✔) |
| 15 | `equipment_codes:text` | 🟢 minor (M✘) — adds «سیستم‌های» | ✅ ok (M✔) | ✅ ok (M✔) |
| 16 | `url:text` | ✅ ok (M✔) | ✅ ok (M✔) | 🟢 minor (M✔) — statement → «گزارش» |
| 17 | `mention:text` | 🟠 major (M✔) — adds «سازمان» before @IntelCrab | 🔴 critical (M✘) — strike → «اعتصاب» (labour strike) | 🔴 critical (M✘) — strike → «اعتصاب»; footage → «فیلمبردار» |
| 18 | `hashtags:text` | ✅ ok (M✔) | ✅ ok (M✔) | ✅ ok (M✔) |
| 19 | `emoji:text` | ✅ ok (M✔) | 🟢 minor (M✔) — emoji dropped | 🟢 minor (M✔) — emoji dropped; «سرن» |
| 20 | `multilingual:text` | ✅ ok (M✔) | ✅ ok (M✔) | 🟠 major (M✔) — quote marks dropped; parade → «پرید» |
| 21 | `uncertain_claim:text` | ✅ ok (M✔) | 🟢 minor (M✔) — facility → «ساختمان» | 🟠 major (M✔) — colloquial «ميده … باشه» |
| 22 | `attributed_claim:text` | ✅ ok (M✘) | ✅ ok (M✘) | ✅ ok (M✘) |
| 23 | `negation:text` | 🟠 major (M✔) — "denied that …" → "announced that none was lost": the denial is lost | 🟠 major (M✔) — same as 12B | 🟢 minor (M✔) — denial kept («انکار کرد»); «طیاره» |
| 24 | `title_summary_numbers:title` | 🔴 critical (M✔) — 96 helicopters → «آپاچی مدل 96» (model 96) | 🔴 critical (M✘) — hallucination: «وب‌گاه رسمی شرکت هواپیمایی زاگرس» | 🟠 major (M✔) — «Apache» left in English |
| 25 | `title_summary_numbers:summary` | 🔴 critical (M✘) — all numbers, AH-64E and the date dropped; «میلیاردها واحد پول» | 🟠 major (M✔) — facts kept, ungrammatical («تحویل‌های انتظاری از 2028,») | 🔴 critical (M✘) — $10 billion → «میلیارد دلاری» (10 dropped); "August" in English |
| 26 | `term_brigade:text` | ✅ ok (M✘) — «تیپ سوم زرهی» correct (validator ordinal false positive) | 🔴 critical (M✘) — brigade → «لشکر» (division): wrong echelon | 🔴 critical (M✘) — gibberish «برگيده بندزه ي سوم» |
| 27 | `term_convoy:text` | 🟢 minor (M✔) — word order | 🟢 minor (M✘) — «قافله», «کامیون‌های 40» word order | 🟢 minor (M✔) — word order |
| 28 | `term_launch:text` | ✅ ok (M✔) | ✅ ok (M✔) | 🟠 major (M✔) — colloquial |
| 29 | `term_commission:text` | 🟠 major (M✘) — frigates → generic «ناو جنگی» | 🔴 critical (M✘) — adds «آمریکا»; frigates → «هواپیماها»; commission → buy | 🟠 major (M✘) — frigate → non-standard «فرگات»; meaning kept |
| 30 | `term_frigate:text` | 🟠 major (M✘) — frigate → generic «کشتی جنگی» | 🔴 critical (M✘) — «کشتی حامل نفتکش را از تنگه عبور داد»: frigate and escort lost | 🟠 major (M✘) — «فرگات»; meaning kept |
| 31 | `term_missile:text` | ✅ ok (M✔) | 🟢 minor (M✔) — depot → «مخزن» | 🟢 minor (M✔) — depot → «مخزن» |
| 32 | `term_deployment:text` | 🟢 minor (M✔) — word order | 🔴 critical (M✘) — hallucination: «نیروی زمینی سپاه پاسداران انقلاب اسلامی»; 2,000 troops dropped | 🟢 minor (M✘) — deployment → «ارسال» |
| 33 | `term_strike_depot:text` | ✅ ok (M✔) | 🟠 major (M✘) — colloquial; «بمب افکن بدون سرنشين» (unmanned bomber) | 🟠 major (M✘) — no verb; «حمله بدون سرنشین» |
| 34 | `names_companies:text` | 🟠 major (M✘) — «مدیرعامل شرکت Rheinmetall CEO»: garbled, facts kept | 🔴 critical (M✘) — "Rheinmetall CEO" dropped (company and role lost) | 🔴 critical (M✘) — "Rheinmetall CEO" dropped |
| 35 | `money_amount:text` | 🟠 major (M✘) — inserts «[واحد پول]»; amount kept | 🟢 minor (M✔) — «$1.2 میلیارد دلار» redundant | 🟢 minor (M✔) — word order |

Full source and output text for every field and model:
`runtime/local-ai-evidence/phase6/compare.md`, generated by
`scripts/translation_compare.py`.

### 3.4 Speed, RAM and CPU (CPU only, i7-13700K, 8 threads)

| | TranslateGemma 12B | MADLAD-400-3B int8 | NLLB-200-600M int8 |
|---|---|---|---|
| Latency per field: avg / max | 5.4 s / 10.6 s | **0.93 s / 3.5 s** | **0.32 s / 0.89 s** |
| Whole 35-fixture run, including model load | — | 39 s | 15 s |
| Peak process RAM | 8.9 GB (runner RSS) | **3.3 GB** | **0.9 GB** |
| Total CPU during run: avg / max | peak 57 % | 64 % / 83 % | 60 % / 81 % |
| One-time conversion | — | 45 s | 11 s |

- **Conversion peak:** 14.3 GB process RAM, with free RAM at least 24.3 GB.
  The sampler started a few seconds into the conversion, so the true peak
  may be slightly higher.
- **Expected throughput:** about 3,900 fields per hour for MADLAD and
  11,000 for NLLB, against about 660 for 12B. These are estimates from the
  measured average latency, not throughput measurements.

## 4. Conclusion

| Model | Decision | Main reason |
|---|---|---|
| MADLAD-400-3B-MT | **Rejected** | 12 critical errors including 3 pure hallucinations (Wikipedia contributors, Zagros Airlines, IRGC), wrong speaker, wrong echelon, wrong amounts. Fast and Apache-2.0, but unsafe. |
| NLLB-200-distilled-600M | **Rejected** | 7 critical errors (12% and $10 billion dropped, "strike" as a labour strike, gibberish brigade, Rheinmetall CEO dropped); weak, often colloquial Persian; English residue. **No invented information.** |
| TranslateGemma 12B | Rejected (phase 3, confirmed) | Fewest critical errors (6) and the most fluent Persian, but it invents facts (official titles, «ایستگاه», «سازمان») and replaced dates and numbers with placeholder text. |
| TranslateGemma 4B | Rejected (phase 2) | Machine results are no better than 12B's. |

**Best option, technically:** none is acceptable for unsupervised publishing.
If one model had to be taken further, it should be **TranslateGemma 12B**
for meaning, provided an automatic addition check is in place. NLLB-200 is
the safest against invented facts and by far the cheapest, but its term and
number accuracy is too low.

### Recommended next step (owner decision)

1. **Translation stays disabled.** Do not publish machine translations
   automatically.
2. **If translation is still wanted, use a two-model check rather than a
   single model.** Translate with TranslateGemma 12B and flag any output
   whose content is not supported by an independent translation (NLLB)
   or by the source: names, numbers, titles, roles. Flagged items go to a
   human; nothing is published without human approval. This needs its own
   gate.
3. **Larger dedicated models** could be evaluated with the same harness:
   NLLB-200 3.3B (CC-BY-NC) or MADLAD-400 7B/10B (Apache-2.0). The harness
   and conversion path are ready. Each download needs your authorisation.
4. **Validator v2.2** should fix the known false positives (ordinals,
   Persian comma, control string). It should also add an English-month check
   and an "entity/role addition" check, because the current validator passes
   wrong speakers and «مدل 96».

### Files

| Path | Content |
|---|---|
| `scripts/translation_nmt_gate.py` | Isolated NMT gate (same fixtures, validator and glossary) |
| `scripts/nmt_fetch_models.py` | Pinned, hash-verified fetch |
| `scripts/nmt_convert_models.py` | CTranslate2 int8 conversion |
| `scripts/translation_compare.py` | Case-by-case comparison |
| `runtime/local-ai-evidence/phase6/` (gitignored) | `nmt-gate-{madlad,nllb}.json`, `nmt-fetch.json`, `nmt-convert.json`, `review-notes.json`, `compare.md`, `convert-metrics.csv`, `nmt-venv-freeze.txt` |
| `runtime/nmt-models/` (gitignored) | Source checkpoints (14.2 GB) and int8 models (3.6 GB). Kept, not deleted. |
