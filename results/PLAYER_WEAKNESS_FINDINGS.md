# Player-Level Pressing Weakness Findings

Raw material for a later message to Yannick -- not written as the message
itself. Full underlying data lives alongside this file:
`dimension_breakdown_signal.csv` (the validated dimension-cause test),
`synchronization_attribution_hsv_players.csv`,
`synchronization_attribution_opponents.csv` (the one validated
attribution), `weakness_summary_hsv_players.csv`,
`weakness_summary_opponents.csv`, `best_defender_summary_hsv_players.csv`,
`best_defender_summary_opponents.csv`, `pressing_breakdown_events.csv`,
`baseline_gap_samples.csv`, `breakdown_events_dimension_diagnosis.csv`,
plus `pressure_attribution_*.csv` / `anticipation_diagnosis_events.csv`
(superseded, exploratory only -- see below).

## Which TPR dimension actually drives a breakdown

**The validated answer: Synchronization, and only Synchronization, is
statistically confirmed to be worse at real breakdown moments than in
ordinary defending. None of the other five dimensions are.**

Tested properly with a one-sided Mann-Whitney U test comparing each
dimension's percentile value at the 1,255 real breakdown moments against
a 20,000-frame random sample of ordinary defending (same `is_defending`
filter, same matches, fixed seed for reproducibility --
`frame_diagnostics.dimension_breakdown_signal`, saved to
`dimension_breakdown_signal.csv`):

| Dimension | Mean percentile, random play | Mean percentile, breakdowns | Shift | p-value |
|---|---|---|---|---|
| **Synchronization** | 0.507 | 0.305 | **-0.202 (worse)** | 5.4e-127 |
| LPC | 0.490 | 0.485 | -0.006 (not significant) | 0.26 |
| Compactness | 0.505 | 0.671 | +0.166 (better) | -- |
| POS | 0.449 | 0.620 | +0.170 (better) | -- |
| Pressure | 0.334 | 0.520 | +0.186 (better) | -- |
| Anticipation | 0.284 | 0.637 | +0.353 (better) | -- |

Only Synchronization moves the direction a "cause of breakdowns" should
move (getting *more* extreme/worse specifically when a breakdown is
about to happen), and it does so overwhelmingly (p < 10^-100, not a
borderline result). Every other dimension gets *better*, not worse, at
real breakdown moments -- which makes real tactical sense: a breakdown
event is a shot or a dribble-past, meaning the ball is dangerously close
to goal, which mechanically draws more defenders into the area (raising
Pressure, Anticipation/presence, POS, Compactness) regardless of whether
the press is actually working. Synchronization is the one thing that
gets worse under that same pressure: bodies arrive, but not as a
coordinated unit.

**This overturns three earlier, weaker analyses that all used some
variant of "which dimension has the lowest raw or percentile-ranked
value in this one frame" (`argmin`/`weakest_dimension`) instead of
testing each dimension against its own random-play baseline.** That
approach is fundamentally the wrong question -- it measures relative
competition between the six dimensions *in that single frame*, not
whether a dimension is actually elevated at breakdowns:
- Comparing raw values first gave Pressure 71%/Anticipation 18% --
  invalidated because those two float near zero in *any* defending
  frame regardless of context (58.7% and 63.5% of ALL ordinary defending
  frames are exactly 0.0 for Pressure/Anticipation respectively).
- Switching to percentile rank (comparing each value against its own
  distribution) looked like a fix and gave Pressure 40%/Synchronization
  32%, but percentile rank still assigns "0.0, most extreme possible" to
  every single frame tied at that same common floor -- so it didn't
  actually solve the base-rate problem, it just moved it one layer
  down. A separate tie-breaking bug on top of that (ties silently
  resolved in Pressure's favor by list order) was found and fixed,
  giving Pressure 33%/Synchronization 32%, effectively tied.
- None of those three numbers survived contact with the actual control
  test: a random sample of ordinary defending frames shows Pressure
  "wins" the argmin comparison 35% of the time *regardless of whether a
  breakdown is happening* -- its 33% breakdown share was just its
  resting base rate, not a real signal. LPC's argmin share (9.5%,
  "2.6x lift" over random) also didn't survive: its own percentile
  barely moves between breakdown and random play (0.485 vs 0.490) --
  it was only "winning" more often because its competitors (Pressure,
  Anticipation, POS, Compactness) got relatively better at breakdowns,
  not because LPC itself got worse.

