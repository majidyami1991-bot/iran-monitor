# Assistant v1.3.1 — human review pack

Contract `assistant_extractive_v1.3.1-qwen3-8b-500a1f067a9f`, fingerprint `b1156669246f4722…`.
Prompt `assistant-extractive-fa-v1.3.0`, validator `extractive-validator-v1.3.1`, lexicon `assistant-lexicon-fa-en-v1.1.0`, relevance `relevance-gate-v1.0.0`.

Source reports: `v131-gate-real-A.json` (run A) and `v131-gate-real-B.json` (run B, after a model unload/reload).
Both are gitignored, in `runtime/local-ai-evidence/phase5/`. This pack is generated from them by `scripts/assistant_v13_review_pack.py`.

The evidence text is the **original** title and excerpt exactly as the pipeline sees it. Stored machine translations are never used.
**No human-review box is pre-filled.** The machine result is not a human decision.

## How to review

1. For each item, read the question, then the evidence text, then the answer.
2. For an answer, check:
   - every cited record is about the question;
   - each quote means in context what the answer suggests;
   - no relevant, verifiable record shown under the item was wrongly left out.
3. For a refusal: is it justified given the records shown?
4. Tick Yes or No for each check, and add a note where needed.
5. A single *No* on relevance or faithfulness is a critical finding. It keeps the assistant `BLOCKED_MODEL_QUALITY`.


---

## R01_common_event_multi_source

**Question:** کدام منابع درباره قرارداد F/A-XX بوئینگ گزارش داده‌اند؟

**Analysis:**
- intent `common_coverage`
- anchors F/A-XX (F/A-XX), Boeing (بوئینگ)
- event types contract
- window `all`; quantity question: False

