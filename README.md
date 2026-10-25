# TrustDTI

An uncertainty-aware drug–protein interaction network with evidence-guided drug repurposing. MSc Data Science & AI research project, 12 weeks.

TrustDTI predicts whether an existing drug interacts with a human protein, attaches a **calibrated** confidence to the prediction, looks up (never predicts) whether the protein is linked to a disease, and uses both signals to decide what scientific literature an AI agent searches for: supporting evidence when the model is confident, counter-evidence when it is not. The research question is whether that adaptive search beats a fixed one.

**Current state (25 Oct 2026):** Stages 1 (data) and 2 (Network 1) are built and verified. Stage 3 has passed a small embedding pilot: 2,312 protein sequences were retrieved and checked; ChemBERTa produced 100 compound vectors of dimension 384; ESM-2 produced 20 protein vectors of dimension 320. Full-scale embeddings and DTI model training/evaluation are not yet complete. See [`docs/STATUS.md`](docs/STATUS.md).

## Pick up where you left off
Open the working folder `C:\Users\91701\code\Trust_DTI` (not the old OneDrive copy), then ask your assistant:

> Read `AGENTS.md`, then `docs/STATUS.md` and the top 3 entries of `docs/PROJECT_LOG.md`. Tell me in 5 lines where we are and what you suggest next, then wait for me. I am still learning this project, so explain simply and one pipeline stage at a time.

## Where to read what
| I want… | Read |
|---|---|
| Current state, next actions, open decisions | [`docs/STATUS.md`](docs/STATUS.md) |
| Session history | [`docs/PROJECT_LOG.md`](docs/PROJECT_LOG.md) |
| Project overview and research question | [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) |
| Pipeline stage teaching notes | [`docs/stages/`](docs/stages/README.md) |
| Methodological decisions | [`DECISIONS.md`](DECISIONS.md) |
| Weekly course reports | [`docs/weekly_reports/`](docs/weekly_reports/README.md) |
| Week 7 report and infographic | [`docs/weekly_reports/week07_embedding_pilot/`](docs/weekly_reports/week07_embedding_pilot/) |
| Raw data sources and checksums | [`data/MANIFEST.md`](data/MANIFEST.md) |

## Quick start
```bash
python -m venv .venv
.venv/Scripts/activate
pip install -r requirements.txt
python -m pytest -q
```

Raw ChEMBL and BindingDB datasets are not in the repository; `data/MANIFEST.md` lists sources, sizes, and checksums. Do not commit raw databases, local environments, or caches.