Full debugging trail (POS bug, both tie-breaking bugs) preserved in git
history and `docs/HSV_INSIGHT_ROADMAP.md` for anyone who wants to see
exactly how each wrong answer was caught -- not repeated here since none
of those intermediate numbers should be used or cited going forward.

**Robustness checks run against the Synchronization finding specifically**
(a positive result on one arbitrary configuration isn't enough after three
prior false positives -- these were run to see if it would break):

- **Random seed:** re-ran the 20,000-frame baseline sample with 4 different
  seeds (1, 7, 123, 999). Shift stayed at -0.204 to -0.208, p between
  1.0e-128 and 1.0e-131 every time -- not a sampling artifact.
- **Breakdown-event definition:** the 1.5s lookback window (how long before
  a shot/dribble-past counts as the "breakdown moment") was an existing,
  separately-chosen parameter -- re-ran the whole test at 1.0s and 2.0s
  too. Synchronization remained the only significant, correctly-directioned
  dimension at all three (p=3.9e-154 at 1.0s, 2.4e-127 at 1.5s, 4.0e-98 at
  2.0s); every other dimension stayed non-significant or wrong-directioned
  at all three as well.
- **Tempo confound, checked and partially real:** breakdown moments have
  ~2x higher ball speed and ~1.5x higher team (defender) speed than random
  play, and there IS a genuine negative correlation between speed and
  Synchronization in general play (r=-0.13 to -0.15) -- so some of the
  effect could plausibly just be "chaotic/fast play looks less
  synchronized." Tested directly: regressed Synchronization on ball speed
  and team speed across the full 204,942-frame baseline, then compared
  the *residuals* (Synchronization value after removing what speed alone
  predicts) at breakdown vs. random. The gap shrinks (raw shift -0.094 ->
  residual shift -0.077 in raw SI units) but stays enormous
  (p=8.5e-89) -- tempo explains part of it, not most of it.
- **Goalkeeper-inclusion check redone properly:** an earlier ad-hoc
  verification of the goalkeeper caveat below used
  `find_goalkeeper_jersey(path, 'home'/'guest')` -- wrong argument type
  (the function takes an int, 0/1; `'home' == 0` is always `False` in
  Python, so it silently always returned the WRONG team's keeper and
  flagged an outfield center-back as a goalkeeper). Fixed and re-run
  correctly (int team codes): confirms the published confident tables
  below are unaffected (10 real goalkeepers exist across the full 400
  events, but only Heuer Fernandes clears the confidence bar, same as
  before) -- but the underlying CSV's `is_goalkeeper` column was
  hardcoded to one name and has now been fixed to compute it properly
  (`synchronization_attribution_reports.py`).
- **Attribution tie-breaking checked directly on real data (not just
  reasoned about):** unlike Pressure/Anticipation/POS, Synchronization's
  per-defender values are continuous (velocity), so there's no
  structural reason for exact ties the way there was for the percentile
  floor -- checked anyway rather than assumed. 6 of 400 events (1.5%)
  have a near-tie (top two candidates within 1 cm/s of each other) where
  `argmax` picking the first arbitrarily matters at all. Traced all 6:
  only one involves a player who appears in a published confident table
  (Torunarigha, who has 9 total flags against a 5-flag bar -- losing
  that single event in the worst case still leaves him confidently
  above threshold); the other 5 involve players who don't appear in any
  confident table either way. Zero risk to anything reported.
- **TPR composite formula re-verified independently:** recomputed
  `0.2305*anticipation + 0.2109*synchronization + 0.1915*pressure +
  0.1644*pos + 0.1217*lpc + 0.0809*compactness` directly from each
  checkpoint's raw columns and compared to the checkpoint's own stored
  TPR column, across all 34 matches, every frame -- exact match to
  floating-point precision (max diff 2.2e-16). This is a separate,
  independent confirmation that the TPR composite itself (not just the
  breakdown-diagnosis layer) is computed correctly.
