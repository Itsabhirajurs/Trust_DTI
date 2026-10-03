# TrustDTI: instructions for any AI assistant (read this first)

**Project.** TrustDTI is a 12-week MSc research project. It predicts whether an existing drug interacts with a human protein, attaches a *calibrated* confidence to each prediction, looks up (never predicts) the protein's disease link, and uses both signals to decide what literature an AI agent searches for. Confident → look for supporting evidence. Uncertain → look for counter-evidence. Details: `docs/PROJECT_GUIDE.md`.

**The owner is learning this project** and is not yet fluent in it. Explain simply, give the *why* before the *how*, go **one pipeline stage at a time**, and do not jump ahead until they say so. When you explain something, save it under `docs/stages/`.

## Start of every session (do this before anything else)
1. Read `docs/STATUS.md`: where we are, what is next, open decisions.
2. Skim the **top 3 entries** of `docs/PROJECT_LOG.md` (newest first).
3. Need background? `docs/PROJECT_GUIDE.md`. Need one stage in depth? `docs/stages/`.
4. Tell the owner in ~5 lines where we are and what you propose next. Then wait.
5. The repo and data are ground truth. If a doc disagrees with the code or data, trust the repo and flag the conflict.

## Rules that never change silently
- **Research question** (exact wording in the guide §2) and the **blinding protocol**: never open `cases/sealed.json` before the Week 9 step that allows it.
- **UNTESTED is never INACTIVE.** Keep censored rows (`>`, `<`, `>=`, `<=`, `>>`, `<<`). Never filter on `pchembl_value IS NOT NULL`. "inconclusive" is not inactive.
- The **router is deterministic, unit-tested code**, never an LLM decision. UNKNOWN is never turned into CONTRADICT.
- Compound–protein edges (predicted) and protein–disease edges (curated) live in separate tables or carry a `provenance` column.
- Every methodological choice goes into `DECISIONS.md` (`D-NNN`, dated, with why and evidence) when it is made.
- No new scope (knowledge graph, docking, LLM fine-tuning, etc.) without a flagged discussion first.
- Raw and interim data are never committed. Small derived results in `reports/` are.
- Do not invent numbers. Every figure must come from a file in `reports/` or a query on the data.

## End of every session
1. Add a dated entry at the **top** of `docs/PROJECT_LOG.md` (template inside that file).
2. Update `docs/STATUS.md` (current state, next actions, open decisions).
3. Record new decisions in `DECISIONS.md`.
4. Commit with a message that says what changed and why, then push to `main`.

## Working environment
- Open the folder `C:\Users\91701\code\Trust_DTI`. The copy in OneDrive is an old backup with no data. Do not work there.
- Python 3.12 virtual environment at `.venv` (Windows: `.venv\Scripts\activate`). Install: `pip install -r requirements.txt`.
- Tests: `pytest` (fast, about 2 s). `pytest -m slow` is a ~1 hour full-database check, run only before a data-version change.
- Raw data are in `data/raw/` (gitignored). How they were obtained and verified: `data/MANIFEST.md`. No GPU on this laptop; heavy embedding jobs go to Colab/Kaggle/HPC (`DECISIONS.md` D-003).
- Run scripts as modules from the repo root, e.g. `python -m src.ingest.profile_chembl`.
