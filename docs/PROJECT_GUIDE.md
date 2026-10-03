# TrustDTI Project Guide

The whole project in one document. Written so a newcomer (or an AI assistant with no memory) can understand what is being built, why, how far it has got, and where everything lives. For *where we are today* read `STATUS.md`; for history read `PROJECT_LOG.md`.

Contents: 1 Idea · 2 Research question · 3 System · 4 Two networks · 5 Router · 6 Evidence · 7 Data rules · 8 Sacred rules · 9 Schedule · 10 Tools · 11 Out of scope · 12 Decisions · 13 Stage 0 numbers · 14 Repo map · 15 How to run · 16 Glossary · 17 Further material

---

## 1. The idea
Drug repurposing means finding a new use for a medicine that is already known to be safe. Models that suggest "drug X may bind protein Y" are common. The bottleneck is knowing which of thousands of suggestions deserve a researcher's time. A raw probability does not say whether the model can be trusted on *this* protein, and people checking the literature tend to look for confirming evidence, so the weakest predictions get challenged least.

TrustDTI (Trust + Drug–Target Interaction):
1. predicts drug–protein interaction with a small trained model;
2. converts each prediction into a **calibrated** state using conformal prediction: confident-active `{1}`, genuinely uncertain `{0,1}`, confident-inactive `{0}`, with a statistical coverage guarantee;
3. **looks up** (never predicts) whether the protein is linked to a disease, using curated databases;
4. lets those two signals decide what an AI agent searches for. Confident → mechanism and disease-context evidence. Uncertain → counter-evidence and safety signals first.

Elevator sentence: *TrustDTI builds a calibrated drug–protein interaction network anchored to disease biology, and tests whether the statistical uncertainty of each prediction can be used to decide what scientific evidence an AI agent should go and look for, confirming when the model is confident and actively trying to falsify itself when it is not.*

## 2. The research question (locked)
> Does conditioning literature-evidence retrieval on calibrated prediction uncertainty (plus a disease-relevance signal) improve evidence precision and counter-evidence recall, compared with a fixed retrieval policy applied to the same candidates?

It is written so it can fail. If adaptive retrieval does not beat fixed retrieval, that is the finding and is reported honestly.

**What is not novel** (say it before a reviewer does): DTI prediction with neural encoders; conformal prediction applied to DTI; uncertainty-adaptive retrieval in general RAG; agentic evidence-seeking for repurposing.
**The one actual claim:** an *externally calibrated* signal from a molecular prediction model controlling the *search behaviour* of a retrieval agent, as opposed to a system reasoning about its own confidence. A literature re-audit is scheduled for Week 9; if anyone finds work that already does exactly this, flag it immediately.

## 3. The system: 13 stages
**Offline, built once and cached**

| # | Stage | What it does | Tools | Status |
|---|---|---|---|---|
| 1 | Data | Restrict ChEMBL 37 to human single-protein targets; profile; cross-check BindingDB | ChEMBL, BindingDB, SQLite, pandas | **done** |
| 2 | Network 1 | Standardise molecules, map proteins, aggregate repeats, three-state label, four splits, leakage check | RDKit, pandas | next |
| 3 | Embeddings | Drug and protein vectors from frozen pretrained models, cached | ChemBERTa, ESM-2 (Colab/Kaggle GPU) | planned |
| 4 | Fusion head | The **only trained component**: MLP over drug + protein vectors → probability | PyTorch, MLflow | planned |
| 5 | Evaluation | Random / drug-cold / target-cold / temporal splits, stratified by family | scikit-learn | planned |
| 6 | Conformal calibration | Probability → `{1}`, `{0,1}`, `{0}` with coverage guarantee | MAPIE or custom | planned |
| 7 | Network 2 | Add curated protein–disease links → anchor strength | Open Targets, DISGENET | planned |

**Online, per query, in seconds**

| Step | What it does |
|---|---|
| A Query | Forward: drug → targets → diseases. Reverse: disease → proteins → drugs |
| B Router | Conformal state × anchor strength → one of 7 policies (plain code) |
| C Evidence retrieval | Policy-specific search of PubMed/PubTator (ChromaDB, sentence-transformers) |
| D Structured extraction | Passage → typed record with direction and citation |
| E Grounded synthesis | LLM writes the report from records only (LangGraph, pinned open-weight LLM) |
| F Report | Prediction + calibrated confidence + disease anchor + cited evidence (Streamlit) |