**Retrieval:** 9 candidate records; 9 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`0e05c6f2644a`, `fcee983473e8`, `52ac3051eaf4`, `3d26e1474c99`]
**Primary-matching events (all anchors in a member's title):** [`0e05c6f2644a`, `fcee983473e8`, `52ac3051eaf4`, `3d26e1474c99`]; [`426ab329d9e9`]; [`fc68972d02ef`]; [`c567d5d731e9`]; [`fc86a96505b5`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **Defence Industry Europe** (source id `516b4133-492d-5c4d-b021-b1113c54b756`) — 2026-09-29T22:18 UTC  
  news id `0e05c6f2644aa1ea40a55095e3cd2e188330e2b9eb40d4fc21a73f9d770f7d6e` · event (cluster) `e2-238430b86bf9e74af5e4` · https://defence-industry.eu/boeing-wins-u-s-navy-f-a-xx-contract-worth-more-than-20-billion-securing-second-sixth-generation-fighter-program-after-f-47/  
  > **Boeing wins U.S. Navy F/A-XX contract worth more than $20 billion, securing second sixth-generation fighter program after F-47**  
  > The F/A-XX contract covers full-scale development and multiple test aircraft for ground, airworthiness, systems and weapons integration testing. The department said the platform will begin augmenting and eventually replacing F/A-18E/F Super Hornets and EA-18G Growlers in the 2030s, while operating alongside the F-35C. The fighter is intended to extend carrier-based operational reach and operate with crewed and uncrewed aircraft, including Collaborative Combat Aircraft. Boeing said the program will incorporate open mission systems architecture and advanced mission systems, although technical and program details remain classified. “F/A-XX will dominate contested airspace, extend operational …

- **Air & Space Forces Magazine** (source id `c1781f8f-c222-5fc4-99a9-5fcc73e5f537`) — 2026-09-29T22:08 UTC  
  news id `fcee983473e8279c4018ebd8072f857ccc8bf9e1ba947d5e64063b917fafa7db` · event (cluster) `e2-238430b86bf9e74af5e4` · https://www.airandspaceforces.com/boeing-wins-navy-f-a-xx-sixth-gen-fighter-f-47/  
  > **F-47 Maker Boeing Tapped for Navy’s F/A-XX Sixth-Gen Fighter**  
  > The Navy has awarded Boeing a contract worth more than $20 billion to build its new carrier-based sixth-generation fighter, the F/A-XX. Boeing is also building the Air Force’s sixth-gen F-47. “The F/A-XX is a critical pillar in our commitment to maintaining peace through strength,” Michael P. Duffey, the undersecretary of defense for acquisition and sustainment, said in a Sept. 29 release from the Pentagon “F/A-XX will dominate contested airspace, extend operational reach, and deliver a decisive combat advantage for the warfighter. The F/A-XX platform represents a crucial, non-negotiable investment in America’s national security and long-term air combat capabilities.” The Pentagon release …

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-29T21:40 UTC  
  news id `52ac3051eaf4556757ff154fd0a1e8713c6525b1249fd2a1565fc629b5128e77` · event (cluster) `e2-238430b86bf9e74af5e4` · https://www.twz.com/air/boeing-wins-f-a-xx-next-generation-navy-stealth-fighter-contract  
  > **Boeing Wins F/A-XX Next Generation Navy Stealth Fighter Contract**  
  > After blowing past a self-imposed August deadline , the U.S. Navy has finally announced Boeing as the winner of its F/A-XX next-generation carrier-based fighter competition. F/A-XX has become one of the most hotly anticipated U.S. defense procurement decisions in recent memory after the Pentagon tried to shelve the program indefinitely last year. Boeing had been competing against Northrop Grumman for the F/A-XX contract. An earlier down-select reportedly eliminated Lockheed Martin back in March 2025. As mentioned, the Pentagon had moved to freeze the F/A-XX program in June 2025. Three months earlier, Boeing had won a separate U.S. Air Force competition to produce what is now called the …

- **Breaking Defense** (source id `e4180227-092a-579e-b192-015a969d24f3`) — 2026-09-29T21:26 UTC  
  news id `3d26e1474c9990700fcb0bf556c9a2d9be5b8a320360e954a20adff755913f55` · event (cluster) `e2-238430b86bf9e74af5e4` · https://breakingdefense.com/2026/09/boeing-navy-ngad-faxx-next-gen-fighter-competition-northrop/  
  > **Boeing wins Navy next-gen fighter F/A-XX competition**  
  > Boeing’s win gives it a monopoly on American sixth-gen fighters, following its 2025 selection to build the F-47.

**Related records excluded as not verified to be the same event (4):**

- **Breaking Defense** (source id `e4180227-092a-579e-b192-015a969d24f3`) — 2026-10-06T14:05 UTC — *excluded, not cited*  
  news id `426ab329d9e92947b5fc55711d3f20b7dfe7de66ae6329c3320e944a2119d843` · event (cluster) `—` · https://breakingdefense.com/2026/10/unpacking-boeings-f-a-xx-win-plus-a-report-from-wartime-ukraine/  
  > **Unpacking Boeing’s F/A-XX win, plus a report from wartime Ukraine**  
  > Boeing’s victory caps a significant turnaround for its defense business, while Breaking Defense reports from western Ukraine on technology and life in wartime.

- **Breaking Defense** (source id `e4180227-092a-579e-b192-015a969d24f3`) — 2026-09-30T01:55 UTC — *excluded, not cited*  
  news id `fc68972d02ef96200b04a585e83f5b1751adad407a33798a4182724dbf19a57c` · event (cluster) `—` · https://breakingdefense.com/2026/09/what-boeings-f-a-xx-win-means-for-the-company-and-what-challenges-come-next/  
  > **What Boeing’s F/A-XX win means for the company, and what challenges come next**  
  > The selection also raises questions about how Boeing’s workforce will take on another major program.

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-30T00:22 UTC — *excluded, not cited*  
  news id `c567d5d731e9d8146c16d264bd466a2502a3ae1cb8d1c5fdda8f73150c2fcdf6` · event (cluster) `—` · https://www.twz.com/air/what-boeings-new-render-of-its-winning-f-a-xx-fighter-tells-us  
  > **What Boeing’s New Rendering Of Its Winning F/A-XX Fighter Tells Us**  
  > We have officially received our second rendering of Boeing’s F/A-XX concept, which has now officially won the tender, beating out Northrop Grumman to build the Navy’s next-generation stealth fighter. Let’s take a look at what we can see in this new image and discuss what insights it may provide. Before we start, it’s worth reminding our readers that we are basing this analysis on two publicly released renders of a highly classified aircraft design. There are deliberate choices made in these renderings to obscure critical features and capabilities and mislead foreign intelligence as to the jet’s intended capabilities. So please keep in mind that the details are bound to change. This is also …

- **USNI News** (source id `70e9a720-f949-5641-a178-fb439bad0e5b`) — 2026-09-29T21:42 UTC — *excluded, not cited*  
  news id `fc86a96505b5b1826d7faaa0406b2242cd1790f19adb232c37b773df3575a95e` · event (cluster) `—` · https://news.usni.org/2026/09/29/boeing-picked-to-build-navys-f-a-xx-carrier-fighter-in-20b-contract  
  > **Boeing Picked to Build Navy’s F/A-XX Carrier Fighter in Estimated $20B Deal**  
  > Boeing concept for F/A-XX. Boeing image Boeing will build the Navy’s next-generation fighter after decades of indecision on the future of the carrier air wing, according to a Tuesday Pentagon announcement. “The contract is valued at more than $20B for the full-scale development phase. The contract procures multiple test aircraft for ground, airworthiness, systems, and weapons integration testing,” reads the announcement . The new tactical aircraft is set to enter the fleet as the first Boeing F/A-18E/F Super Hornets leave the fleet in the 2030s. A primary mission for the new fighter will be to extend the effective strike range of the U.S. carrier air wing that has steadily shrunk over the …

**Assistant answer (run A):**

```
این رویداد را ۴ منبع مستقل گزارش کرده‌اند. تعلق اسناد به یک رویداد واحد به‌صورت خودکار احراز شد: فاصله زمانی حداکثر ۰.۹ ساعت، نوع رویداد مشترک: قرارداد، موجودیت‌های مشترک: Boeing, F/A-XX, Navy, United States، بدون تعارض مکانی. (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• Defence Industry Europe — ۲۰۲۶-۰۹-۲۹: «Boeing wins U.S. Navy F/A-XX contract worth more than $20 billion, securing second sixth-generation fighter program after F-47» [۱]
• Air & Space Forces Magazine — ۲۰۲۶-۰۹-۲۹: «F-47 Maker Boeing Tapped for Navy’s F/A-XX Sixth-Gen Fighter» [۲]
• TWZ — ۲۰۲۶-۰۹-۲۹: «Boeing Wins F/A-XX Next Generation Navy Stealth Fighter Contract» [۳]
• Breaking Defense — ۲۰۲۶-۰۹-۲۹: «Boeing wins Navy next-gen fighter F/A-XX competition» [۴]
توجه: ۴ خبر مرتبط دیگر با همین موجودیت‌ها پیدا شد که تعلقشان به همین رویداد به‌طور قابل اتکا احراز نشد؛ در این پاسخ آورده نشده‌اند.
```

**Run B (after a model unload/reload) gave a different answer — review both:**

```
این رویداد را ۴ منبع مستقل گزارش کرده‌اند. تعلق اسناد به یک رویداد واحد به‌صورت خودکار احراز شد: فاصله زمانی حداکثر ۰.۹ ساعت، نوع رویداد مشترک: قرارداد، موجودیت‌های مشترک: Boeing, F/A-XX, Navy, United States، بدون تعارض مکانی. (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• Defence Industry Europe — ۲۰۲۶-۰۹-۲۹: «Boeing wins U.S. Navy F/A-XX contract worth more than $20 billion, securing second sixth-generation fighter program after F-47» [۱]
• Air & Space Forces Magazine — ۲۰۲۶-۰۹-۲۹: «The Navy has awarded Boeing a contract worth more than $20 billion to build its new carrier-based sixth-generation fighter, the F/A-XX» [۲]
• TWZ — ۲۰۲۶-۰۹-۲۹: «Boeing had been competing against Northrop Grumman for the F/A-XX contract» [۳]
• Breaking Defense — ۲۰۲۶-۰۹-۲۹: «Boeing wins Navy next-gen fighter F/A-XX competition» [۴]
توجه: ۴ خبر مرتبط دیگر با همین موجودیت‌ها پیدا شد که تعلقشان به همین رویداد به‌طور قابل اتکا احراز نشد؛ در این پاسخ آورده نشده‌اند.
```

  - `core_quote_title:E4` — the model's sentence did not name every entity of the question; the record's verbatim title (which does) was used instead

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, citations_within_allowed=✔, min_sources=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R02_different_reports_one_event

**Question:** تفاوت روایت منابع درباره سقوط F-16 در میشیگان چیست؟

**Analysis:**
- intent `compare`
- anchors F-16 (F-16), Michigan (میشیگان)
- event types crash
- window `all`; quantity question: False

**Retrieval:** 5 candidate records; 4 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`25aa6cc06876`, `90fabcdfce2b`, `4b24898e9a9f`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **JFeed** (source id `3bef586c-ca0d-5ee7-a837-beb5f31f510a`) — 2026-09-18T13:55 UTC  
  news id `25aa6cc068764814df7e4c34fa078ea5cee4e0cd1d16e3d8c4dc0aed8e47321d` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.jfeed.com/news-world/tlkb8k  
  > **US F-16 Crashes in Michigan After Suspected Bird Strike**  
  > (no summary text stored)

- **Air & Space Forces Magazine** (source id `c1781f8f-c222-5fc4-99a9-5fcc73e5f537`) — 2026-09-18T00:25 UTC  
  news id `90fabcdfce2b1869c028a7e666da40fb7787325279b60f66ed6a59c28575e658` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.airandspaceforces.com/f-16-crashes-during-training-exercise-in-michigan-pilot-ejects/  
  > **F-16 Crashes During Training Exercise in Michigan; Pilot Ejects**  
  > (no summary text stored)

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-17T20:30 UTC  
  news id `4b24898e9a9f5c8e11aa3149995c5cfe0ab881af24f85fae8eab3d80f20c344b` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.twz.com/air/f-16-crashes-in-michigan  
  > **F-16 Crashes In Michigan**  
  > (no summary text stored)

**Assistant answer (run A):**

```
روایت ۳ منبع مستقل از یک رویداد واحد. تعلق اسناد به یک رویداد واحد به‌صورت خودکار احراز شد: فاصله زمانی حداکثر ۱۷.۴ ساعت، نوع رویداد مشترک: سقوط، موجودیت‌های مشترک: F-16, Michigan، بدون تعارض مکانی. هر منبع عیناً نقل شده و درباره درستی روایت‌ها داوری نمی‌شود (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• JFeed — ۲۰۲۶-۰۹-۱۸: «US F-16 Crashes in Michigan After Suspected Bird Strike» [۱]
• Air & Space Forces Magazine — ۲۰۲۶-۰۹-۱۸: «F-16 Crashes During Training Exercise in Michigan; Pilot Ejects» [۲]
• TWZ — ۲۰۲۶-۰۹-۱۷: «F-16 Crashes In Michigan» [۳]
```

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, citations_within_allowed=✔, min_sources=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R03_similar_but_independent_events

**Question:** درباره سقوط F-16 چه گزارش شده است؟

**Analysis:**
- intent `event_evidence`
- anchors F-16 (F-16)
- event types crash
- window `all`; quantity question: False

**Retrieval:** 41 candidate records; 7 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`9bcb1cdc58bd`, `ff9cc966a982`, `04a4425ba03a`]; [`25aa6cc06876`, `90fabcdfce2b`, `4b24898e9a9f`]
**Primary-matching events (all anchors in a member's title):** [`9bcb1cdc58bd`, `ff9cc966a982`, `04a4425ba03a`]; [`25aa6cc06876`, `90fabcdfce2b`, `4b24898e9a9f`]; [`de5e3d49171e`]

**Records that passed the relevance gate (not sent to the model; reason below):**

- **JFeed** (source id `3bef586c-ca0d-5ee7-a837-beb5f31f510a`) — 2026-09-22T19:22 UTC  
  news id `9bcb1cdc58bdaad0e83bc4f81ea22026d56d1ed4505b414380c58bb76a5e8fc5` · event (cluster) `e2-9d0a20b660231575a48c` · https://www.jfeed.com/news-world/tls49h  
  > **US F-16 Crashes at German Air Base, Pilot Ejects Safely**  
  > The US Air Force confirmed that an F-16 fighter jet crashed at an American military installation at Spangdahlem Air Base in Germany. Military officials said the circumstances surrounding the incident are under investigation. According to the Air Force statement, the crash occurred during midday hours while the crew was conducting a training flight, when the aircraft "unexpectedly went down." The pilot activated his ejection seat and survived, though officials said he sustained injuries and is "undergoing medical evaluation." No details about the pilot's condition have been released at this stage. Emergency response teams arrived at the base following the incident and launched an …

- **Air & Space Forces Magazine** (source id `c1781f8f-c222-5fc4-99a9-5fcc73e5f537`) — 2026-09-22T18:50 UTC  
  news id `de5e3d49171e263cea05b8e663d254d625c2462826b8113cc396feeacc0bded8` · event (cluster) `—` · https://www.airandspaceforces.com/f-16-thunderbird-crash-investigators-blame-turned-blade-engine/  
  > **Investigators Blame F-16 Thunderbird Crash on Turned Fan Blade Deep in Engine**  
  > A misaligned vane in an F-16 engine that field-level maintainers cannot see to inspect caused one of the U.S. Air Force’s Thunderbird jets to crash last December, a new report concludes. The same problem led another F-16 to crash 20 months earlier. The pilots ejected in both cases, escaping with minor injuries, while both jets were total losses. Separate Air Force Accident Investigation Boards came to similar conclusions. The report on the Dec. 3, 2025, Thunderbird crash in the California desert was released Sept. 21. The report on the prior crash, on April 30, 2024 , near Holloman Air Force Base, N.M., was released months before the Thunderbird crash, in February 2025. The latest …

- **Air & Space Forces Magazine** (source id `c1781f8f-c222-5fc4-99a9-5fcc73e5f537`) — 2026-09-22T16:23 UTC  
  news id `ff9cc966a98208c74cf906a3dceee1f3dfcf290b4dc7a139e97632f15ef7fa14` · event (cluster) `e2-9d0a20b660231575a48c` · https://www.airandspaceforces.com/f-16-crashes-in-germany-pilot-ejects/  
  > **F-16 Crashes in Germany; Pilot Successfully Ejects**  
  > A U.S. Air Force F-16 Fighting Falcon crashed on a local mission in Germany on Sept. 22. The pilot ejected safely and is receiving medical care, Air Force officials said. The fighter was assigned to the 52nd Fighter Wing at Spangdahlem Air Base. The jet went down on base property in the Eifel region of western Germany. The wing said in a statement the cause of the crash is under investigation and emergency personnel are at the scene of the crash. The jet went down around 2:30 p.m. local time. This is the second F-16 crash for the Air Force in five days—a Viper belonging to the Texas Air National Guard’s 149th Fighter Wing crashed during a training mission in Michigan on Sept. 17. The pilot …

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-22T15:38 UTC  
  news id `04a4425ba03a3dd4e76a5cc5fd771cf925df186e99baadaebb9076a1e38cf415` · event (cluster) `e2-9d0a20b660231575a48c` · https://www.twz.com/air/usaf-f-16-crashes-at-spangdahlem-air-base-in-germany  
  > **USAF F-16 Crashes At Spangdahlem Air Base In Germany**  
  > The pilot of a U.S. Air Force F-16 Fighting Falcon assigned to the 52nd Fighter Wing safely ejected before the aircraft crashed at Spangdahlem Air Base in Germany, according to the wing. The pilot is still receiving medical treatment, the wing said in a statement. Emergency response teams are still on the scene. The cause of the incident, which took place about 2:30 p.m. local time, is still under investigation and additional details will be released when available. The crash happened as the jet was on approach to land at the installation, located in the western German region of Rhineland-Palatinate, according to the New York Post . “Following a plane crash in the vicinity of U.S. Air Base …

- **JFeed** (source id `3bef586c-ca0d-5ee7-a837-beb5f31f510a`) — 2026-09-18T13:55 UTC  
  news id `25aa6cc068764814df7e4c34fa078ea5cee4e0cd1d16e3d8c4dc0aed8e47321d` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.jfeed.com/news-world/tlkb8k  
  > **US F-16 Crashes in Michigan After Suspected Bird Strike**  
  > (no summary text stored)

- **Air & Space Forces Magazine** (source id `c1781f8f-c222-5fc4-99a9-5fcc73e5f537`) — 2026-09-18T00:25 UTC  
  news id `90fabcdfce2b1869c028a7e666da40fb7787325279b60f66ed6a59c28575e658` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.airandspaceforces.com/f-16-crashes-during-training-exercise-in-michigan-pilot-ejects/  
  > **F-16 Crashes During Training Exercise in Michigan; Pilot Ejects**  
  > (no summary text stored)

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-17T20:30 UTC  
  news id `4b24898e9a9f5c8e11aa3149995c5cfe0ab881af24f85fae8eab3d80f20c344b` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.twz.com/air/f-16-crashes-in-michigan  
  > **F-16 Crashes In Michigan**  
  > (no summary text stored)

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `ambiguous_event` — more than one distinct event matches every anchor; the assistant does not choose or merge. Shown to the user: «بیش از یک رویداد با پرسش منطبق است؛ برای پاسخ، مکان، تاریخ یا موجودیت دقیق‌تری ذکر کنید.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R04_one_event_evidence

**Question:** درباره سقوط اف-۱۶ در میشیگان چه گزارش شده است؟

**Analysis:**
- intent `event_evidence`
- anchors F-16 (اف-16), Michigan (میشیگان)
- event types crash
- window `all`; quantity question: False

**Retrieval:** 5 candidate records; 4 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`25aa6cc06876`, `90fabcdfce2b`, `4b24898e9a9f`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **JFeed** (source id `3bef586c-ca0d-5ee7-a837-beb5f31f510a`) — 2026-09-18T13:55 UTC  
  news id `25aa6cc068764814df7e4c34fa078ea5cee4e0cd1d16e3d8c4dc0aed8e47321d` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.jfeed.com/news-world/tlkb8k  
  > **US F-16 Crashes in Michigan After Suspected Bird Strike**  
  > (no summary text stored)

- **Air & Space Forces Magazine** (source id `c1781f8f-c222-5fc4-99a9-5fcc73e5f537`) — 2026-09-18T00:25 UTC  
  news id `90fabcdfce2b1869c028a7e666da40fb7787325279b60f66ed6a59c28575e658` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.airandspaceforces.com/f-16-crashes-during-training-exercise-in-michigan-pilot-ejects/  
  > **F-16 Crashes During Training Exercise in Michigan; Pilot Ejects**  
  > (no summary text stored)

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-17T20:30 UTC  
  news id `4b24898e9a9f5c8e11aa3149995c5cfe0ab881af24f85fae8eab3d80f20c344b` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.twz.com/air/f-16-crashes-in-michigan  
  > **F-16 Crashes In Michigan**  
  > (no summary text stored)

**Assistant answer (run A):**

```
بر اساس ۳ سند مرتبط با پرسش، موارد زیر گزارش شده است (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• JFeed — ۲۰۲۶-۰۹-۱۸: «US F-16 Crashes in Michigan After Suspected Bird Strike» [۱]
• Air & Space Forces Magazine — ۲۰۲۶-۰۹-۱۸: «F-16 Crashes During Training Exercise in Michigan; Pilot Ejects» [۲]
• TWZ — ۲۰۲۶-۰۹-۱۷: «F-16 Crashes In Michigan» [۳]
```

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, citations_within_allowed=✔, min_sources=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R05_specific_record

**Question:** خبر 4b24898e9a9f5c8e چه می‌گوید؟

**Analysis:**
- intent `specific_record`
- anchors —
- event types —
- window `all`; quantity question: False

**Retrieval:** 1 candidate records; — passed the relevance gate (every anchor + event type in the original title/excerpt).

**Evidence given to the model (full original text as seen by the pipeline):**

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-17T20:30 UTC  
  news id `4b24898e9a9f5c8e11aa3149995c5cfe0ab881af24f85fae8eab3d80f20c344b` · event (cluster) `e2-57435c973ad16e6e91e0` · https://www.twz.com/air/f-16-crashes-in-michigan  
  > **F-16 Crashes In Michigan**  
  > (no summary text stored)

**Assistant answer (run A):**

```
بر اساس ۱ سند مرتبط با پرسش، موارد زیر گزارش شده است (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• TWZ — ۲۰۲۶-۰۹-۱۷: «F-16 Crashes In Michigan» [۱]
```

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, citations_within_allowed=✔, min_sources=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R06_no_evidence

**Question:** درباره سقوط F-35 در آلاسکا چه گزارش شده است؟

**Analysis:**
- intent `event_evidence`
- anchors F-35 (F-35), Alaska (آلاسکا)
- event types crash
- window `all`; quantity question: False

**Retrieval:** 1 candidate records; 0 passed the relevance gate (every anchor + event type in the original title/excerpt).

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `no_relevant_record` — no record contains every anchor and the event type in its original text. Shown to the user: «هیچ خبری پیدا نشد که همه موجودیت‌ها و نوع رویداد پرسش را در متن اصلی خود داشته باشد.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R07_number_question_money

**Question:** فروش F-35 به عربستان به چه مبلغی تأیید شد؟

**Analysis:**
- intent `event_evidence`
- anchors F-35 (F-35), Saudi Arabia (عربستان)
- event types sale
- window `all`; quantity question: True

**Retrieval:** 5 candidate records; 4 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`1b221ff18c20`, `f7d8a8c5c7b8`]
**Primary-matching events (all anchors in a member's title):** [`1b221ff18c20`, `f7d8a8c5c7b8`]; [`cdaa8f668a7c`]; [`7cf6e04306c6`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **Breaking Defense** (source id `e4180227-092a-579e-b192-015a969d24f3`) — 2026-09-17T19:39 UTC  
  news id `1b221ff18c20cc8c480df38ce28f321ba51cfe1df83278c15a8a687f119cb03b` · event (cluster) `e2-0c04300f60628ec18944` · https://breakingdefense.com/2026/09/us-clears-24b-f-35-sale-for-saudi-arabia/  
  > **US clears $24B F-35 sale for Saudi Arabia**  
  > (no summary text stored)

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-17T19:14 UTC  
  news id `f7d8a8c5c7b8ba4a988f6e3bdc794d74e5bbdb2bedf9958cd6c54c7d08b0157c` · event (cluster) `e2-0c04300f60628ec18944` · https://www.twz.com/air/f-35-sale-to-saudi-arabia-approved-by-state-department  
  > **F-35 Sale To Saudi Arabia Approved By State Department**  
  > (no summary text stored)

**Related records excluded as not verified to be the same event (2):**

- **JFeed** (source id `3bef586c-ca0d-5ee7-a837-beb5f31f510a`) — 2026-09-22T13:54 UTC — *excluded, not cited*  
  news id `cdaa8f668a7cc4ea8656f0062b19777a31765721c96c16721d5e7d1867eae019` · event (cluster) `—` · https://www.jfeed.com/news-israel/tlrqn3  
  > **Israel Demands Unprecedented Compensation for Saudi F-35 Deal**  
  > Washington has formally notified the Prime Minister's Office of its intention to execute one of the largest arms deals in history, the sale of approximately 48 advanced F-35 stealth fighters to Saudi Arabia for roughly $25 billion. According to initial reports from Walla and The Jerusalem Post, Jerusalem has no intention of letting the move pass quietly and has compiled a pointed list of compensation demands that will force the Pentagon to fall in line. The deal, which now requires approval from the U.S. Congress within a roughly 30-day window, breaks all policy precedents. While actual delivery to the Saudis remains at least five years away, Israel is already presenting an unprecedented …

- **JFeed** (source id `3bef586c-ca0d-5ee7-a837-beb5f31f510a`) — 2026-09-19T17:45 UTC — *excluded, not cited*  
  news id `7cf6e04306c640b97e918bc232ef4f6ddc198505af1d449411de013253ce595a` · event (cluster) `—` · https://www.jfeed.com/news-world/tlmhbp  
  > **Israel Stays Silent as Washington Approves F-35 Sale to Saudi Arabia**  
  > (no summary text stored)

**Assistant answer (run A):**

```
بر اساس ۲ سند مرتبط با پرسش، موارد زیر گزارش شده است (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• Breaking Defense — ۲۰۲۶-۰۹-۱۷: «US clears $24B F-35 sale for Saudi Arabia» [۱]
• TWZ — ۲۰۲۶-۰۹-۱۷: «F-35 Sale To Saudi Arabia Approved By State Department» [۲]
توجه: ۲ خبر مرتبط دیگر با همین موجودیت‌ها پیدا شد که تعلقشان به همین رویداد به‌طور قابل اتکا احراز نشد؛ در این پاسخ آورده نشده‌اند.
```

**Evidence selection notes (deterministic rules applied):**
  - `title_fallback:E2` — the model did not quote this member of the verified event; its verbatim title is shown so no outlet is hidden

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answer_within_allowed_or_expected_refusal=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R08_number_question_count

**Question:** چند نفر در سانحه ناو آیزنهاور زخمی شدند؟

**Analysis:**
- intent `event_evidence`
- anchors USS Dwight D. Eisenhower (آیزنهاور), warship (ناو)
- event types crash, casualties
- window `all`; quantity question: True

**Retrieval:** 5 candidate records; 3 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`b42c7d548639`, `f0bfa259343f`]
**Primary-matching events (all anchors in a member's title):** [`b42c7d548639`, `f0bfa259343f`]; [`226d893a9e5a`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-29T18:33 UTC  
  news id `b42c7d5486399bc992f33cd39094eedff38702e620fae6188ae1dbedd712bdc4` · event (cluster) `e2-7300a237590efed7ec3e` · https://www.twz.com/sea/navy-identifies-ea-18g-growler-as-type-involved-in-mishap-aboard-uss-dwight-d-eisenhower-last-night  
  > **Navy Identifies EA-18G Growler As Type Involved In Mishap Aboard USS Dwight D. Eisenhower Last Night**  
  > The Navy has identified the aircraft type at the center of last night’s mishap aboard the aircraft carrier USS Dwight D. Eisenhower . The service said the incident involved the crew of an EA-18G Growler electronic warfare jet forced who were forced to eject after the aircraft experienced an arresting gear failure while trying to land. This took place about 6:18 p.m. Eastern Daylight Time Monday as the vessel was off the coast of Virginia. The Growler crew, attached to the “Zappers” of Electronic Attack Squadron (VAQ) 130, was “promptly recovered by search-and-rescue personnel assigned to Helicopter Sea Combat Squadron (HSC) 7. Both aviators were safely returned to the ship,” the Navy added. …

- **USNI News** (source id `70e9a720-f949-5641-a178-fb439bad0e5b`) — 2026-09-29T03:08 UTC  
  news id `f0bfa259343f8fc25f507aae6ebca46065502c4ca126e32f77f7419b2e99fe6b` · event (cluster) `e2-7300a237590efed7ec3e` · https://news.usni.org/2026/09/28/four-injured-after-landing-mishap-aboard-uss-dwight-d-eisenhower-crew-safely-recovered  
  > **Four Injured After Landing Mishap Aboard USS Dwight D. Eisenhower, Crew Safely Recovered**  
  > An F/A-18F Super Hornet, attached to the ‘Fighting Swordsmen’ of Strike Fighter Squadron (VFA) 32, lands on the flight deck of Nimitz-class aircraft carrier USS Dwight D. Eisenhower (CVN-69) May 6, 2026. US Navy photo This post will be updated as new information becomes available. Four personnel were injured in a landing mishap aboard USS Dwight D. Eisenhower (CVN-69) on Monday, USNI News has learned. The crew of the unspecified two-seat aircraft assigned to Carrier Air Wing 3 was safely recovered after ejecting from the aircraft, the Navy said in a statement provided to USNI News. “At approximately 6:18 p.m. EDT on Sept. 28, a mishap occurred during aircraft recovery operations aboard the …

**Related records excluded as not verified to be the same event (1):**

- **USNI News** (source id `70e9a720-f949-5641-a178-fb439bad0e5b`) — 2026-10-03T12:31 UTC — *excluded, not cited*  
  news id `226d893a9e5a4d5d04ccbb4e6187bd8c694250cc537c11904f29a338559f97c8` · event (cluster) `—` · https://news.usni.org/2026/10/03/carrier-uss-dwight-d-eisenhower-to-return-to-port-after-growler-mishap  
  > **Carrier USS Dwight D. Eisenhower to Return to Port After Growler Mishap**  
  > USS Dwight D. Eisenhower (CVN-69) sails down the Elizabeth River, Apr. 20, 2026. US Navy photo Aircraft carrier USS Dwight D. Eisenhower (CVN-69) is returning to Naval Station Norfolk, Va., after a Sept. 28 incident that injured four sailors and resulted in the loss of a EA-18G Growler, USNI News has learned. The return to port will, “allow for a comprehensive assessment of the ship’s aircraft launch and recovery equipment following the Sept. 28 aviation mishap,” reads an early Saturday morning statement from Naval Air Force Atlantic. “The decision reflects the Navy’s deliberate approach to flight safety and readiness. While the cause of the mishap remains under investigation, Navy …

**Assistant answer (run A):**

```
بر اساس ۲ سند مرتبط با پرسش، موارد زیر گزارش شده است (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• TWZ — ۲۰۲۶-۰۹-۲۹: «Navy Identifies EA-18G Growler As Type Involved In Mishap Aboard USS Dwight D. Eisenhower Last Night» [۱]
• USNI News — ۲۰۲۶-۰۹-۲۹: «Four personnel were injured in a landing mishap aboard USS Dwight D. Eisenhower (CVN-69) on Monday» [۲]
توجه: ۱ خبر مرتبط دیگر با همین موجودیت‌ها پیدا شد که تعلقشان به همین رویداد به‌طور قابل اتکا احراز نشد؛ در این پاسخ آورده نشده‌اند.
```

**Evidence selection notes (deterministic rules applied):**
  - `quote_case_normalised:E1` — the model capitalised the first letter of a mid-sentence quote; the exact source text is shown
  - `quote_irrelevant:E1` — a model sentence that names no anchor/event of the question was dropped
  - `title_fallback:E1` — the model did not quote this member of the verified event; its verbatim title is shown so no outlet is hidden

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answer_within_allowed_or_expected_refusal=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R09_compare_same_numbers

**Question:** تفاوت روایت منابع درباره قرارداد PAC-3 بوئینگ چیست؟

**Analysis:**
- intent `compare`
- anchors Patriot (PAC-3), Boeing (بوئینگ)
- event types contract
- window `all`; quantity question: False

**Retrieval:** 3 candidate records; 2 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`7f97540be033`, `4a934d193c73`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **Breaking Defense** (source id `e4180227-092a-579e-b192-015a969d24f3`) — 2026-10-05T20:21 UTC  
  news id `7f97540be033198dda99400ead81378d8ed9fffc5facd20062092604be520b94` · event (cluster) `e2-3b7849ceb5333624189f` · https://breakingdefense.com/2026/10/boeing-nabs-potential-14-7-billion-pac-3-seeker-contract/  
  > **Boeing nabs potential $14.7 billion PAC-3 seeker contract**  
  > The award was issued as an undefinitzed contract by PAC-3 prime contractor Lockheed Martin.

- **Defence Industry Europe** (source id `516b4133-492d-5c4d-b021-b1113c54b756`) — 2026-10-05T20:15 UTC  
  news id `4a934d193c731fdaac40612d2a3a9e98aeedc6e0eaf8c4fd4c339db50b549c6c` · event (cluster) `e2-3b7849ceb5333624189f` · https://defence-industry.eu/boeing-wins-14-7-billion-contract-to-triple-patriot-pac-3-mse-seeker-output-amid-record-global-demand-for-air-defense-missiles/  
  > **Boeing wins $14.7 billion contract to triple Patriot PAC-3 MSE seeker output amid record global demand for air defense missiles**  
  > The seeker allows the interceptor to identify, track and engage targets, including hostile aircraft and hypersonic, ballistic and cruise missiles. Boeing said the award supports the department’s Acquisition Transformation Strategy and its Arsenal of Freedom initiative to strengthen domestic defense manufacturing. “Early investment and a relentless focus on quality and execution have positioned us to now deliver seekers at unprecedented levels in the near-term, and we’re committed to building on that momentum,” said Steve Parker, president and CEO of Boeing Defense, Space & Security. “Our Boeing teammates could not be prouder of the role they play in protecting U.S. and allied service …

**Assistant answer (run A):**

```
روایت ۲ منبع مستقل از یک رویداد واحد. تعلق اسناد به یک رویداد واحد به‌صورت خودکار احراز شد: فاصله زمانی حداکثر ۰.۱ ساعت، نوع رویداد مشترک: قرارداد، موجودیت‌های مشترک: Boeing, PAC-3, Patriot، بدون تعارض مکانی. هر منبع عیناً نقل شده و درباره درستی روایت‌ها داوری نمی‌شود (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• Breaking Defense — ۲۰۲۶-۱۰-۰۵: «Boeing nabs potential $14.7 billion PAC-3 seeker contract» [۱]
• Defence Industry Europe — ۲۰۲۶-۱۰-۰۵: «Boeing wins $14.7 billion contract to triple Patriot PAC-3 MSE seeker output amid record global demand for air defense missiles» [۲]
اعداد مندرج در نقل‌قول‌ها (استخراج خودکار از متن، بدون تفسیر): [۱]: $14.7 billion ؛ [۲]: $14.7 billion
```

**Evidence selection notes (deterministic rules applied):**
  - `core_quote_title:E1` — the model's sentence did not name every entity of the question; the record's verbatim title (which does) was used instead

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, citations_within_allowed=✔, min_sources=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R10_republished_same_outlet

**Question:** کدام منابع درباره انتخاب ایرباس A321 توسط اسپانیا گزارش داده‌اند؟

**Analysis:**
- intent `common_coverage`
- anchors A-321 (A321), Spain (اسپانیا), Airbus (ایرباس)
- event types —
- window `all`; quantity question: False

**Retrieval:** 2 candidate records; 2 passed the relevance gate (every anchor + event type in the original title/excerpt).

**Records that passed the relevance gate (not sent to the model; reason below):**

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-10-05T21:03 UTC  
  news id `4736f137b45d6c58ec72fab3c84f0302f3b72a68bd516348885505c8e3dd5a43` · event (cluster) `e2-ef3c1b2f3fa0d82a4963` · https://www.twz.com/air/spain-picks-airbus-a321-for-new-electronic-intelligence-aircraft  
  > **Spain Picks Airbus A321 For New Electronic Intelligence Aircraft**  
  > Spain is moving ahead with plans to rebuild its airborne signals intelligence (SIGINT) capability, with the Airbus A321 — part of the highly successful A320 twin-engine airliner family — selected as the basis for three new SIGINT aircraft. The choice is disclosed in the latest issue of Spain’s Revista de Aeronáutica y Astronáutica , the Ministry of Defense’s official publication. Airbus and Indra are currently working on the program’s conceptual design under the Santiago II initiative, which aims to deliver a crewed platform capable of collecting and processing intelligence across the electromagnetic spectrum. The program is intended to restore a capability Spain lost when its last Boeing …

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-10-05T21:03 UTC  
  news id `70db1a1a5ad545e03e7e4cd5b2db30bdb68bb411e326f6bbe1b4cd5a1d3bed49` · event (cluster) `e2-ef3c1b2f3fa0d82a4963` · https://www.twz.com/uncategorized/spain-picks-airbus-a321-for-new-electronic-intelligence-aircraft  
  > **Spain Picks Airbus A321 For New Electronic Intelligence Aircraft**  
  > Spain is moving ahead with plans to rebuild its airborne signals intelligence (SIGINT) capability, with the Airbus A321 — part of the highly successful A320 twin-engine airliner family — selected as the basis for three new SIGINT aircraft. The choice is disclosed in the latest issue of Spain’s Revista de Aeronáutica y Astronáutica , the Ministry of Defense’s official publication. Airbus and Indra are currently working on the program’s conceptual design under the Santiago II initiative, which aims to deliver a crewed platform capable of collecting and processing intelligence across the electromagnetic spectrum. The program is intended to restore a capability Spain lost when its last Boeing …

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `single_source` — only one independent outlet remains after removing duplicates. Shown to the user: «فقط یک منبع مستقل این رویداد را گزارش کرده است؛ پوشش مشترک یا مقایسه ممکن نیست.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R11_false_cluster_typhoon

**Question:** کدام منابع درباره بازدید مقامات ترکیه از پایگاه RAF برای تایفون گزارش داده‌اند؟

**Analysis:**
- intent `common_coverage`
- anchors Typhoon (تایفون), base (پایگاه), Turkey (ترکیه), United Kingdom (RAF), Air Force (RAF)
- event types visit
- window `all`; quantity question: False

**Retrieval:** 4 candidate records; 1 passed the relevance gate (every anchor + event type in the original title/excerpt).

**Records that passed the relevance gate (not sent to the model; reason below):**

- **The Defence Blog – Military and Defense News** (source id `854ac2a3-ba0c-5f95-a62b-6d296294960a`) — 2026-09-21T07:56 UTC  
  news id `c26be0aae833f4913022bfcfc91cfdad004af6cd58775f2cf6fe7c20bf713e9b` · event (cluster) `e2-ff69db5f703ac2a53986` · https://defence-blog.com/turkish-officials-inspect-raf-base-for-typhoon-support/  
  > **Turkish officials inspect RAF base for Typhoon support**  
  > Turkish defense specialists inspected aircraft maintenance facilities at Royal Air Force Coningsby in England on Sept. 15-17 as work continues on Türkiye’s purchase of Eurofighter Typhoon fighter jets from the United Kingdom. The Turkish Ministry of National Defense announced the visit in a post on X. The delegation included personnel from the ministry, the Turkish […]

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `single_source` — only one independent outlet remains after removing duplicates. Shown to the user: «فقط یک منبع مستقل این رویداد را گزارش کرده است؛ پوشش مشترک یا مقایسه ممکن نیست.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R12_multilingual_record

**Question:** درباره نخستین استفاده رزمی از موشک بالستیک FP-7 اوکراین چه گزارش شده است؟

**Analysis:**
- intent `event_evidence`
- anchors FP-7 (FP-7), ballistic missile (موشک بالستیک), Ukraine (اوکراین)
- event types combat_use
- window `all`; quantity question: False

**Retrieval:** 4 candidate records; 2 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Primary-matching events (all anchors in a member's title):** [`d9fe19a2146d`]; [`74c26e402a03`]

**Records that passed the relevance gate (not sent to the model; reason below):**

- **Defence Industry Europe** (source id `516b4133-492d-5c4d-b021-b1113c54b756`) — 2026-10-04T15:50 UTC  
  news id `d9fe19a2146d2c0c1135aedaa9a82b80d19a92a9f034a8b53451d3854e3e923b` · event (cluster) `—` · https://defence-industry.eu/zelenskyy-reports-first-combat-use-of-ukraines-fp-7-ballistic-missile-while-fire-point-develops-further-strike-and-interceptor-capabilities/  
  > **Zelenskyy reports first combat use of Ukraine’s FP-7 ballistic missile while Fire Point develops further strike and interceptor capabilities**  
  > The missile underwent at least 15 tests before its combat debut, according to the source report. Its first test took place on 28 February 2026. Several hours before Zelenskyy’s announcement, the General Staff of the Armed Forces of Ukraine reported strikes carried out overnight on 30 September–1 October. One of those targets may have been attacked with the FP-7, but the report does not confirm which weapon was used. The General Staff said Ukrainian forces hit a facility near Donetsk used to store, prepare and launch attack drones. A Russian drone command post was also struck near Pokrovsk in the Donetsk region. Ukrainian tactical ballistic missile. FP-7. First combat use. Thank you for the …

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-10-01T22:36 UTC  
  news id `74c26e402a03760cb696e9be913316407e560362dfbbb66a3aef40197ad9d955` · event (cluster) `—` · https://www.twz.com/news-features/ukraine-claims-first-combat-use-of-fp-7-ballistic-missile  
  > **Ukraine Claims First Combat Use Of FP-7 Ballistic Missile**  
  > Ukraine says it has used its domestically developed FP-7 tactical ballistic missile in combat for the first time, in what would mark another significant milestone in the country’s rapidly expanding indigenous long-range strike program . President Volodymyr Zelensky announced today that Ukraine had conducted the first combat use of the FP-7, a ground-launched ballistic missile developed by Ukrainian defense company Fire Point . He also said production of the weapon would follow. Ukrainian tactical ballistic missile. FP-7. First combat use. Thank you for the result. Next up: production. Glory to Ukraine! pic.twitter.com/IxdjVg51c1 — Volodymyr Zelenskyy / Володимир Зеленський (@ZelenskyyUa) …

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `ambiguous_event` — more than one distinct event matches every anchor; the assistant does not choose or merge. Shown to the user: «بیش از یک رویداد با پرسش منطبق است؛ برای پاسخ، مکان، تاریخ یا موجودیت دقیق‌تری ذکر کنید.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answer_within_allowed_or_expected_refusal=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R13_out_of_contract_why

**Question:** چرا بوئینگ برنده قرارداد F/A-XX شد؟

**Analysis:**
- intent `event_evidence`
- anchors F/A-XX (F/A-XX), Boeing (بوئینگ)
- event types contract
- window `all`; quantity question: False
- out of contract: `analysis`

**Retrieval:** 0 candidate records; — passed the relevance gate (every anchor + event type in the original title/excerpt).

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `out_of_contract_analysis` — independent analysis / motive / uncertainty judgement is outside the contract (refused before retrieval). Shown to the user: «تحلیل مستقل، انگیزه‌یابی، ارزیابی عدم قطعیت یا نتیجه‌گیری بدون سند در قرارداد این نسخه نیست.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R14_entity_lookup

**Question:** اخبار مرتبط با راینمتال

**Analysis:**
- intent `entity_lookup`
- anchors Rheinmetall (راینمتال)
- event types —
- window `all`; quantity question: False

**Retrieval:** 17 candidate records; 15 passed the relevance gate (every anchor + event type in the original title/excerpt).

**Evidence given to the model (full original text as seen by the pipeline):**

- **Defence Industry Europe** (source id `516b4133-492d-5c4d-b021-b1113c54b756`) — 2026-10-07T08:32 UTC  
  news id `92a5eb4a5f30fa0bb8bed6fe26932f3ed348c85b428164c2c05549ba77bb27ed` · event (cluster) `—` · https://defence-industry.eu/rheinmetall-gives-german-military-direct-access-to-dedicated-radar-satellites-for-lithuania-brigade-and-nato-eastern-flank-monitoring/  
  > **Rheinmetall gives German military direct access to dedicated radar satellites for Lithuania brigade and NATO eastern flank monitoring**  
  > The satellites operate under SPOCK 1, the first phase of a national radar reconnaissance system designed for continuous, all-weather surveillance. Rheinmetall ICEYE Space Solutions operates the spacecraft and is expanding the constellation. The dedicated satellites supplement reconnaissance capabilities already available to the Bundeswehr through other spacecraft. SPOCK 1 stands for “SAR Space System for Persistent Operational Tracking, Stage 1”. “Less than a year after the contract was signed, the German Armed Forces are gaining direct access to a dedicated SAR reconnaissance capability,” said Rheinmetall CEO Armin Papperger. “The successful start of production in Neuss demonstrates that …

- **EDR Magazine** (source id `a7040487-3b56-54d0-aa0a-a86ee5eac297`) — 2026-10-06T14:16 UTC  
  news id `986efc7075c388ccd4f1887927d201d6aae66860879a5414a8572c0e0998e1b3` · event (cluster) `—` · https://www.edrmagazine.eu/major-milestone-achieved-rheinmetall-iceye-space-solutions-provides-the-german-armed-forces-with-exclusive-access-to-sar-satellites  
  > **Major milestone achieved: Rheinmetall ICEYE Space Solutions provides the German Armed Forces with exclusive access to SAR satellites**  
  > Less than a year after its official commissioning, Rheinmetall ICEYE Space Solutions GmbH has reached another key milestone in the new SPOCK 1 satellite programme for the German Armed Forces. The German armed forces now have direct access to several Synthetic Aperture Radar (SAR) reconnaissance satellites dedicated exclusively to this purpose. They can commission these satellites independently, thereby building on the SAR reconnaissance capabilities already available via other satellites. Rheinmetall ICEYE Space Solutions operates the SAR satellites and continues to expand the constellation. This capability is being used primarily to protect the brigade in Lithuania and to monitor NATO’s …

- **Defence Industry Europe** (source id `516b4133-492d-5c4d-b021-b1113c54b756`) — 2026-10-06T00:21 UTC  
  news id `ab510ceb4e9868edac9c8523f36bcb6ab8b8bacabd3ec4eef76ddac09b958a30` · event (cluster) `—` · https://defence-industry.eu/rheinmetall-and-breaker-demonstrate-voice-controlled-drone-swarms-for-australian-army-boxer-combat-vehicles/  
  > **Rheinmetall and Breaker demonstrate voice-controlled drone swarms for Australian Army Boxer combat vehicles**  
  > The operator used the Boxer’s standard-issue microphone and headset after less than 30 minutes of training. Breaker’s tactical orchestration software allows crews to command teams of robots through the vehicle’s open architecture. The companies integrated the software into Rheinmetall Defence Australia’s simulator within weeks. A working capability was demonstrated on the Boxer within six months of their first discussion. The integration is intended to extend the vehicle’s reach and situational awareness without adding personnel. The companies said it would improve crew survivability and mission effectiveness. “The Boxer CRV, delivered through LAND400 Phase Two, is the most advanced land …

- **EDR Magazine** (source id `a7040487-3b56-54d0-aa0a-a86ee5eac297`) — 2026-10-02T12:18 UTC  
  news id `db3021bc0c825c629fb78e6e8ce96bfccaecfc46f5c1d762a776ce53df2bd5c4` · event (cluster) `—` · https://www.edrmagazine.eu/rheinmetall-italia-s-p-a-and-argotec-deploy-first-satellite-for-military-air-defence-surveillance-into-orbit  
  > **Rheinmetall Italia S.p.A. and Argotec deploy first satellite for military air defence surveillance into orbit**  
  > Rheinmetall has achieved a decisive milestone within its new strategic partnership with Italian space company Argotec: On October 1, 2026, the first satellite developed within this collaboration was successfully launched into orbit aboard a SpaceX Falcon 9 launch vehicle from Vandenberg Space Force Base in California, United States. With this successful launch, the Düsseldorf-based technology group, acting through its subsidiary Rheinmetall Italia S.p.A., initiates the targeted development of an independent, satellite-based capability for national security and military situational awareness, in close coordination with institutional stakeholders. The successful launch marks an important …

- **EDR Magazine** (source id `a7040487-3b56-54d0-aa0a-a86ee5eac297`) — 2026-10-02T07:53 UTC  
  news id `5702761089c8b8f9588f6d383be06bb728d912e39fba1c6a7afd2c7dc1128259` · event (cluster) `—` · https://www.edrmagazine.eu/rheinmetall-opens-new-site-in-skoppum-expansion-of-development-and-production-capacities-in-norway  
  > **Rheinmetall opens new site in Skoppum – expansion of development and production capacities in Norway**  
  > Rheinmetall is strengthening its technological and production capabilities in Norway. On 1 October 2026, Rheinmetall Nordic AS, a subsidiary of Rheinmetall, officially opened its new site in Skoppum. This expansion will increase the company’s capabilities in development, production, system integration, logistics, and customer support. The site will support the Norwegian Armed Forces, international customers, and other Rheinmetall Group companies. The new site has a gross floor area of 4,579 square metres and is designed to accommodate 127 employees. At the time of opening, 100 employees will be based there. There is potential for future expansion of up to around 5,000 square metres. A …

- **Defence Industry Europe** (source id `516b4133-492d-5c4d-b021-b1113c54b756`) — 2026-09-27T21:05 UTC  
  news id `0a536d674c9b81e86207e60a12ddba313e13e7e6acdc3ae0384daed85f2b878e` · event (cluster) `—` · https://defence-industry.eu/rheinmetall-ceo-says-first-cruise-missile-order-expected-by-year-end-or-early-2027-as-destinus-and-lockheed-martin-ventures-near-signing/  
  > **Rheinmetall CEO says first cruise missile order expected by year-end or early 2027 as Destinus and Lockheed Martin ventures near signing**  
  > The forecast gives a potential timetable for Rheinmetall’s move into cruise missiles with Destinus, a Netherlands-based defence technology company. Papperger said the separate planned venture with Lockheed Martin would cover artillery rockets. Rheinmetall and Destinus announced an agreement in April to establish Rheinmetall Destinus Strike Systems in the second half of 2026. The proposed company would be 51% owned by Rheinmetall and 49% by Destinus, subject to regulatory approval. The partners said it would manufacture, market and deliver cruise missiles and ballistic rocket artillery, adding production and qualification capacity at Rheinmetall’s German facilities. Destinus would continue …

**Assistant answer (run A):**

```
اخبار مرتبط با «راینمتال» در سامانه — ۴ خبر (هر خبر جداگانه؛ نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• Defence Industry Europe — ۲۰۲۶-۱۰-۰۷: «Rheinmetall gives German military direct access to dedicated radar satellites for Lithuania brigade and NATO eastern flank monitoring» [۱]
• EDR Magazine — ۲۰۲۶-۱۰-۰۶: «Rheinmetall ICEYE Space Solutions provides the German Armed Forces with exclusive access to SAR satellites» [۲]
• Defence Industry Europe — ۲۰۲۶-۱۰-۰۶: «Rheinmetall and Breaker demonstrate voice-controlled drone swarms for Australian Army Boxer combat vehicles» [۳]
• EDR Magazine — ۲۰۲۶-۱۰-۰۲: «Rheinmetall Italia S.p.A. and Argotec deploy first satellite for military air defence surveillance into orbit» [۴]
```

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, every_cited_record_mentions_entity=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R15_overview_no_anchor

**Question:** کدام منابع درباره یک رویداد مشترک گزارش داده‌اند؟

**Analysis:**
- intent `common_coverage`
- anchors —
- event types —
- window `all`; quantity question: False

**Retrieval:** 47 candidate records; — passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`0e05c6f2644a`, `fcee983473e8`, `52ac3051eaf4`, `3d26e1474c99`]; [`c4489b2da5be`, `8983d0b2487d`, `c8f0eaaee900`]; [`9bcb1cdc58bd`, `ff9cc966a982`, `04a4425ba03a`]; [`25aa6cc06876`, `90fabcdfce2b`, `4b24898e9a9f`]; [`8a395f9e9182`, `392eb910702f`]; [`7f97540be033`, `4a934d193c73`] (+12 more)

**Assistant answer (run A):**

```
رویدادهایی که دست‌کم دو منبع مستقل گزارش کرده‌اند و تعلق اخبارشان به یک رویداد واحد به‌صورت خودکار احراز شده است (هم‌خوشه، فاصله حداکثر ۷۲ ساعت، نوع رویداد و دست‌کم دو موجودیت مشترک، بدون تعارض مکانی؛ عنوان‌ها عین متن اصلی):
• رویداد ۱ — ۴ منبع مستقل: «Boeing wins U.S. Navy F/A-XX contract worth more than $20 billion, securing second sixth-generation fighter program after F-47» (Defence Industry Europe، ۲۰۲۶-۰۹-۲۹) [۱]؛ «F-47 Maker Boeing Tapped for Navy’s F/A-XX Sixth-Gen Fighter» (Air & Space Forces Magazine، ۲۰۲۶-۰۹-۲۹) [۲]؛ «Boeing Wins F/A-XX Next Generation Navy Stealth Fighter Contract» (TWZ، ۲۰۲۶-۰۹-۲۹) [۳]؛ «Boeing wins Navy next-gen fighter F/A-XX competition» (Breaking Defense، ۲۰۲۶-۰۹-۲۹) [۴]
• رویداد ۲ — ۳ منبع مستقل: «Northrop’s Talon Blue Collaborative Combat Aircraft Makes First Flight» (Air & Space Forces Magazine، ۲۰۲۶-۱۰-۰۵) [۵]؛ «Northrop’s Talon Blue drone wingman makes first flight» (The Defence Blog – Military and Defense News، ۲۰۲۶-۱۰-۰۳) [۶]؛ «Northrop Grumman’s Talon Blue Collaborative Combat Aircraft Has Flown» (TWZ، ۲۰۲۶-۱۰-۰۳) [۷]
• رویداد ۳ — ۳ منبع مستقل: «US F-16 Crashes at German Air Base, Pilot Ejects Safely» (JFeed، ۲۰۲۶-۰۹-۲۲) [۸]؛ «F-16 Crashes in Germany; Pilot Successfully Ejects» (Air & Space Forces Magazine، ۲۰۲۶-۰۹-۲۲) [۹]؛ «USAF F-16 Crashes At Spangdahlem Air Base In Germany» (TWZ، ۲۰۲۶-۰۹-۲۲) [۱۰]
• رویداد ۴ — ۳ منبع مستقل: «US F-16 Crashes in Michigan After Suspected Bird Strike» (JFeed، ۲۰۲۶-۰۹-۱۸) [۱۱]؛ «F-16 Crashes During Training Exercise in Michigan; Pilot Ejects» (Air & Space Forces Magazine، ۲۰۲۶-۰۹-۱۸) [۱۲]؛ «F-16 Crashes In Michigan» (TWZ، ۲۰۲۶-۰۹-۱۷) [۱۳]
• رویداد ۵ — ۲ منبع مستقل: «Leonardo DRS completes delivery of INOD Block III thermal sights to Australian Army» (Defence Industry Europe، ۲۰۲۶-۱۰-۰۶) [۱۴]؛ «Leonardo DRS completes Australian sniper thermal sight deliveries» (The Defence Blog – Military and Defense News، ۲۰۲۶-۱۰-۰۶) [۱۵]
```

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R16_phase3_q1_ranking

**Question:** مهم‌ترین تحولات ۲۴ ساعت اخیر چیست؟

**Analysis:**
- intent `event_evidence`
- anchors —
- event types —
- window `24h`; quantity question: False
- out of contract: `ranking`

**Retrieval:** 0 candidate records; — passed the relevance gate (every anchor + event type in the original title/excerpt).

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `out_of_contract_ranking` — importance ranking is outside the contract (refused before retrieval). Shown to the user: «رتبه‌بندی اهمیت اخبار به داوری نیاز دارد و در قرارداد این نسخه نیست.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R17_phase3_q4_ranking_compare

**Question:** تفاوت روایت منابع درباره مهم‌ترین موضوع چیست؟

**Analysis:**
- intent `compare`
- anchors —
- event types —
- window `all`; quantity question: False
- out of contract: `ranking`

**Retrieval:** 0 candidate records; — passed the relevance gate (every anchor + event type in the original title/excerpt).

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `out_of_contract_ranking` — importance ranking is outside the contract (refused before retrieval). Shown to the user: «رتبه‌بندی اهمیت اخبار به داوری نیاز دارد و در قرارداد این نسخه نیست.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R18_phase3_q5_uncertainty

**Question:** بر اساس داده موجود چه مواردی هنوز عدم قطعیت دارند؟

**Analysis:**
- intent `event_evidence`
- anchors —
- event types —
- window `all`; quantity question: False
- out of contract: `analysis`

**Retrieval:** 0 candidate records; — passed the relevance gate (every anchor + event type in the original title/excerpt).

**Assistant answer (run A):**

```
در اخبار موجود، شواهد کافی و قابل اتکایی برای پاسخ به این پرسش یافت نشد.
```

**Why refused:** `out_of_contract_analysis` — independent analysis / motive / uncertainty judgement is outside the contract (refused before retrieval). Shown to the user: «تحلیل مستقل، انگیزه‌یابی، ارزیابی عدم قطعیت یا نتیجه‌گیری بدون سند در قرارداد این نسخه نیست.»

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, refused_with_expected_reason=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________


---

## R19_hypersonic_test

**Question:** درباره آزمایش موشک هایپرسونیک کره شمالی چه گزارش شده است؟

**Analysis:**
- intent `event_evidence`
- anchors hypersonic (هایپرسونیک), North Korea (کره شمالی), missile (موشک)
- event types test
- window `all`; quantity question: False

**Retrieval:** 2 candidate records; 2 passed the relevance gate (every anchor + event type in the original title/excerpt).
**Verified same-event groups:** [`283c7bf0976a`, `a10479089b43`]

**Evidence given to the model (full original text as seen by the pipeline):**

- **USNI News** (source id `70e9a720-f949-5641-a178-fb439bad0e5b`) — 2026-09-23T15:01 UTC  
  news id `283c7bf0976a83c422eb1441568d1544825a1ff98332d51ab1cab7f529072e2d` · event (cluster) `e2-7e4801105337937cc819` · https://news.usni.org/2026/09/23/north-korea-tests-new-hypersonic-missile  
  > **North Korea Tests New Hypersonic Missile**  
  > North Korea tests a Hwasongpho-11Ma-1 hypersonic missile on Sept. 20, 2026. State media Korean Central News Agency photo North Korea test launched a new weapon over the weekend that appears to be a hypersonic missile, according to photos released Tuesday by state media Korean Central News Agency . North Korea’s Missile Administration Bureau tested a new weapon on Sunday, demonstrating the rapid technological development of the weapon systems, KCNA reported. KCNA did not specify what the weapons were but wording on a display of the missile’s movement reads: “Hwasongpho-11Ma-1 flight trajectory,” indicating an upgraded version of the Hwasong-11MA hypersonic missiles that North Korea unveiled …

- **TWZ** (source id `1c638686-e35b-53e9-959c-dc122aa9079f`) — 2026-09-22T18:44 UTC  
  news id `a10479089b43c9ed070a8fe2c4023c1c0be327af3085f9a3433e8a39ccb691e3` · event (cluster) `e2-7e4801105337937cc819` · https://www.twz.com/land/north-korea-tests-new-hwasong-11ma-hypersonic-missile  
  > **North Korea Tests New Hwasong-11Ma Hypersonic Missile**  
  > North Korea has released imagery of what appears to be a flight test of an updated version of its Hwasong-11Ma hypersonic missile, nearly a year after the weapon first appeared publicly at a military technology exhibition in Pyongyang. Launch of a Hwasong-11Ma-1 missile from the test facility in Anbyon County, south of Wonsan. North Korean State Media The September 20 test involved a short-range ballistic missile (SRBM) booster fitted with a hypersonic glide vehicle , according to photographs released by North Korean state media. A display screen visible in the imagery identifies the weapon as the Hwasongpho-11Ma-1, or Hwasong-11E-1 in the equivalent English-language designation. The test …

**Assistant answer (run A):**

```
بر اساس ۲ سند مرتبط با پرسش، موارد زیر گزارش شده است (نقل‌قول عین متن اصلی منبع، بدون ترجمه):
• USNI News — ۲۰۲۶-۰۹-۲۳: «North Korea tests a Hwasongpho-11Ma-1 hypersonic missile on Sept. 20, 2026.» [۱]
• TWZ — ۲۰۲۶-۰۹-۲۲: «North Korea has released imagery of what appears to be a flight test of an updated version of its Hwasong-11Ma hypersonic missile» [۲]
```

Run B (after a model unload/reload): identical answer.

**Machine result:** PASS — refusal_text_exact=✔, quotes_verbatim_in_cited_record=✔, no_url_or_injection_in_answer=✔, answered=✔, citations_within_allowed=✔, min_sources=✔

**Human review:**

| Check | Yes | No | Note |
|---|---|---|---|
| Every cited record is about what the question asks | ☐ | ☐ |  |
| Each quote is faithful in context (not misleading) | ☐ | ☐ |  |
| Nothing relevant and verifiable is wrongly left out | ☐ | ☐ |  |
| A refusal (if any) is justified | ☐ | ☐ |  |
| Decision: accept this item | ☐ | ☐ |  |

Reviewer: ______________  Date: __________

