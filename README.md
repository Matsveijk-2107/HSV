# HSV Pressing Dashboard

A season-long pressing analytics dashboard for Hamburger SV's 2025-26
Bundesliga campaign (34 matches), built on **TPR (Team Pressing Response)**,
a composite metric scoring how well a team presses at every moment it
doesn't have the ball.

TPR itself comes from a Master's thesis, *"Team Pressing Response Metrics
for Professional Football Analytics"* (Tilburg University, Data Science &
Society). This dashboard is a separate, applied extension of that work:
the same six component metrics, recomputed on HSV's own real tracking and
event data and checked against 1,255 real defensive breakdowns from the
season, rather than the synthetic Eredivisie dataset the thesis itself used.

**Live app:** deployed on Streamlit Community Cloud from this repository.

## What it shows

- **Executive Summary**: the headline findings from every page, one screen.
- **Pressing Phases** / **Where It Goes Wrong**: the core statistical
  result — of TPR's six dimensions, only **Synchronization** (whether the
  back line shifts as one coordinated block) is confirmed to actually
  predict real breakdowns, tested against a random baseline
  (p = 5.4×10⁻¹²⁷, robust across seeds, window definitions, and a tempo
  confound check). Every other dimension moves the *opposite* direction
  near a breakdown — a mechanical artifact of the ball being close to
  goal, not a real defensive cause.
- **Synchronization Attribution**: per-player breakdown of the one
  validated cause, cross-checked against an independent method.
- **Player Weakness Finder** / **Best Defender**: which players are
  furthest out of position, or closest to the block, at real danger
  moments — with a per-player dimension drill-down.
- **Opponent Playmaker Impact**: which opposing players get more time on
  the ball than their position alone predicts, controlled for role.
- **Match Explorer**: pick a match and a minute window, see the
  frame-level shape underneath the season averages.
- **Visual Examples**: real pitch plots (via `mplsoccer`) for the extreme
  frames of each dimension.
- **Season Patterns**: matchday trend, home/away, fatigue, live game
  state, weather — what actually moves pressing intensity and what's a
  checked-and-ruled-out null result.
- **Restarts, Triggers & Recovery**: corners, throw-ins, goal-kicks,
  backpass-to-keeper pressing, and how fast HSV wins the ball back.
- **Frame-Level Mistake Attribution**: every defending frame rather than
  just real danger moments; flagged with its own caveats, see the page.

Every number traces back to a saved result CSV in `results/`; nothing is
computed live in the app. A finding is only called a *cause* once it's
tested against a random baseline from the same context, not just observed
to look different from a raw count. A "How to read this" glossary
(percentile, shift, p-value, validated vs. exploratory, confident vs.
exploratory tier) is available from every page's header.

## Data

No raw tracking or event data is included. `results/` and
`data/checkpoints/` hold only already-aggregated, already-anonymized-where-
relevant CSV outputs (per-match, per-player, per-frame summaries) — the
inputs a match analyst would actually work from, not the underlying
StatsBomb/DFL feeds.

## Running locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app/Home.py
```

Requires Python 3.13 (see `runtime.txt`). `.streamlit/config.toml` pins a
light theme regardless of the visitor's OS setting.

## Structure

```
streamlit_app/
  Home.py                 Landing page: methodology, formula, navigation
  utils.py                Shared theme, colors, glossary, loaders
  pages/                  12 dashboard pages (numbered = sidebar order)
  data/                   Small prep tables specific to the app
frame_diagnostics.py       Frame-level lookup used by Match Explorer
results/                   Per-analysis output CSVs + visual_validation/*.png
data/checkpoints/          Per-match aggregated tracking/event data
Hamburger_SV_logo.svg
requirements.txt / runtime.txt / .streamlit/config.toml
```