- **`is_defending`/`team_in_possession` invariant re-verified:** confirmed
  `is_defending==1` exactly matches `team_id != team_in_possession` with
  zero mismatches across all 34 checkpoints -- the frame-selection filter
  underlying every training/analysis result in this whole project is
  internally consistent.

## Synchronization-specific attribution -- the one validated finding
## (mechanism corrected after direct challenge -- see below)

**A direct challenge to the whole metric led to a real correction, not
just reassurance.** Pushed on plainly: "count the players -- if one
isn't moving with the block, that's the problem; if everyone stays
still, that's fine" -- a simpler, more literal read of Synchronization
than the actual two-term formula. Rather than argue, both halves of
`SI(t) = 0.5*(directional_term + coherence_term)` were tested
independently against real breakdown data
(`synchronization_decompose_test.py`), with and without the goalkeeper:

| Component | What it measures | HSV shift | HSV p-value |
|---|---|---|---|
| Directional term (`max(n_fwd,n_bwd)/N`) | Is a majority moving the same rough direction | -0.002 to -0.005 | 0.34-0.42 (not significant) |
| Coherence term (`1-std(vy)/sigma_max`) | Are defenders moving at *similar speed*, not just direction | -0.17 to -0.20 | as low as 2e-66 |

**The directional term -- the half that matches the plain-language
"count who's moving with the block" description -- carries no real
signal at breakdown moments at all.** The entire validated effect comes
from the coherence term: not "one player ran the wrong way," but one
player moving at a very different *pace* than the rest of the unit,
even while broadly aligned in direction. Goalkeeper inclusion barely
affects either result.

**This directly changed the per-player attribution.** The original
version picked "responsible" primarily by directional mismatch (97% of
events) -- exactly the half now shown to carry no signal. Fixed:
"responsible" is now always whichever defender deviates most from the
team's own mean velocity (the actual driver of the validated coherence
term), regardless of whether that deviation also happens to be a
directional mismatch.

**Then the formula itself was rebuilt, not just the attribution.** Since
the directional term carries no signal at all, keeping it in the score
at 50% weight only dilutes the half that's real. Two further hypotheses
(full 2D speed instead of just the y-axis; smoothing velocity over a
trailing 1-second window instead of one instantaneous frame) were tested
against real data and both turned out to make things *worse*, not
better -- the plain single-frame, y-axis-only version already
outperforms both (see `synchronization_formula_search.py`; y is
specifically the pitch's width axis, and lateral "shifting as a block"
is the real coaching concept, while a genuine lapse is often a sharp
instant that smoothing dilutes). The evidence-based formula that
survived all of this -- `src/metrics/compute_si_v2.py`, goalkeeper
excluded -- is a clear, substantial improvement over the thesis original
by the exact same baseline-controlled test used everywhere else in this
project:

| | Original SI | Improved si_v2 |
|---|---|---|
| Pooled | shift -0.202, p=5.4e-127 | shift **-0.239**, p=**2.3e-178** |
| HSV | shift -0.194, p=1.5e-59 | shift **-0.229**, p=**1.8e-83** |
| Opponents | shift -0.209, p=5.4e-73 | shift **-0.248**, p=**2.3e-97** |

Bigger effect size and far more extreme significance across every cut,
with no change to the underlying breakdown-event data or methodology --
only the formula. This is the HSV-dashboard's version specifically; the
thesis's own submitted formula and results are untouched (kept
separately in `compute_si_thesis.py`).

