# Season-Level Pattern Findings (HSV-only)

Separate from `PLAYER_WEAKNESS_FINDINGS.md` (which is about individual
players) -- this covers team-level, season-wide patterns from the
"quick win"/"medium effort" sections of `docs/HSV_INSIGHT_ROADMAP.md`.
Raw data in `season_patterns_frames.csv`, `season_patterns_per_match_tpr.csv`,
and `restart_pressing_windows.csv`.

## Weather: no meaningful effect (checked, ruled out)

Quick check using match_info.xml's own Environment tag (temperature,
humidity, precipitation, roof) against HSV's per-match average defending
TPR. Temperature: r=0.134, p=0.448. Humidity: r=-0.243, p=0.165. Neither
significant. Precipitation and roof status barely vary in this dataset
(33 of 34 matches "none"/open roof), too small a sample to say anything
about rain specifically. A real null result, not a gap -- weather isn't
a meaningful driver of pressing intensity in this data.

## Home vs. away: no meaningful difference

HSV's own average TPR while defending: 0.373 at away matches vs. 0.370
at home, across ~48-50k defending frames each side. Given the standard
deviation (~0.104) and sample size, this difference is not meaningfully
different from noise. Real finding, just a null one: HSV's pressing
intensity does not depend on venue in this dataset.

(Numbers on this page were refreshed against the current, POS-fix-
corrected checkpoints via `streamlit_app/prepare_dashboard_data.py` --
small shifts of 0.003-0.007 from an earlier draft of this table, same
qualitative pattern throughout, nothing reversed.)

## In-match fatigue/decay: not what a simple aggregate would suggest

The naive aggregate (TPR by 15-minute block, all 34 matches combined)
shows TPR *rising* across the match (0.364 in the first 15 minutes to
0.382 in stoppage time), the opposite of a fatigue effect. Compactness
shows the same rising pattern, even more sharply (0.584 to 0.626).

Before accepting "no fatigue, pressing gets better late" at face value,
checked whether this is confounded by game state (teams often press
differently depending on the scoreline) -- it is. Splitting by HSV's
actual result (14 losses, 11 draws, 9 wins that season):

| Time block | Draws | Losses | Wins |
|---|---|---|---|
| 0-15 | 0.367 | 0.365 | 0.359 |
| 15-30 | 0.362 | 0.363 | 0.378 |
| 30-45 | 0.371 | 0.362 | 0.372 |
| 45-60 | 0.374 | 0.371 | 0.368 |
| 60-75 | 0.375 | **0.388** | **0.356** |
| 75-90 | 0.378 | **0.384** | 0.367 |
| 90+ | 0.373 | 0.382 | **0.390** |

- **Losses**: clear, strong late intensification (0.384-0.388 in the
  60-90 window vs. ~0.36 early) -- textbook "chasing the game" pressing.
- **Wins**: the opposite shape. TPR dips to the season-low (0.356) in
  the 60-75 window (game management, sitting on a lead), then spikes to
  the season-high (0.390) in the final minutes (closing out the game,
  and/or the trailing opponent committing more numbers forward, creating
  more to press against).
- **Draws**: the mildest pattern of the three, consistent with less
  extreme urgency in a level game.

**The honest conclusion**: the raw "TPR rises late" aggregate is real
but was masking a scoreline-dependent story, not a universal
fatigue-immunity finding. Since HSV lost more matches than they won this
season, the loss-driven late-game surge disproportionately shapes the
overall trend -- this is the more useful, actionable version of the
finding, not the naive aggregate.

## Game-state effect (live score state, not just final result)

More precise than the win/loss/draw split above: rather than labeling a
whole match by its final outcome, this uses the actual score
differential at each moment (a team that trailed most of a match it
eventually won is correctly labeled "behind" for that earlier period,
not "leading" throughout). Needs real goal timing, found in the raw
StatsBomb event JSON (own goals are a separate event type, "Own Goal
For"/"Own Goal Against" -- not a Shot with outcome "Goal"; missed
entirely at first, caught by validating each match's reconstructed final
score against the actual scoreline, which failed on exactly the 2
matches where HSV conceded an own goal until fixed). Validated
cleanly: 34 of 34 matches' reconstructed scorelines now match exactly.