## 4. Two networks: never mix them
| | Network 1: compound–protein | Network 2: compound–protein–disease |
|---|---|---|
| Nodes | compounds, proteins | + diseases |
| Edge | measured / **predicted** interaction, with probability and conformal set | + **curated** protein–disease association with a score |
| Built | Weeks 1–6 | Week 8 |

Predicted and curated edges go in separate tables or carry an explicit `provenance` column (`"predicted"` / `"curated"`) from the first script that touches them.

## 5. The router
Deterministic, unit-tested code. Never an LLM, so the most consequential decision is reproducible.

| Model says | Disease anchor | Policy | Searches for |
|---|---|---|---|
| `{1}` | Strong | CONFIRM | mechanism + disease context |
| `{1}` | Moderate | CONTEXTUALISE | disease linkage, mechanism secondary |
| `{1}` | Weak/none | INVESTIGATE | general background |
| `{0,1}` | Strong | CHALLENGE | counter-evidence and safety first |
| `{0,1}` | Moderate | CHALLENGE+CONTEXT | counter-evidence, then disease linkage |
| `{0,1}` | Weak/none | LOW_PRIORITY | minimal search |
| `{0}` | any | STOP | no retrieval |

## 6. Evidence categories and the UNKNOWN rule
Categories: **MECHANISTIC** (does the drug hit the protein?), **DISEASE_CONTEXT** (does the protein matter for the disease?), **COUNTER** (what would make this wrong?), **SAFETY** (reason not to pursue?).
Every retrieved item becomes a record with direction `SUPPORT`, `CONTRADICT` or `UNKNOWN`. `UNKNOWN` means "nothing relevant found" and is **never** converted to `CONTRADICT`; doing so would discard genuinely novel candidates.

## 7. Data rules (apply from the first script)
1. **Three-state label.** ACTIVE (measured, meaningfully active), INACTIVE (measured, not active under the stated conditions), UNTESTED (no usable measurement). UNTESTED is never converted to INACTIVE. This is a positive-unlabelled setting and is stated openly.
2. **Censored values are not exact values.** `standard_relation` can be `>`, `<`, `>=`, `<=`, `>>`, `<<`. Example: ChEMBL activity 884645, imatinib vs FLT3, IC50 > 30,000 nM means "no activity found up to 30 µM". ChEMBL leaves pChEMBL empty for every such row, so filtering on `pchembl_value IS NOT NULL` silently deletes all of them (for imatinib it keeps 833 of 4,878 rows). Never apply that filter.
3. **Keys.** Compounds join on InChIKey (not SMILES); proteins on UniProt accession.
4. **Splits** (all four required): random; drug-cold (Bemis–Murcko scaffold computed *before* splitting); target-cold (the primary test); temporal. The calibration set is carved from training data only and must be provably disjoint from every test split.

## 8. Rules that never change silently
1. The research question (section 2).
2. The **blinding protocol**: six retrospective test cases are written to `cases/sealed.json` in Week 8 and not read, referenced or used to influence any decision until the Week 9 step that opens them.
Everything else may evolve, but changes are recorded in `DECISIONS.md`.

## 9. Schedule (authoritative: Briefing / Master Plan, D-002)
10 build weeks + 2 reserved buffer weeks. Each phase has a gate that must pass, or be waived in writing, before the next starts.

| Weeks | Phase | Gate |
|---|---|---|
| 1–2 | Data foundation | Both databases profiled; scope and label policy justified by real numbers (not waivable) |
| 3 | Network 1 | Versioned table, three-state labels, four splits, passing leakage check |
| 4–5 | Representation + fusion head | Embeddings cached; model beats classical baselines |
| 6 | Honest evaluation | Four splits × family reported; shift gap documented |
| 7 | Conformal calibration | Empirical coverage matches target; uncertainty rises under harder splits |
| 8 | Network 2 + router | Anchor built; both query directions work; six cases sealed |
| 9 | Evidence system + **central experiment** | Fixed-vs-adaptive run; sealed cases opened |
| 10 | Delivery | Demo, report, rehearsed defence |
| 11–12 | Buffer | Absorb delay first; depth second; never new scope |

