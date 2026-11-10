"""Phase-8 independent test set for the TranslateGemma 27B evaluation.

Fixed and versioned BEFORE any 27B output exists (and before the 27B model is
downloaded). Synthetic news-style sentences; none repeats a dev fixture
(scripts/local_ai_quality_gate.py, translation_quality_gate_tg.py) or a
phase-7 held-out sentence (scripts/translation_qc_heldout.py).

Each item: (id, category, english, key_facts, trap)
  key_facts  what a correct Persian translation MUST preserve; a translation
             that violates one is CRITICAL (labelling rubric, fixed in advance)
  trap       the specific error the item is designed to provoke
Categories (6 items each):
  A level_vs_change   rise TO a value vs rise BY a value
  B number_unit       the number stays attached to its own unit/noun
  C person_role       roles and titles of named people
  D certainty         confirmed / reported / alleged / possible / denied
  E military_term     echelons, ship types, live-fire vs exercise, battery …
  F time_order        tense, before/after, deadlines, sequence
  G negation          not / no / failed / without / neither-nor
  H unsupported_add   sentences that tempt the model to add titles, places, causes
"""
SET_VERSION = 'translation-eval-p8-v1.0.0'

ITEMS = [
    # A — level vs change
    ('A01', 'level_vs_change', 'Unemployment rose to 7.2% in September.', ['level: to 7.2% (not by 7.2%)', 'September'], 'to→by'),
    ('A02', 'level_vs_change', 'Unemployment rose by 0.4 percentage points in September.', ['change: by 0.4 percentage points', 'September'], 'by→to; points→percent'),
    ('A03', 'level_vs_change', 'The army cut its reserve forces to 80,000 troops.', ['level after cut: 80,000 troops'], 'to→by'),
    ('A04', 'level_vs_change', 'Oil exports fell by a third to 1.1 million barrels a day.', ['change: by one third', 'level: 1.1 million barrels per day'], 'both quantities kept, roles not swapped'),
    ('A05', 'level_vs_change', 'Inflation slowed from 9.1% to 6.5% over the year.', ['from 9.1%', 'to 6.5%', 'slowed (decreased)'], 'from/to swapped'),
    ('A06', 'level_vs_change', 'The budget will grow 12% to $886 billion.', ['change: 12%', 'level: $886 billion'], 'level dropped or treated as change'),
    # B — number and unit
    ('B01', 'number_unit', 'Ukraine received 31 Abrams tanks and $2 billion in ammunition.', ['31 tanks (Abrams)', '$2 billion for ammunition'], 'number moved to the wrong noun'),
    ('B02', 'number_unit', 'The missile has a range of 2,000 kilometres and carries a 500-kilogram warhead.', ['range 2,000 km', 'warhead 500 kg'], 'units swapped'),
    ('B03', 'number_unit', 'The 15-kilometre buffer zone will be patrolled by 600 soldiers.', ['zone 15 km', '600 soldiers'], 'number–noun mismatch'),
    ('B04', 'number_unit', 'Each of the four ships displaces 7,000 tonnes.', ['four ships', '7,000 tonnes EACH (not in total)'], 'each→total'),
    ('B05', 'number_unit', 'The deal covers 12 helicopters worth $1.8 billion in total.', ['12 helicopters', '$1.8 billion total (not each)'], 'total→each'),
    ('B06', 'number_unit', 'Drones flew 250 kilometres to hit targets 40 kilometres inside the border.', ['flew 250 km', 'targets 40 km inside the border'], 'distances swapped'),
    # C — person roles
    ('C01', 'person_role', 'Former defence minister Ben Wallace criticised the decision.', ['FORMER defence minister', 'Ben Wallace'], 'former dropped'),
    ('C02', 'person_role', 'Deputy Prime Minister Denys Shmyhal met NATO officials in Brussels.', ['DEPUTY prime minister', 'Denys Shmyhal', 'NATO officials', 'Brussels'], 'deputy dropped → prime minister'),
    ('C03', 'person_role', 'Mark Rutte, NATO secretary general, arrived in Vilnius on Monday.', ['Mark Rutte', 'NATO secretary general', 'Vilnius', 'Monday'], 'role changed'),
    ('C04', 'person_role', 'Acting defence secretary Sarah Lin signed the order.', ['ACTING defence secretary', 'Sarah Lin'], 'acting dropped'),
    ('C05', 'person_role', 'The spokesman for the navy, Captain Alan Ruiz, declined to comment.', ['navy spokesman', 'Captain (rank)', 'Alan Ruiz', 'declined to comment'], 'rank/role mixed'),
    ('C06', 'person_role', 'Opposition leader Ana Brnabić called for early elections.', ['OPPOSITION leader', 'Ana Brnabić', 'early elections'], 'opposition dropped / becomes head of state'),
    # D — certainty
    ('D01', 'certainty', 'The strike reportedly killed a senior commander.', ['REPORTEDLY (not confirmed)', 'senior commander killed'], 'reportedly dropped → fact'),
    ('D02', 'certainty', 'Officials confirmed that the tanker had been seized.', ['CONFIRMED', 'tanker seized'], 'confirmed weakened'),
    ('D03', 'certainty', 'The group may have used chemical weapons, investigators said.', ['MAY HAVE (possibility)', 'investigators said'], 'possibility → fact'),
    ('D04', 'certainty', 'Moscow alleged that the drones were launched from Estonia.', ['ALLEGED (claim by Moscow)', 'drones launched from Estonia'], 'allegation → fact'),
    ('D05', 'certainty', 'It is unlikely that the talks will resume this year.', ['UNLIKELY', 'talks resume this year'], 'unlikely → likely / will'),
    ('D06', 'certainty', 'The ministry neither confirmed nor denied the report.', ['neither confirmed nor denied'], 'becomes confirmed or denied'),
    # E — military terms
    ('E01', 'military_term', 'Two companies of the 101st Airborne Division reached the airport.', ['two COMPANIES (military units, not firms)', '101st Airborne Division', 'airport'], 'company→firm; division→other echelon'),
    ('E02', 'military_term', 'An artillery battery fired 40 rounds during the live-fire exercise.', ['artillery BATTERY (not battalion)', '40 rounds', 'LIVE-FIRE exercise'], 'battery→battalion; live-fire→simulated'),
    ('E03', 'military_term', 'The destroyer escorted an amphibious assault ship through the strait.', ['DESTROYER', 'amphibious assault ship', 'escorted', 'strait'], 'ship types changed'),
    ('E04', 'military_term', 'Fighter jets flew 120 sorties in support of ground troops.', ['120 SORTIES (flights)', 'fighter jets', 'ground troops'], 'sorties mistranslated'),
    ('E05', 'military_term', 'The submarine will be decommissioned after 30 years of service.', ['DECOMMISSIONED (retired, not commissioned)', '30 years'], 'decommission→commission'),
    ('E06', 'military_term', 'A corps headquarters was moved closer to the front line.', ['CORPS headquarters (echelon)', 'closer to the front line'], 'corps→IRGC/other'),
    # F — time and order
    ('F01', 'time_order', 'The ceasefire took effect two hours after the agreement was signed.', ['ceasefire AFTER signing', 'two hours'], 'order reversed'),
    ('F02', 'time_order', 'Before the attack, the base had been evacuated.', ['evacuation happened BEFORE the attack (pluperfect)'], 'order reversed'),
    ('F03', 'time_order', 'The troops will withdraw by the end of 2027.', ['FUTURE', 'deadline: by end of 2027'], 'tense or year changed'),
    ('F04', 'time_order', 'The plant was shut down last week and will reopen in March.', ['shut down LAST WEEK (past)', 'reopen in March (future)'], 'tenses swapped'),
    ('F05', 'time_order', 'The talks have been suspended since June.', ['suspended SINCE June (ongoing)'], 'since→in'),
    ('F06', 'time_order', 'Elections, originally set for May, were postponed until October.', ['originally May', 'postponed until October'], 'months swapped'),
    # G — negation
    ('G01', 'negation', 'The missile did not hit its target.', ['did NOT hit'], 'negation lost'),
    ('G02', 'negation', 'No casualties were reported in the second attack.', ['NO casualties', 'second attack'], 'negation lost'),
    ('G03', 'negation', 'The rocket failed to reach orbit.', ['FAILED to reach orbit'], 'failure → success'),
    ('G04', 'negation', 'The convoy crossed the border without an escort.', ['WITHOUT escort', 'convoy crossed the border'], 'without dropped'),
    ('G05', 'negation', 'Neither side accepted the proposal.', ['NEITHER side accepted'], 'one side accepted'),
    ('G06', 'negation', 'The general said the base was not under threat.', ['base NOT under threat', 'the general said'], 'negation lost'),
    # H — unsupported additions
    ('H01', 'unsupported_add', 'Keir Starmer spoke with Volodymyr Zelensky by phone.', ['Starmer', 'Zelensky', 'by phone', 'NO titles or countries added'], 'adds titles/countries'),
    ('H02', 'unsupported_add', 'The explosion damaged a warehouse.', ['explosion', 'warehouse damaged', 'NO cause, place or casualties added'], 'adds cause/place'),
    ('H03', 'unsupported_add', 'Hensoldt delivered the radars.', ['Hensoldt', 'delivered radars', 'NO description or nationality added'], 'adds “German company”'),
    ('H04', 'unsupported_add', 'Shots were fired near the embassy.', ['shots fired', 'near the embassy', 'NO country, shooter or casualties added'], 'adds country/shooter'),
    ('H05', 'unsupported_add', 'The vote was 54 to 46.', ['54 to 46', 'NO body, subject or outcome added'], 'adds parliament/subject'),
    ('H06', 'unsupported_add', 'Sweden joined the exercise.', ['Sweden', 'joined the exercise', 'NO exercise name or NATO added'], 'adds exercise name/NATO'),
]