| Game state | Mean TPR | Std | Frames |
|---|---|---|---|
| Behind | 0.378 | 0.104 | 26,129 |
| Level | 0.370 | 0.104 | 54,043 |
| Leading | 0.366 | 0.107 | 17,688 |

A clean, monotonic result: HSV presses hardest when chasing a goal,
most conservatively when protecting a lead, with level games in between.
This confirms and sharpens the win/loss/draw finding above with a more
precise, moment-by-moment signal rather than a whole-match label.

By time block, the "leading" state specifically still spikes to 0.388 in
the final minutes (the single highest value across every state/time
combination) -- consistent with either seeing a lead out under late
pressure, or the trailing opponent committing more players forward and
creating more for HSV to press against.

## Compactness trend

Same rising pattern as the naive TPR aggregate at first glance (0.584
early to 0.626 late) -- but splitting by result the same way shows a
genuinely different story from TPR, not just a repeat of it:

| Time block | Draws | Losses | Wins |
|---|---|---|---|
| 0-15 | 0.562 | 0.590 | 0.603 |
| 15-30 | 0.574 | 0.585 | 0.631 |
| 30-45 | 0.540 | 0.587 | 0.638 |
| 45-60 | 0.593 | 0.556 | 0.609 |
| 60-75 | 0.621 | 0.617 | 0.596 |
| 75-90 | 0.590 | 0.616 | 0.638 |
| 90+ | 0.613 | 0.605 | 0.664 |

Wins are consistently the most compact across nearly every time block
(0.60-0.66), not just late on -- unlike TPR, there's no sharp
result-dependent late-game swing here (wins don't show TPR's dramatic
dip-then-spike shape). The more accurate read: **compact defensive shape
is associated with winning throughout the match**, while TPR's
scoreline-dependent late-game surge is a separate, more time-specific
phenomenon. Two different metrics, two different stories -- worth
keeping them distinct rather than assuming one explains the other.

## Restart-specific pressing: corners/throw-ins vs. goal kicks pull in
## opposite directions -- pooling them would have hidden both

Does the defending team's TPR right after a stoppage (the moment their
shape has just been reset) differ from their normal defending TPR?
Restart moments come from StatsBomb's own `play_pattern` field on each
event (read from the raw event JSON, not the pared-down synced CSV,
which doesn't carry it), anchored to tracking frames via the existing
event_id/sync join. Each restart's 5-second follow-up window is compared
against that same team's own overall defending-TPR distribution for that
match (not a global average -- teams differ in baseline intensity), via
Mann-Whitney U, the same baseline-controlled method established in
`frame_diagnostics.dimension_breakdown_signal` after the "which TPR
dimension drives breakdowns" investigation showed raw/pooled comparisons
can't be trusted on their own.

| Restart type | n frames | Mean TPR | Baseline TPR | p-value |
|---|---|---|---|---|
| Corner | 1,343 | 0.419 | 0.371 | 3.7e-54 |
| Throw-in | 4,962 | 0.389 | 0.371 | 9.8e-35 |
| Goal kick | 1,908 | 0.327 | 0.371 | 4.2e-89 |
| **All pooled** | 8,213 | 0.380 | 0.371 | 8.1e-10 |

(A first pass under-covered this -- the team-name join used exact string
equality between DFL and StatsBomb team names, which silently drops any
team with a spelling difference between the two sources, e.g. DFL's "FC
St. Pauli" vs. StatsBomb's "St. Pauli"; caught by noticing only 44 of a
possible ~68 match-team pairs had any restart data at all, fixed with
the same loose-containment name match already used elsewhere in this
project (`_names_match`), and re-run across the full 64 pairs. The
conclusion below is unchanged and, if anything, more significant with
full coverage -- but the exact numbers here supersede an earlier,
incomplete version.)

**Pooling all three types first (the naive approach) would have shown
only a small bump and missed the real story entirely.** Corners and
throw-ins genuinely raise defending intensity above normal (+0.048 and
+0.018 TPR) -- both are proximity-driven defensive scrambles, consistent
with real tactical expectation. Goal kicks do the opposite, and by a
larger margin (-0.044 TPR, the single strongest effect of the three): a
goal kick starts from the opposing goalkeeper deep in their own half, so
HSV/the opponent (now "defending" in the sense of not having the ball)
hasn't had time or proximity to engage yet in the moments right after --
a low-pressing window by construction, not a lapse in effort. Averaging
these three together would have produced a technically-significant but
practically misleading number (+0.009, masking a -0.044 to +0.048 spread
underneath it) -- exactly the kind of pooling mistake this whole project
already learned to distrust once.

## Counter-press / recovery speed

How long after losing the ball in open play does a team win it back?
Built from StatsBomb's `possession`/`possession_team` fields (raw event
JSON) -- a genuine open-play turnover is a possession handover where the
new possession's `play_pattern` is "Regular Play" or "From Counter" (not
a dead-ball restart, which is a different situation already covered
above); the recovery ends whenever that team's next possession starts,
however it starts. Same `_names_match` team-name bug as restart_pressing.py
was caught and fixed here too -- the first pass showed HSV losing the
ball 1,299 times to the opponents' 401, a 3.2x imbalance implausible for
real football; traced to 24 of 34 matches silently dropping every
opponent turnover because of a DFL/StatsBomb name mismatch. Fixed,
re-run: 1,299 vs. 1,106, a believable ~1.17x difference.