**If time runs short, protect Weeks 7, 8 and 9 first.** The contribution is what happens after the prediction, not the predictor.
**Course report weeks vs project weeks:** the course's weekly progress reports are numbered separately. Course Weeks 2 and 3 both describe project Week 1.
**People:** two team members. Role A: data, biology, modelling, evaluation, scientific writing. Role B: engineering, environment, tracking, orchestration, interface, deployment. Both: design decisions and reviews.

## 10. Tools and why
RDKit (molecule standardisation, scaffolds) · pandas/PyArrow (curation, Parquet) · ChemBERTa and ESM-2, **frozen** (representations) · PyTorch (the one trained model) · scikit-learn/XGBoost (baselines to beat) · MAPIE or custom (conformal) · Open Targets/DISGENET (disease anchor) · PubTator + NCBI E-utilities (literature) · sentence-transformers + ChromaDB (semantic search) · LangGraph (orchestration) · a pinned open-weight LLM, prompted only (D-003) · MLflow (every run logged with its data version) · Streamlit (interface). Nothing outside this list is added without discussion.

## 11. Out of scope
Custom knowledge graph / Neo4j, imaging or transcriptomic fusion, docking, LLM fine-tuning (LoRA/QLoRA), a wet-lab experiment recommender, a second disease-prediction model, and chasing benchmark-leading DTI accuracy. New ideas go in the final report as future work.

## 12. Decisions so far (full text in `DECISIONS.md`)
| ID | Decision |
|---|---|
| D-001 | Universal scope: all human single-protein targets, reported per family (not kinome-only) |
| D-002 | Schedule of record: Briefing / Master Plan (10 + 2 weeks) |
| D-003 | No local GPU; embeddings on Colab/Kaggle/HPC; free pinned open-weight LLM, no paid API |
| D-004 | Working repo is `C:\Users\91701\code\Trust_DTI`, outside OneDrive |
| D-005 | ChEMBL 37 and BindingDB 202609, each verified against the publisher's checksum |
| D-006 | Family assignment: walk ChEMBL's protein tree to level 1 and 2; conflicts → "Multiple" |
| D-007 | Censored operators are `> < >= <= >> <<`; never filter on pChEMBL |
| D-008 | Overlap measured on independent records; ChEMBL-only for v1 *recommended, not yet approved* |
| D-009 | "inconclusive", "not determined", "nd", "na" are not inactive |
| D-010 | The ~1 h full-database test is marked `slow` and excluded by default |

## 13. Stage 0 numbers (ChEMBL 37, human single-protein)
| Fact | Value | Source file |
|---|---|---|
| Activity rows (of 24,527,044 in ChEMBL) | 8,299,186 | `chembl_extract_stats.json` |
| Proteins / compounds / pairs | 5,738 / 1,559,417 / 5,064,882 | `chembl_profile_summary.json` |
| Approved drugs (max phase 4) | 2,685 | same |
| Censored rows (all without pChEMBL) | 810,994 | same |
| Busiest 10% of proteins hold | 88% of pairs | same |
| Proteins with fewer than 10 partners | 2,883 | same |
| Rows with no publication year | 39.8% | `d4_missingness.csv` |
| Candidate measured-inactive pairs | ~1.04M (estimate) | `chembl_profile_summary.json` |
| Naive vs independent ChEMBL∩BindingDB pairs | 872,761 vs 66,145 (~13×) | `d3_overlap.csv` |
| Families where PubChem shifts median pChEMBL by more than 1 log unit | 5 | `pchembl_source_confounding.csv` |
| Pairs with more than one record | 28.0% | `stage2_probe_output.txt` |

