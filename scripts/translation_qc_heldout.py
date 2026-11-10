"""Held-out test set for the translation quality controls (QC).

Written and committed BEFORE any QC rule was designed, so the rules cannot be
fitted to these sentences. The rules are developed only on the 35 earlier
gate fixtures (dev set). SYNTHETIC news-style sentences, not real events;
none repeats a dev fixture.

Each item: (id, topic, text)
"""
HELDOUT = [
    ('H01', 'politics', 'Prime Minister Kaja Kallas said on Wednesday that Estonia would raise defence spending to 3.5% of GDP in 2027.'),
    ('H02', 'diplomacy', 'Foreign ministers of France and Germany met in Paris on 14 November to discuss the ceasefire proposal.'),
    ('H03', 'sanctions', 'The European Union adopted its 19th sanctions package, targeting 45 vessels of the so-called shadow fleet.'),
    ('H04', 'energy', 'Brent crude rose 4.2% to $87.60 a barrel after the attack on the refinery.'),
    ('H05', 'military', 'The 82nd Airborne Division deployed 1,500 paratroopers to the region within 48 hours.'),
    ('H06', 'military', 'A battalion of marines landed on the island during the amphibious exercise.'),
    ('H07', 'military', 'The destroyer USS Carney shot down three drones over the Red Sea on Saturday.'),
    ('H08', 'military', 'The live-fire drill involved 30 tanks and two artillery batteries.'),
    ('H09', 'military', 'The corvette will be commissioned into the Indonesian Navy in March 2027.'),
    ('H10', 'security', 'Police arrested four suspects in Hamburg on charges of planning an attack on a synagogue.'),
    ('H11', 'security', 'The spokesman for the interior ministry denied reports that the border had been closed.'),
    ('H12', 'claims', 'Rebel sources claimed, without providing evidence, that 12 soldiers had been killed.'),
    ('H13', 'claims', 'It is not yet clear whether the explosion was caused by a missile or by an accident.'),
    ('H14', 'tech', 'Microsoft said the cyberattack affected about 200 government agencies in 11 countries.'),
    ('H15', 'tech', 'The new radar can track up to 300 targets at a range of 450 kilometres.'),
    ('H16', 'industry', 'Airbus Defence and Space signed a €2.1 billion contract for six A400M transport aircraft.'),
    ('H17', 'industry', 'BAE Systems chief executive Charles Woodburn said deliveries would begin in the second quarter.'),
    ('H18', 'politics', 'The Senate approved the $95 billion aid package by a vote of 70 to 29.'),
    ('H19', 'diplomacy', 'Ambassador Linda Thomas-Greenfield told the Security Council that the resolution had failed.'),
    ('H20', 'military', 'General Christopher Cavoli warned that Russia was rebuilding its forces faster than expected.'),
    ('H21', 'military', 'Two F-16 fighter jets intercepted a Russian Il-20 reconnaissance aircraft near the border.'),
    ('H22', 'military', 'The brigade withdrew from the town after three days of heavy fighting.'),
    ('H23', 'security', 'The convoy was ambushed on the road between Gao and Ménaka, killing seven civilians.'),
    ('H24', 'energy', 'The pipeline carries up to 55 billion cubic metres of gas per year.'),
    ('H25', 'politics', 'The president signed the decree on 3 January 2026, ordering a partial mobilisation.'),
    ('H26', 'quote', 'The minister said: "Our troops will not leave until the mission is complete."'),
    ('H27', 'military', 'The navy test-fired a hypersonic missile from a submarine for the first time.'),
    ('H28', 'military', 'Satellite images show at least 40 aircraft parked at the air base, up from 25 last month.'),
    ('H29', 'security', 'Authorities said the drone strike on the depot caused no casualties.'),
    ('H30', 'diplomacy', 'Talks in Geneva ended at 23:30 local time without an agreement.'),
    ('H31', 'industry', 'Hanwha Aerospace will build 24 K9 howitzers in Poland under the deal.'),
    ('H32', 'claims', 'According to the Kyiv Independent, the strike hit an ammunition depot in Toropets.'),
    ('H33', 'military', 'The exercise simulated an attack on a naval base, officials said.'),
    ('H34', 'politics', 'Chancellor Friedrich Merz rejected calls to send Taurus missiles to Ukraine.'),
    ('H35', 'sanctions', 'Treasury officials froze assets worth $1.4 million linked to the network.'),
    ('H36', 'military', 'A frigate of the Royal Navy shadowed two Russian warships through the English Channel.'),
    ('H37', 'security', 'The hostage was released after 471 days in captivity.'),
    ('H38', 'military', 'The regiment received its first batch of 18 Leopard 2A8 tanks on Friday.'),
    ('H39', 'tech', 'The satellite was launched at 06:12 GMT on a Falcon 9 rocket from Vandenberg.'),
    ('H40', 'claims', 'Officials did not confirm the number of casualties.'),
]