| | n | Median recovery | Mean recovery | Within 6s |
|---|---|---|---|---|
| HSV loses the ball | 1,299 | 15.96s | 20.83s | 21.5% |
| Opponent loses the ball (vs. HSV) | 1,106 | 13.92s | 20.20s | 21.4% |

**Honest null result, checked properly rather than eyeballed:** the raw
medians look different (15.96s vs. 13.92s), but neither a pooled
Mann-Whitney (p=0.35) nor a per-match paired test (30 matches, p=0.16)
shows this as statistically real -- HSV's counter-pressing speed isn't
meaningfully different from what opponents show recovering the ball
against them. About 1 in 5 turnovers on both sides gets won back within
the classic "6-second" gegenpressing window, for both sides alike.

**The genuinely useful result here is a validation of TPR itself, not
the HSV-vs-opponent comparison:** checked whether each team's own TPR in
the 3 seconds right after losing the ball predicts how long they
actually took to recover it. Spearman correlation across 2,288 turnovers:
rho=-0.147, p=1.6e-12 -- small in magnitude but real and correctly
signed (higher immediate pressing intensity predicts a faster recovery).
This is a different kind of check than anything else in this project:
not "does the formula match its own spec" or "is this dimension elevated
at breakdowns," but "does TPR predict a real, independent match outcome"
-- and it does, modestly. A useful external sanity check on the metric
as a whole, separate from the six-dimension internal validation done
earlier.

## Missed-press-trigger detection: backpasses to the keeper