## 14. Repo map
```
AGENTS.md                 entry point for AI assistants (auto-loaded by Antigravity)
CLAUDE.md                 same idea for Claude Code
README.md                 front door
DECISIONS.md              every methodological choice, dated (D-NNN)
CLAUDE_CODE_BRIEFING.md   the original full plan and rules (history; repo wins on conflict)
docs/
  PROJECT_GUIDE.md        this file
  STATUS.md               where we are now, next actions, open decisions
  PROJECT_LOG.md          diary, newest first
  stages/                 one teaching note per pipeline stage
  interactive/            two interactive explainer pages (open in a browser)
  stage0_report.md        Week 1 data report and open-issue list
  chembl_schema_notes.md  the ChEMBL tables we use and how they join
  weekly_reports/         course progress reports, form text, figures, PDFs
src/
  config.py               paths and pinned data versions
  ingest/                 chembl_extract, bindingdb_extract, profile_*, families, relations, probe_stage2_issues
tests/                    10 tests (9 fast, 1 slow)
reports/stage0/           every small result file the scripts produce (committed)
data/MANIFEST.md          provenance of every raw file; data/raw and data/interim are gitignored
notebooks/                01_chembl_first_look.ipynb (imatinib censoring check)
requirements.in / .txt    direct dependencies / pinned freeze
```

## 15. How to run
```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
pytest                                   # fast tests
python -m src.ingest.chembl_extract      # needs data/raw/chembl_37 (see data/MANIFEST.md)
python -m src.ingest.bindingdb_extract
python -m src.ingest.profile_chembl
python -m src.ingest.profile_overlap
python -m src.ingest.profile_source_confounding
```
Figures and PDFs for weekly reports: `python docs/weekly_reports/_build/figures.py` then `python docs/weekly_reports/_build/render.py` (needs Chrome or Edge).

## 16. Glossary
- **ChEMBL**: EMBL-EBI's curated database of bioactivity measurements (24.5M in release 37).
- **BindingDB**: a smaller binding-measurement database; largely overlaps ChEMBL.
- **UniProt accession**: the standard ID of a protein (FLT3 = P36888).
- **InChIKey**: a standard fingerprint of a molecule's structure; the first 14 characters encode its skeleton.
- **SMILES**: a text notation for a molecule; the same molecule can have several spellings.
- **Activity / measurement**: one recorded experiment result for a drug–protein pair.
- **IC50, Ki, Kd, EC50**: potency measures (lower concentration = stronger drug).
- **pChEMBL**: −log10 of molar potency (7 = 100 nM); only exists for exact values.
- **Censored measurement**: a bound such as "IC50 > 30,000 nM", not an exact value.
- **Target family**: ChEMBL's protein classification (e.g. Enzyme > Kinase).
- **Scaffold (Bemis–Murcko)**: a molecule's core ring system with side chains removed.
- **Cold split**: test set made of drugs (by scaffold) or proteins never seen in training.
- **Leakage**: information from the test set getting into training, which inflates results.
- **Embedding**: a vector of numbers representing a molecule or protein; ChemBERTa for drugs, ESM-2 for proteins.
- **Fusion head**: the small neural network that combines two embeddings into one probability.
- **Calibration / conformal prediction**: turning a score into a set `{1}`, `{0,1}`, `{0}` with a coverage guarantee, assuming exchangeability.
- **Disease anchor**: strength of a *curated* protein–disease link.
- **Positive-unlabelled**: most unlabelled pairs are unknown, not negative.
- **Provenance**: whether an edge was `predicted` or `curated`.

## 17. Further material
- `docs/stages/README.md`: index of the stage teaching notes.
- `docs/interactive/TrustDTI_Explained.html` (concept and architecture) and `TrustDTI_Pipeline.html` (all 13 stages with real numbers): open in a browser. They load fonts from Google Fonts; without internet they still work with fallback fonts.
- The same two pages were published as private claude.ai artifacts: TrustDTI Explained (`https://claude.ai/artifact/V2ytHoyZZax6wBjosdFEte`), TrustDTI Pipeline (`https://claude.ai/artifact/77NbVdTWghovZeU61vR1MH`). Only the owner can open them.
- The owner's original planning PDFs (Master Plan, Project Bible, 12-Week Working Protocol, Project Submission) are not in the repo. Where they conflict, `DECISIONS.md` records which one won.
- `CLAUDE_CODE_BRIEFING.md`: the long-form plan with week-by-week tasks, risks and fallbacks (Part 5) and the questions to be ready to answer (Part 6).