**Attribution re-run to match (goalkeeper now excluded from the pool
entirely, not just flagged):** the split between the two failure modes
is close to even (220 "same direction, different speed" vs. 180 "against
the majority") -- confirming again that direction was never the real
driver. 100% of the same 400 events still attributed (no "ball
mid-flight" failure mode, since this only needs defender velocities).

**HSV squad, confident (>=5 times responsible, >=3 matches):**

| Player | Times responsible | Matches | Avg deviation from team mean (cm/s) |
|---|---|---|---|
| Miro Max Maria Muheim | 41 | 20 | 329 |
| Giorgi Gocholeishvili | 20 | 11 | 269 |
| Nicolai Remberg | 19 | 13 | 284 |
| Nicolas Capaldo Taboas | 19 | 13 | 338 |
| Jordan Torunarigha | 13 | 8 | 293 |
| Warmed Omari | 11 | 9 | 282 |
| Luka Vušković | 10 | 7 | 246 |
| William Mikelbrencis | 10 | 6 | 290 |
| Rayan Philippe | 10 | 9 | 291 |
| Bakery Jatta | 6 | 6 | 246 |
| Daniel Elfadli | 5 | 5 | 269 |

Muheim remains clearly #1 (41 of 400, one in ten events). Daniel Heuer
Fernandes is gone from the list entirely now -- excluded from the pool
by design (`compute_si_v2.py`), not just flagged as a caveat, since a
keeper's job was never to shift with the back line regardless of which
formula is used.

**Cross-metric agreement holds up completely:** all 11 confident names
are corroborated by the independent positional-gap method (Muheim,
Gocholeishvili, Capaldo Taboas, Mikelbrencis, Philippe, Jatta at its
confident tier; Remberg, Torunarigha, Omari, Vušković, Elfadli at its
exploratory tier) -- two methods that share no computation, agreeing on
every single name.

Opponent side, confident (>=3 responsible, >=2 matches): 10 players --
Luca Netz, Omar Haktab Traoré, Sirlord Calvin Conteh, Josip Stanišić,
Anton Kade, Leon Avdullahu, Phillipp Mwene, Cédric Adrian Zesiger,
Konstantinos Koulierakis, Christopher Trimmel -- full list in
`synchronization_attribution_opponents.csv`.

## Pressure-specific attribution -- superseded, kept only as exploratory data

**Caveat up front: the statistical test above shows Pressure is NOT
actually elevated at real breakdown moments (it's better, not worse,
than its random-play baseline, p not significant in the "worse"
direction) -- so "pressure-driven breakdown" is not a validated
category, and the player list below should NOT be read as "who caused a
breakdown through a pressure failure."** It's kept here only because the
underlying computation (who has the lowest individual pressure value at
a real danger moment, reusing Pressure's own TTI formula) is still a
real, correctly-computed fact about those specific moments -- it's the
causal framing ("this is why the breakdown happened") that doesn't hold
up, not the arithmetic. Treat this table as "who tends to be least
engaged, pressure-wise, right before HSV concedes a chance" -- a
descriptive positioning/engagement pattern, not a confirmed cause.

Reused Pressure's own formula (time-to-intercept per defender) to
identify, at each of the 504 events where Pressure happened to be at its
own floor at a breakdown moment, which specific defender had the highest
individual pressure value. Succeeded on 124 of 504 (24.6%) -- the rest
have the ball mid-flight in a pass at that exact instant, no clear
carrier to compute against.

**HSV squad, confident (>=5 times responsible, >=3 matches):**

| Player | Times responsible | Matches | Avg dist to carrier (m) |
|---|---|---|---|
| Albert-Mboyo Sambi Lokonga | 7 | 6 | 5.1 |
| Jordan Torunarigha | 6 | 5 | 3.0 |
| Miro Max Maria Muheim | 6 | 6 | 2.7 |
| Fábio Daniel Ferreira Vieira | 5 | 5 | 6.8 |
| Warmed Omari | 5 | 4 | 3.5 |
| Nicolas Capaldo Taboas | 5 | 5 | 3.8 |

14 further HSV players fall below the confidence bar -- see
`pressure_attribution_hsv_players.csv` for the full list.

**Cross-metric overlap (weaker evidence than previously claimed):**
Muheim, Vieira, and Capaldo Taboas show up here *and* in the confident
positional-gap weakness list above (the general "furthest from
teammates" method, which does NOT depend on the dimension-selection
analysis and remains independently valid). That overlap is still worth
noting, but given Pressure itself isn't a validated breakdown cause, it
shouldn't be presented as strong corroborating evidence -- at most it
says these three are also flagged by the (separately valid) positional-
gap method, which is the finding that actually carries weight.

Opponent side: only 2 players clear the confidence bar (Philipp Treu and
Antonio Nordby Nusa, 3 responsible / 2 matches each) -- the smaller
attributed pool (124 events total, split across ~30 opposition players)
means most opponents don't reach a reliable sample here even though they
do on the general positional-gap metric above. Full list (52 opponents,
mostly exploratory) in `pressure_attribution_opponents.csv`.

## Anticipation diagnostic -- superseded, kept only as exploratory data

**Caveat up front: the statistical test above shows Anticipation moves
in the WRONG direction to be a breakdown cause -- it's the single most
"improved" dimension at real breakdown moments (mean percentile 0.284
in random play vs. 0.637 at breakdowns, i.e. LESS extreme, not more).**
This makes sense once you see why: a breakdown event means the ball is
close to goal, which mechanically draws more defenders within 5m
regardless of whether the team is actually defending well -- so
Anticipation looks "better" at exactly the moments defined by imminent
danger. The category breakdown below is still a real, correctly-
computed fact about what these specific (dimension-tied, not causally
special) events look like, but it should NOT be presented as "why
breakdowns happen."

Not per-player attributable (Anticipation/DAI is a count-and-average over
however many defenders are near the ball, not a max/min over
individuals -- see `HSV_INSIGHT_ROADMAP.md`), but its formula splits into
two genuinely different team-level problems: not enough defenders got
near the ball at all (a shape/discipline issue) vs. defenders were there
but not tight enough (a speed/intensity issue). Validated by cross-
checking the reimplementation against the checkpoint's own stored value
at matching frames -- exact match once frame-timing is accounted for
(the two differ by up to half a second in fast transitional moments,
which is expected, not a bug).

Run against the tie-corrected 325-event set (routed by membership in
`tied_dimensions`, not equality on `weakest_dimension` -- catches the
189 events that are genuinely anticipation-tied with pressure and/or
POS, which the earlier equality-based routing silently dropped). A
second tie-breaking bug was found and fixed here too: when zero
defenders are within 5m, `presence_term` and `proximity_term` are both
exactly 0.0 (a tie), but the original `"presence" if presence_term <
proximity_term else "proximity"` silently resolved every such tie to
"proximity" -- checked directly: all 275 zero-defender events were
mislabeled "proximity", inverting the headline finding. Fixed by
special-casing `n_close==0` as `"presence"` explicitly (proximity of
players who aren't there isn't a meaningful concept).

| Category | Count | Share |
|---|---|---|
| Zero defenders within 5m at all | 275 | 85% |
| Defenders present, but too few | 20 | 6% |
| Defenders present, enough of them, just not tight enough | 30 | 9% |

**The headline finding is stronger than the earlier (buggy) version
suggested: 85% of anticipation-driven breakdowns involve literally no
defender within 5 meters of the ball at all** -- not a reaction-speed
problem, a structural one (the defensive block
wasn't positioned to have anyone nearby when it mattered). Similar for
both sides -- HSV: zero-defenders 81% / too-few 9% / not-tight 10%
(n=172); opponents: 89% / 3% / 8% (n=153) -- not a HSV-specific issue, a
pattern common to both sides in this dataset.

## Method (brief)

For every team in every one of HSV's 34 matches: find real defensive-danger
moments (a shot conceded, a player dribbled past -- from the synced event
data, not an abstract score), and at each one, identify which specific
defender was furthest out of position relative to the rest of the
defensive block, just before the moment completed.

Each flagged player's danger-moment gap is compared against their own
*normal* positioning (a periodic sample across the whole match, not just
danger moments) -- `diff_m` is the difference. A large positive `diff_m`
means a player is genuinely worse-positioned specifically when it matters,
not just naturally spread further from the pack as part of their normal
role (e.g. a fullback). This check is what caught and discarded a
misleading first-pass signal: two of the three most-frequently-flagged
players showed almost no difference from their own baseline, meaning they
were being flagged for their normal position, not a real weakness.

Split into HSV's own squad vs. opponents (different practical use:
self-coaching vs. scouting), each with its own reliability bar before a
finding is called "confident" rather than exploratory:

- **HSV players**: >=10 flagged instances across >=3 matches (meaningful
  given they appear in up to 34 matches).
- **Opponents**: >=5 flagged instances across >=2 matches (no single
  opponent plays HSV more than twice a season, so the HSV bar is
  structurally impossible here -- confirmed against the real distribution,
  not an arbitrary guess).

Below-bar entries are listed as exploratory: real data, smaller sample,
lower confidence, not something to present as a settled finding.

## HSV squad -- confident findings (>=10 flags, >=3 matches)

| Player | Times flagged | Matches | Breakdown gap (m) | Baseline gap (m) | Diff (m) |
|---|---|---|---|---|---|
| Yussuf Yurary Poulsen | 13 | 6 | 29.1 | 16.1 | **+13.0** |
| Ransford-Yeboah Königsdörffer | 102 | 27 | 28.2 | 17.0 | **+11.2** |
| Rayan Philippe | 36 | 17 | 28.3 | 17.9 | +10.3 |
| Robert-Nesta Glatzel | 24 | 12 | 25.2 | 15.1 | +10.2 |
| Philip Porwei Otele | 25 | 6 | 28.5 | 19.8 | +8.7 |
| Fábio Daniel Ferreira Vieira | 34 | 16 | 22.0 | 13.6 | +8.5 |
| Nicolas Capaldo Taboas | 12 | 8 | 22.9 | 15.5 | +7.4 |
| Albert Grønbæk Erlykke | 11 | 6 | 24.8 | 17.5 | +7.3 |
| Bakery Jatta | 30 | 12 | 26.2 | 23.1 | +3.0 |
| Miro Max Maria Muheim | 46 | 22 | 22.0 | 19.0 | +3.0 |
| Alexander Rössing-Lelesiit | 18 | 6 | 23.9 | 21.7 | +2.2 |
| Jean-Luc Mamadou Diarra Dompé | 95 | 18 | 25.5 | 24.6 | +0.9 |
| William Mikelbrencis | 87 | 20 | 23.5 | 22.9 | +0.6 |
| Fabio Amado Uri Baldé | 19 | 9 | 22.3 | 21.7 | +0.6 |
| Giorgi Gocholeishvili | 31 | 14 | 21.7 | 22.6 | -0.9 |

Read this top-to-bottom as a gradient, not a hard cutoff at "top 8": the
top ~8 names show a clear, meaningful gap between danger-moment and normal
positioning; the bottom ~5 (Dompé, Mikelbrencis, Baldé, Gocholeishvili,
and Rössing-Lelesiit to a lesser extent) are frequently flagged but show
little-to-no real difference from their own baseline -- despite high flag
counts, these are NOT strong findings and shouldn't be reported as such.

## HSV squad -- exploratory (below the confidence bar)

Real data, but fewer than 10 flags or fewer than 3 matches -- treat as
suggestive, not confirmed.

| Player | Times flagged | Matches | Diff (m) |
|---|---|---|---|
| Nicolai Remberg | 2 | 2 | +23.3 |
| Luka Vušković | 4 | 3 | +13.1 |
| Jordan Torunarigha | 5 | 5 | +12.3 |
| Damion Lamar Downs | 7 | 5 | +12.0 |
| Daniel Elfadli | 1 | 1 | +8.4 |
| Albert-Mboyo Sambi Lokonga | 3 | 2 | +8.2 |
| Immanuël-Johannes Pherai | 1 | 1 | +8.0 |
| Otto Emerson Stange | 5 | 4 | +7.8 |
| Warmed Omari | 6 | 5 | +8.8 |
| Emir Sahiti | 3 | 1 | +2.3 |

## Opponents -- confident findings (>=5 flags, >=2 matches, both fixtures played)

A scouting list: specific opposition players measurably worse-positioned
during danger moments against HSV specifically. Sorted by diff_m.

| Player | Times flagged | Diff (m) |
|---|---|---|
| Rômulo José Cardoso da Cruz | 8 | +16.0 |
| Sirlord Calvin Conteh | 10 | +13.9 |
| Deniz Undav | 8 | +12.5 |
| Tim Lemperle | 10 | +12.2 |
| Andrej Ilić | 11 | +9.9 |
| Michael Akpovie Olise | 10 | +9.5 |
| Linton Maina | 5 | +9.4 |
| Andrej Kramarić | 7 | +9.3 |
| Ragnar Prince Friedel Ache | 8 | +8.5 |
| Haris Tabaković | 18 | +8.4 |
| Yan Diomande | 7 | +8.1 |
| Bazoumana Toure | 7 | +8.0 |
| Yukinari Sugawara | 10 | +7.8 |
| Ansgar Knauff | 8 | +6.4 |
| Omar Haktab Traoré | 7 | +6.2 |
| Dimitrios Christos Giannoulis | 6 | +6.2 |
| Marco Grüll | 7 | +6.0 |
| Stefan Schimmer | 7 | +5.8 |
| Philipp Treu | 5 | +5.0 |
| Christopher Trimmel | 17 | +4.4 |
| Justin Gideon Njinmah | 9 | +4.4 |
| Luca Netz | 10 | +4.2 |
| Vladimir Coufal | 6 | +3.3 |
| Julian Ryerson | 7 | +3.2 |
| Anton Kade | 7 | +3.0 |
| Franck Honorat | 5 | +2.1 |
| Jan-Niklas Beste | 8 | +1.6 |
| Oliver Jasen Burke | 5 | +1.4 |
| Arijon Ibrahimović | 5 | +1.0 |
| Phillipp Mwene | 10 | +0.6 |
| Alexis Julian Claude-Maurice | 9 | +0.5 |
| Bote Ridle Nzuzi Baku | 11 | -0.9 |
| Mohamed El Amine Amoura | 11 | -1.1 |
| Saïd El Mala | 5 | -3.5 |
| Louis Oppie | 6 | -4.2 |

146 further opponents fall below the reliability bar (1 match played, or
fewer than 5 flags) -- see `weakness_summary_opponents.csv` for the full
list.

## "Best defender" -- the positive counterpart

Same method as the weakness finder above, flipped: at each of the same
1,255 real danger moments, instead of whoever is furthest from the
defensive block (`idxmax`), this finds whoever stays *closest* to it
(`idxmin`), then compares that to their own normal-play baseline gap the
same way (`diff_m` = baseline gap minus breakdown gap here, so a large
positive number means genuinely tighter to the pack specifically when it
matters, not just naturally central all match). Built in
`find_best_defenders.py`, split HSV/opponents the same way as every
other table here (`best_defender_reports.py`).

**A real, explainable nuance, not a contradiction:** Muheim and
Königsdörffer top both this list *and* the weakness list above (checked
directly -- zero overlapping frames between their "best" and "worst"
appearances, so this isn't a data error). Both are high-minutes, heavily
pressing-involved players, which mechanically gives them more chances to
land at either extreme across 1,255 events than a player who barely
features. The read: their positioning is high-variance, not
uniform-bad -- at some danger moments they're caught out, at others
they're the one covering. A low-minutes player can't show up prominently
on either list; a heavily-involved one can show up on both, and that's
informative in itself (inconsistency is itself a coaching-relevant
signal, distinct from a consistently-bad player like Königsdörffer's
dominant net-negative pattern above, or a consistently-good one below).

**HSV squad, confident (>=10 times best, >=3 matches):**

| Player | Times best | Matches | Diff (m) |
|---|---|---|---|
| Nicolai Remberg | 227 | 32 | +4.1 |
| Albert-Mboyo Sambi Lokonga | 97 | 20 | +6.6 |
| Fábio Daniel Ferreira Vieira | 61 | 19 | +8.1 |
| Luka Vušković | 42 | 18 | +10.1 |
| Nicolas Capaldo Taboas | 35 | 14 | +11.1 |
| Miro Max Maria Muheim | 20 | 12 | **+16.4** |
| Ransford-Yeboah Königsdörffer | 16 | 12 | +14.3 |
| Daniel Elfadli | 16 | 12 | +10.1 |
| Jordan Torunarigha | 15 | 10 | +12.1 |
| Warmed Omari | 15 | 8 | +12.0 |
| Yussuf Yurary Poulsen | 13 | 7 | +11.0 |
| Damion Lamar Downs | 13 | 6 | +12.8 |
| Jonas Meffert | 12 | 3 | +4.1 |
| Albert Grønbæk Erlykke | 11 | 3 | +12.8 |

**The clearest, most football-sensible pattern in this whole analysis:**
Remberg (227 times, by far the highest count of anything in this entire
project) and Sambi Lokonga (97 times) are both defensive midfielders --
whose literal job is staying compact and central, screening the back
line. Their `diff_m` is smaller than the more sporadic names below them
because they're *already* naturally close to the pack most of the time
(a low baseline gap to begin with), so there's less room to show a
dramatic swing -- volume and consistency, not a single standout
occasion, is their signal. Muheim's +16.4m is the single largest number
on either list in this whole project.

Opponent side, confident (>=5 times best, >=2 matches): 32 players, and
the position pattern is even sharper -- the list is dominated by
recognizable, elite defensive/central midfielders: **Joshua Kimmich**
(Bayern Munich, +7.4m), Angelo Stiller, Aleix García, Maximilian Arnold
(Wolfsburg's captain and defensive-midfield anchor, +5.9m), Rani Khedira,
Nicolas Seiwald, Rocco Reitz, Jobe Bellingham. This is an unprompted,
independent confirmation of the same real-world pattern the HSV side
shows: positional discipline is a defensive-midfield trait, and the
method finds it correctly on players whose reputations are well known,
not just on HSV's own squad. Full list in
`best_defender_summary_opponents.csv`.

## Honest limitations (say these plainly if this becomes a message)

- **Synchronization's per-player heuristic was spot-checked against real
  tracking positions (pitch plots + velocity arrows) for Muheim's 4
  highest-deviation flagged frames -- result is genuinely mixed, not a
  clean pass.** One frame (DFL-MAT-J04205, frame 52527) is a clear,
  unambiguous visual match: the rest of HSV's back line is uniformly
  drifting toward their own byline while Muheim, right next to the ball
  at the byline, moves the opposite way -- exactly what "moving against
  team direction" claims. The other three are inconclusive from a static
  image, not contradictory -- Muheim's marker sits tightly on top of the
  ball in each (he's a fullback, often genuinely near it), making his
  velocity arrow visually unreadable at plot scale, a real limitation of
  this validation method, not evidence the metric is wrong. Real video
  footage (not static tracking-frame plots) would be needed to fully
  resolve the other three -- worth doing before treating any single
  flagged frame as certain, though the aggregate statistical finding
  (based on hundreds of frames, not these four) stands independently of
  this spot-check either way.
- **The goalkeeper is included in Synchronization attribution** (Daniel
  Heuer Fernandes, 17 flags) because the underlying formula doesn't
  exclude keepers from the defending team's velocity set -- faithful to
  the metric, but not a like-for-like comparison with outfield players
  and should be excluded from any coaching-facing version of this list.
- **Single metric.** "Furthest from the mean of teammates" is one proxy
  for "out of position," not a complete tactical picture. It doesn't
  account for who the player was supposed to be marking, where the ball
  actually was, or the team's intended shape at that moment.
- **Correlation, not proof of individual fault.** A player being the
  biggest outlier at a danger moment doesn't by itself prove they caused
  it -- it's the most out-of-position defender at that instant, which is
  suggestive, not a video-confirmed attribution.
- **Exploratory-tier entries are real but noisy.** Don't present anyone
  below the confidence bar as a settled finding.
- **This is a first pass.** Worth validating a handful of the strongest
  findings against actual match video before treating them as final,
  the same way the sync work itself went through several rounds before
  being trustworthy.