A backpass to the goalkeeper is one of the clearest textbook cues to
press (the keeper's options are limited) -- does pressing intensity
actually rise in the moments after one? The goalkeeper for each team is
read directly from the raw StatsBomb "Starting XI" event (no cross-
source lookup needed for this part), and a qualifying event is an
open-play `Pass` whose recipient is that team's keeper. Same
`_names_match` fix as the other two analyses above was needed and
applied here too before running the full batch.

789 such moments across all 34 matches. The pressing team's TPR in the
5 seconds after is **lower**, not higher, than their own match baseline
(0.320 vs. 0.371, p=8.2e-166) -- the opposite of what a "trigger" should
look like. 75.0% of individual instances show below-median pressing
intensity in the follow-up window.

**Read this carefully, not as a simple "missed opportunity" story.** The
effect size (-0.051 TPR) is almost identical to the goal-kick effect
found in restart-pressing above (-0.044) -- both are moments where the
ball sits deep in the passing team's own defensive third, so the
pressing team's players are mechanically not close to it regardless of
intent. This data can't distinguish a deliberate, conservative low-block
choice (drop into shape rather than commit numbers forward to chase a
back-pass) from a genuine missed opportunity to press -- both would
produce the same TPR pattern. What the data *can* speak to is the
comparison between HSV and their opponents on the exact same cue:

| | Missed-trigger rate | n |
|---|---|---|
| HSV pressing (opponent backpasses to their own keeper) | 80.7% | 280 |
| Opponents pressing (HSV backpasses to their own keeper) | 71.9% | 509 |

HSV misses this specific cue measurably more often than opponents do
against them -- a real, comparative gap on identical situations, even if
the absolute "should everyone press this more" question stays
open-ended without knowing each team's intended tactical setup.

## Opponent playmaker impact -- resolved after finding the real confound

The goal: which specific opposing players, when personally on the ball,
correlate with HSV's press measurably loosening -- sharper scouting
information than generically flagging weak opposition defenders.

**The full debugging trail, kept in full because the eventual fix isn't
the one that looks obvious at first:**

1. First pass used TPR (team-level 6-metric composite) at the moment of
   each touch, compared to that team's own same-match baseline.
   Correlation between a player's average pitch position and their
   "impact" score: **0.855** -- the "suppresses the press" list was
   literally every goalkeeper, the "increases it" list literally every
   forward. Pure pitch geometry (the same mechanism as the goal-kick and
   backpass-to-keeper findings above), not a player-specific effect.
2. Switched from TPR to something more direct: the real distance from
   the ball to the nearest HSV defender at that exact tracking frame
   (a full re-parse of tracking data, not a proxy metric). Controlled
   for position with a 10m x-bin, then a 10m x/y grid. Correlation only
   dropped to -0.723, then -0.650 -- barely better, because nearest-
   defender distance is, if anything, *more* mechanically tied to pitch
   zone than TPR was (a settled defensive block's distance to the ball
   scales with zone almost by definition).
3. **The actual fix: control for ROLE, not position.** A striker's zone
   and a center-back's zone aren't just spatially different, they're
   categorically different jobs with different expected defensive
   treatment -- no amount of finer spatial binning was going to separate
   that. Each player's real starting position (StatsBomb's own Starting
   XI lineup data, grouped into 8 broad roles: Goalkeeper, Center Back,
   Full Back, Defensive Mid, Central Mid, Attacking Mid, Winger,
   Forward) replaced the spatial baseline. Correlation: **-0.107** --
   effectively resolved, after six serious attempts across two different
   underlying measures.

**Final, validated ranking (>=15 touches), each player compared only to
others in the SAME role:**

| Most pressed relative to role peers | Role | Most space relative to role peers | Role |
|---|---|---|---|
| Moritz Nicolas | GK | Kamil Grabara | GK |
| Jonas Adjei Adjetey | CB | Frederik Rønnow | GK |
| Péter Gulácsi | GK | Fabio Chiarodia | CB |
| Alexander Nübel | GK | Albian Hajdari | FB |
| Philipp Sander | CB | Abdoul Karim Coulibaly | CB |
| Nikola Vasilj | GK | Castello Lukeba | CB |
| Jan Bürger | FB | Ansgar Knauff | FWD |
| Rani Khedira | DM | Eric Anders Smith | DM |
| Nico Schlotterbeck | CB | Andreas Hanche-Olsen | CB |
| Rasmus Kristensen | FB | Vincenzo Grifo | Winger |

The most striking, football-coherent part: even within goalkeepers
specifically, there's real spread -- some (Nicolas, Gulácsi, Nübel,
Vasilj) get pressed far more than others (Grabara, Rønnow, Kobel,
Schwäbe get 3-6m more space than a typical keeper's baseline), plausibly
reflecting which keepers HSV respects enough in build-up to press
higher against vs. which they leave alone. Same story among center-backs
-- recognizable, composed ball-players (Chiarodia, Coulibaly, Lukeba,
Hanche-Olsen) get real extra space beyond what their role alone would
predict, a genuinely more specific and useful signal than the earlier,
confounded version.

**Residual limitation, disclosed rather than hidden:** within-role
position correlation isn't fully zero for every role (Full Back -0.532,
Center Back -0.373, Defensive Mid -0.349) -- some roles still show a
player-plays-deeper-within-their-role effect. Smaller than the original
confound by a wide margin, but real; treat the ranking as a strong
signal, not a perfectly clean one.
