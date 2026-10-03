# TrustDTI

An uncertainty-aware drug–protein interaction network with evidence-guided drug repurposing. MSc Data Science & AI research project, 12 weeks.

TrustDTI predicts whether an existing drug interacts with a human protein, attaches a **calibrated** confidence to the prediction, looks up (never predicts) whether the protein is linked to a disease, and uses both signals to decide what scientific literature an AI agent searches for: supporting evidence when the model is confident, counter-evidence when it is not. The research question is whether that adaptive search beats a fixed one.

**Current state:** project Week 1 (data profiling) is complete and awaiting review. See [`docs/STATUS.md`](docs/STATUS.md) for exactly where things stand and what is next.

## Pick up where you left off (new session, new IDE, lost history)
Open the folder `C:\Users\91701\code\Trust_DTI` (not the old OneDrive copy), then paste this to your AI assistant:

> Read `AGENTS.md`, then `docs/STATUS.md` and the top 3 entries of `docs/PROJECT_LOG.md`. Tell me in 5 lines where we are and what you suggest next, then wait for me. I am still learning this project, so explain simply and one pipeline stage at a time.

Antigravity loads `AGENTS.md` from the project root automatically. Claude Code loads `CLAUDE.md`, which points to the same files.

## Where to read what
| I want… | Read |
|---|---|
| Where we are, what is next, open decisions | [`docs/STATUS.md`](docs/STATUS.md) |
| What happened, session by session | [`docs/PROJECT_LOG.md`](docs/PROJECT_LOG.md) |
| The whole project explained | [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) |
| One pipeline stage in depth | [`docs/stages/`](docs/stages/README.md) |
| Interactive explainers (open in a browser) | [`docs/interactive/`](docs/interactive/) |
| Every methodological decision and why | [`DECISIONS.md`](DECISIONS.md) |
| The Week 1 data report | [`docs/stage0_report.md`](docs/stage0_report.md) |
| How the raw data were obtained and verified | [`data/MANIFEST.md`](data/MANIFEST.md) |
| The original full plan | [`CLAUDE_CODE_BRIEFING.md`](CLAUDE_CODE_BRIEFING.md) |

## Quick start
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
pytest
```
Raw data (ChEMBL 37, 30 GB; BindingDB 202609) are not in the repo; `data/MANIFEST.md` lists exact sources, sizes and checksums.

## Habit that keeps this working
At the end of every session: add a dated entry at the top of `docs/PROJECT_LOG.md`, update `docs/STATUS.md`, record decisions in `DECISIONS.md`, commit, push.
