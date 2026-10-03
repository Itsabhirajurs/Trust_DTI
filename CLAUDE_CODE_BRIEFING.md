# TrustDTI — Claude Code Briefing

**Read this entire file before touching any code.** This is not a summary — it is the full context of a research project that is already carefully scoped, and the scoping decisions in here exist *because* earlier, larger versions of this project failed to fit a 12-week timeline. Re-litigating those decisions from scratch (e.g. "wouldn't it be better to also add a knowledge graph") wastes time and re-introduces risks that have already been deliberately designed out. Extend what's here; don't redesign it without flagging the reason first.

If anything in this file conflicts with what you observe in the actual repo (code, data, `DECISIONS.md`), **the repo is ground truth** — this file describes intent and history, but reality (what's actually on disk, what a query actually returns) always wins. When you find a conflict, don't silently pick one — surface it in your own update to this file (see **Part 8**) and ask.

---

## Part 0 — How to work on this project

### 0.1 Your operating instructions, specifically

- You have GitHub access to this repo. Work directly in it. Commit and push at the end of every meaningful unit of work — a finished day's task, a working script, a passing test — not at the end of a whole week. Small, frequent, honestly-described commits are what this project's provenance depends on.
- Every commit message should say what changed and, where relevant, *why* — not just `wip` or `fixes`.
- Before writing new code for a task, check whether `DECISIONS.md` or this file already answers the design question. If it does, follow it. If it's silent, make the smallest reasonable decision, implement it, and **write down what you decided and why** in `DECISIONS.md` before moving on. Undocumented decisions are the single most damaging failure mode for this project, because the final report depends entirely on being able to reconstruct why the pipeline works the way it does.
- You are expected to do your own research where this file doesn't already give you the answer — database schemas, library APIs, current best practice for a technique. Search for it, read primary documentation over blog summaries where possible, and **cite what you relied on** in your commit message or in `DECISIONS.md` when a design choice depended on something you looked up.
- Give feedback proactively. If a plan in this file looks wrong once you're looking at real data (e.g. a class-imbalance assumption that turns out false, a split that turns out to leak), say so immediately, explain the evidence, and propose a fix — don't quietly work around it or quietly follow a plan you can see is broken.
- At the end of each work session, update **Part 8 (Running Log)** at the bottom of this file with a short dated entry: what you did, what you found, what changed versus the plan, what's still open. This file is meant to stay current — it is not a static spec you read once.

### 0.2 The two things that must never quietly change

1. The research question in **Part 1.3**.
2. The sealed-case protocol in **Part 5, Week 8/9** — those six cases, once written to `cases/sealed.json`, are not to be read, referenced, or used to influence any decision until the point in Week 9 explicitly described below. This is a blinding protocol; breaking it silently invalidates the project's central experiment.

Everything else can evolve. These two cannot change without an explicit, flagged conversation first.

### 0.3 Working rhythm

The project runs on a 10-week build + 2-week buffer plan (detailed fully in Part 5). At any point, the most useful question to ask is: *which week/day are we on, what is that day's gate, and does today's work satisfy it?* Don't jump ahead to later weeks' work even if it seems easy or tempting — later weeks depend on artifacts (splits, calibration sets, sealed cases) that don't exist yet, and building ahead of them risks building on a foundation that later turns out wrong.

---

## Part 1 — What TrustDTI is

### 1.1 One paragraph

TrustDTI predicts whether an existing drug is likely to interact strongly with a human protein it was not originally designed for, states honestly how much that specific prediction can be trusted using a calibrated statistical method (not just a raw probability), looks up — rather than predicts — whether that protein is genuinely linked to a disease using curated biological databases, and then lets those two facts together decide what kind of scientific literature an AI agent goes and searches for. When the system is confident, it looks for evidence explaining *why* the prediction might be right. When it is uncertain, it deliberately goes looking for evidence that the prediction might be *wrong*. The system is built once as a large drug–protein network and can then be queried in either direction: from a drug, to find new diseases it might treat, or from a disease, to find existing drugs that might treat it.

### 1.2 The one sentence for anyone external (supervisor, panel, teammate)

> TrustDTI builds a calibrated drug–protein interaction network anchored to disease biology, and tests whether the statistical uncertainty of each prediction can be used to decide what scientific evidence an AI agent should go and look for — confirming when the model is confident, and actively trying to falsify itself when it is not.

### 1.3 The research question this project exists to test

> Does conditioning literature-evidence retrieval on calibrated prediction uncertainty (plus a disease-relevance signal) improve evidence precision and counter-evidence recall, compared with a fixed retrieval policy applied to the same candidates?

This question is written so it can fail. If uncertainty-adaptive retrieval does *not* beat fixed retrieval, **that is the finding** — it gets reported honestly, not adjusted until it looks better. See Part 5, Week 9 for exactly how this is tested.

### 1.4 What is deliberately NOT the novelty claim here

Say this plainly, to a supervisor or a reviewer, before they say it to you:

- Drug–protein interaction prediction with graph/sequence encoders — a very active, crowded research area. Not novel.
- Conformal prediction applied to DTI — already published elsewhere. Not novel.
- Uncertainty-adaptive retrieval in general RAG systems — an established subfield (Adaptive-RAG, SUGAR, ConfRAG, TRAQ). Not novel.
- Agentic, evidence-seeking drug-repurposing reasoning — close prior work exists (RareAgent, CLADD, DrugMCTS). Not novel.

**What has not been directly demonstrated**, and is this project's actual claim: an externally calibrated statistical signal from a molecular prediction model controlling the evidence-acquisition *behaviour* of a retrieval agent evaluating a biological hypothesis — as distinct from a system reasoning about its own self-referential uncertainty. That narrow, specific coupling is what gets tested. A literature re-audit against the newest work in this space is scheduled for Week 9 before this claim is finalised in writing — if you find something that already does exactly this during your own research along the way, **flag it immediately**, don't wait for Week 9.

### 1.5 The two network objects — do not conflate these

This project builds two related but structurally different objects. Confusing them, or storing them in one undifferentiated table, breaks the disease-anchor design at its root.

| | **Network 1 — Compound–Protein** | **Network 2 — Compound–Protein–Disease** |
|---|---|---|
| Node types | Compounds, proteins only | Compounds, proteins, diseases |
| Edge types | One — measured/predicted interaction | Two structurally different kinds (see below) |
| Where it's used | Trains the fusion head; conformal calibration operates over it | Built by joining Network 1's predictions to a curated disease-association lookup |
| Built in | Weeks 1–6 | Week 8, on top of the finished Network 1 |

**The trap to avoid:** Compound–protein edges are *inferred* by a trained model and carry a probability plus a conformal prediction set. Protein–disease edges are *looked up* from a curated resource (Open Targets / DISGENET) and are never predicted — they carry a curated association score instead. If these two edge types end up in one undifferentiated table, the system loses the distinction its entire disease-anchor design depends on. **Store them as two separate tables, or two edge types with an explicit `provenance` column (`"predicted"` vs `"curated"`), from the very first script that touches them.**

---

## Part 2 — Full system architecture

### 2.1 Offline half — built once, cached

```
DATA                    ChEMBL + BindingDB, profiled and filtered
   ↓
NETWORK 1               Compound–Protein: cleaned, three-state labelled,
                        four splits defined
   ↓
EMBEDDINGS              ChemBERTa / GNN (frozen) + ESM-2 (frozen),
                        cached once for the whole universe
   ↓
FUSION HEAD             The ONE trained component → interaction probability
   ↓
EVALUATION              Random / drug-cold / target-cold / temporal splits,
                        stratified by target family
   ↓
CONFORMAL CALIBRATION   Probability → prediction set {1} / {0,1} / {0},
                        with a coverage guarantee
   ↓
NETWORK 2               Network 1 + curated protein–disease edges
                        (Open Targets / DISGENET) → anchor strength
```

### 2.2 Online half — per user query, in seconds

```
QUERY                   Forward: a drug → candidate targets → diseases
                        Reverse: a disease → associated proteins → drugs
   ↓
DUAL-SIGNAL ROUTER      conformal state × disease-anchor strength
                        — deterministic, unit-tested CODE, not a model
                          decision. This is intentional: the single most
                          consequential decision in the system must be
                          reproducible, so it is never made by an LLM.
   ↓
   ┌─────────────────┬──────────────────────┬──────────────────┐
   CONFIRM /          CHALLENGE /            STOP /
   CONTEXTUALISE      CHALLENGE+CONTEXT      LOW_PRIORITY
   (seeks support)    (seeks falsification)  (conserves budget)
   └─────────────────┴──────────────────────┴──────────────────┘
   ↓
EVIDENCE RETRIEVAL      Policy-specific search across MECHANISTIC,
                        DISEASE_CONTEXT, COUNTER, SAFETY categories
   ↓
STRUCTURED EXTRACTION   passage → typed record: drug, protein, disease,
                        type, direction (SUPPORT/CONTRADICT/UNKNOWN),
                        study system, citation, source span
   ↓
GROUNDED SYNTHESIS      LLM writes the report from records ONLY —
                        no claim without a matching citation. A claim
                        with no matching record is rejected before it
                        reaches the report.
   ↓
REPORT                  Prediction + calibrated confidence + disease
                        anchor + evidence, ranked, fully traceable
```

### 2.3 The dual-signal router — full logic table

The router combines the conformal state (how certain the model is) with the disease-anchor strength (how well-established the protein–disease link is) into one policy. This is plain, unit-tested code — implement it as such, not as a prompt to an LLM.

| Conformal state | Disease anchor | Policy | What the agent searches for |
|---|---|---|---|
| `{1}` confident-active | Strong | CONFIRM | Mechanistic + disease-context evidence |
| `{1}` confident-active | Moderate | CONTEXTUALISE | Disease-linkage evidence, mechanism secondary |
| `{1}` confident-active | Weak / none | INVESTIGATE | General background — curated context is thin |
| `{0,1}` uncertain | Strong | CHALLENGE | Counter-evidence and safety signals *first* |
| `{0,1}` uncertain | Moderate | CHALLENGE+CONTEXT | Counter-evidence, then disease linkage |
| `{0,1}` uncertain | Weak / none | LOW_PRIORITY | Minimal search — conserve budget |
| `{0}` confident-inactive | Any | STOP | No retrieval — spending budget here returns nothing useful |

**Why deterministic, restated:** if a language model chose the policy, the most consequential decision in the whole system would be irreproducible and unfalsifiable as a claim. The router is ordinary code specifically so this doesn't happen.

### 2.4 Evidence categories and the UNKNOWN rule

Four evidence categories, chosen because they mirror the reasoning chain a pharmacologist actually follows:

- **MECHANISTIC** — does the drug actually affect this protein? (binding, inhibition, target engagement)
- **DISEASE_CONTEXT** — does this protein matter for this disease? (pathway involvement, genetic evidence)
- **COUNTER** — what would make this prediction wrong? (failed efficacy, negative assays, contradictory studies)
- **SAFETY** — even if it works, is there a reason not to pursue it? (toxicity, off-target effects, terminated trials)

Every retrieved item becomes a structured record — drug, protein, disease, evidence type, **direction**, study system, citation, source span. The LLM summarises these records; it does not invent claims outside them.

**Direction has three values, not two:** `SUPPORT`, `CONTRADICT`, `UNKNOWN`. `UNKNOWN` is a *result state* — "nothing relevant was found" — and must never be silently converted to `CONTRADICT`. Conflating "nobody has studied this" with "there is evidence against this" is a serious, specific error that this project is designed to avoid, because it is precisely what would cause a genuinely novel candidate to be discarded instead of flagged for further investigation.

---

## Part 3 — Data specification (fill in / verify against Week 1–2 findings)

> The following section reflects the plan as of project start. **Do not treat the numbers below as final** — Week 1–2's job is to profile the real data and confirm or correct every value here. Where you have real profiling output that disagrees with something below, the real output wins; update this section and note the change in Part 8.

### 3.1 Primary sources

- **ChEMBL** — release version: **ChEMBL 37** (prepared 2026-05-01; SQLite; SHA-256 verified 2026-09-27 — see `data/MANIFEST.md`). Primary bioactivity source.
- **BindingDB** — release **202609** (MD5 verified). Complementary binding evidence. Week 1 D3 found ChEMBL and BindingDB import from each other (see `docs/stage0_report.md` §6); recommendation pending review: ChEMBL-only for Network 1 v1.
- **UniProt** — canonical protein identifiers and sequences.
- **Open Targets / DISGENET** — curated protein–disease association (Network 2 only, Week 8).

### 3.2 Restriction criteria (apply before profiling)

- `target_type = 'SINGLE PROTEIN'`
- `organism = 'Homo sapiens'`

### 3.3 The three-state label — critical, do not simplify

Every compound–protein pair is one of exactly three states:

- **ACTIVE** — a measurement exists and indicates meaningful activity
- **INACTIVE** — a measurement exists and indicates no meaningful activity *under the stated assay conditions*
- **UNTESTED** — no measurement exists

**UNTESTED must never be converted to INACTIVE.** In a sparse network, the overwhelming majority of possible pairs are untested. Treating "never measured" as "measured and negative" would teach any downstream model that almost nothing binds, destroying precision on exactly the novel predictions this project exists to surface. This is positive-unlabelled territory, and the project states so explicitly rather than hiding it.

### 3.4 The censored-measurement trap (`standard_relation`)

ChEMBL's `activities` table includes a `standard_relation` field with values including `=`, `>`, `<`. A row with `standard_relation = '>'` and `standard_value = 10000` means the assay was stopped without finding the actual point where activity falls off — it is **not** the same as a precisely measured potency of exactly 10000. Any thresholding logic (deciding ACTIVE vs INACTIVE from a numeric cutoff) must account for this operator, not just the numeric value.

**A related trap already discovered during initial exploration:** querying ChEMBL's web client with a filter like `pchembl_value__isnull=False` can silently exclude exactly the censored (`>`, `<`) rows, because `pchembl_value` (a −log10 transform of an exact potency) is often left null precisely when the underlying measurement is inexact. If you ever filter on `pchembl_value` being non-null anywhere in the pipeline, check what you're throwing away first.

### 3.5 Activity threshold policy

No single global threshold (e.g. a flat 100 nM cutoff) should be assumed to mean the same thing across every target family — potency distributions differ meaningfully between families (kinases vs. GPCRs vs. proteases, etc.). The threshold policy should be set from the **actual observed distribution** (per-family, where the data supports it) during Week 1–2 profiling, with a documented sensitivity analysis, not chosen in advance from convention.

### 3.6 Splits — all four are required, not optional

- **Random** — can the model interpolate within known chemistry and biology?
- **Drug-cold (scaffold-disjoint)** — does it generalise to unseen chemical scaffolds? Compute the Bemis–Murcko scaffold *before* splitting, never after (computing it after splitting risks leaking structure across the split).
- **Target-cold (protein-disjoint)** — does it generalise to proteins never seen in training? This is the **primary** generalisation test, since real repurposing usually involves a protein the model has never trained on.
- **Temporal** — train on pre-cutoff measurements, test on post-cutoff. The closest available proxy for a genuinely prospective test.

The calibration set (Week 7) must be carved from **training data only**, and must be verifiably disjoint from every test split before conformal calibration is trusted. Leakage here invalidates the entire coverage guarantee downstream.

---

## Part 4 — Technology stack, and what each piece is *for*

Nothing on this list exists to look sophisticated. If you find yourself reaching for a tool not on this list, stop and ask whether the task actually needs it, or whether an existing tool already covers it.

| Layer | Tool | Role in this project |
|---|---|---|
| Data | ChEMBL, BindingDB | Bioactivity source |
| Data | UniProt | Protein identity, sequence |
| Data | RDKit | SMILES standardisation, molecular graphs, scaffolds |
| Data | pandas / Polars | Curation, profiling, EDA |
| Model | ChemBERTa | Drug representation, **frozen** |
| Model | PyTorch Geometric | Molecular graph encoder, **frozen**, optional ablation vs. ChemBERTa |
| Model | ESM-2 | Protein sequence representation, **frozen** |
| Model | PyTorch | The fusion head — the **only trained component** |
| Model | scikit-learn / XGBoost | Classical baselines the fusion head must beat |
| Calibration | MAPIE or custom | Split conformal prediction |
| Biology | Open Targets, DISGENET | Curated disease association (Network 2) |
| Evidence | PubTator | Pre-annotated biomedical literature entities |
| Evidence | NCBI E-utilities | Literature retrieval |
| Evidence | sentence-transformers, ChromaDB | Semantic search with evidence-category metadata filters |
| Agent | Pretrained instruction LLM, prompted only | Evidence interpretation and grounded synthesis — **no fine-tuning, no LoRA/QLoRA** |
| Agent | LangGraph | Orchestration, state, deterministic routing |
| Ops | MLflow | Experiment tracking — every run logged with its data version |
| Ops | Git | Version control |
| Ops | Streamlit | Final interface |
| Ops | Docker | Reproducible packaging (later) |

**Explicitly out of scope** — do not add these without an explicit flagged discussion first: a large custom knowledge graph / Neo4j, cell-imaging or transcriptomic fusion, molecular docking, LLM fine-tuning of any kind, a wet-lab experiment recommender, or chasing state-of-the-art DTI benchmark performance (the predictor only needs to be *good enough and rigorously validated* — the contribution sits downstream of it, not in beating a leaderboard).

---

## Part 5 — Week-by-week execution plan

10 build weeks, 2 buffer weeks. Each week has a **goal**, a **gate** (must pass before the next week starts), dated tasks, a named risk with its fallback, and skills it builds. **A phase's gate must be met, or explicitly and reasonably waived with a written reason in `DECISIONS.md`, before the next phase begins.**

### Phase overview

| Weeks | Phase | Passing this phase means |
|---|---|---|
| 1–2 | Data foundation | Both databases profiled; scope and label policy justified by real numbers |
| 3 | Network 1 construction | Clean, leakage-checked, versioned compound–protein network with four splits |
| 4–5 | Representation + prediction | Embeddings cached; the one trained component beats classical baselines |
| 6 | Honest evaluation | All four splits evaluated per target family; shift gap documented |
| 7 | Calibrated uncertainty | Empirical coverage matches target; uncertainty rises under harder splits |
| 8 | Network 2 + router | Disease anchor built; both query directions work; six cases sealed |
| 9 | Evidence system + the experiment | Full pipeline wired; fixed-vs-adaptive ablation run; sealed cases opened |
| 10 | Delivery | Working demo, complete write-up, rehearsed defence |
| 11–12 | Buffer (reserved) | Absorb delay first; depth second; polish last — never new scope |

### Week 1 — Data profiling I: access and first counts

**Goal:** working access to both databases, schemas understood by hand, first honest counts of what exists.

**Gate:** raw extracts on disk with dated filenames/versions recorded; a first table of protein counts by target family.

- Get ChEMBL access (SQLite bulk download preferred for full profiling; web client is an acceptable, already-verified fallback for smaller targeted queries — see Part 8 log for what's already been confirmed working). Identify and understand these tables: `activities`, `assays`, `target_dictionary`, `target_components`, `component_sequences`, `molecule_dictionary`, `compound_structures`. Verify you can see the `standard_relation` censored-measurement operator with a real example before moving on.
- Restrict to single-protein human targets; count distinct compounds, proteins, and compound–protein pairs with ≥1 activity record. Break down by target family. Plot interaction-count skew.
- Repeat on BindingDB; compute overlap with ChEMBL using InChIKey (compounds) and UniProt accession (proteins) — not raw SMILES strings, which canonicalise differently across sources.
- Tabulate assay confidence scores, `standard_type` counts, pChEMBL distribution (global and per-family), missingness.
- Consolidate into one family-level table; write the explicit open-issue list (measured-inactive count estimate; whether pChEMBL shape differs enough across families to need stratified thresholds; BindingDB integration decision; identifier mapping failures).

**Risk:** download/API access problems. **Fallback:** the ChEMBL web client (`chembl_webresource_client`) is a legitimate alternative to the bulk SQLite dump for smaller, targeted queries — already confirmed reachable during initial setup. For full-scale profiling, the bulk dump remains preferable once accessible.

### Week 2 — Data profiling II: lock the scope

**Goal:** let the real data — not convention — decide project scope, then freeze that decision in writing.

**Gate:** protein universe, drug universe, activity threshold policy, and label scheme are written into `DECISIONS.md` with the numbers that justify them. **This gate cannot be waived.**

- Count genuine measured-inactive records precisely (not estimated) — this number determines whether the negative-label strategy survives as planned.
- Decide inclusion criteria as explicit, testable rules: minimum interactions per protein, assay confidence floor, which activity endpoints are admitted (IC50-only vs. documented multi-endpoint policy).
- Apply 2–3 candidate criteria variants; measure what survives each (sensitivity analysis, not a single blind choice).
- Choose final criteria; confirm resulting density supports a meaningful target-cold split; confirm a plausible temporal cutoff leaves enough post-cutoff data.
- Write the full specification into `DECISIONS.md`.

**Risk:** too few genuine measured-inactive records survive filtering. **Fallback:** state the positive-unlabelled setting explicitly as a documented methodological constraint rather than hiding it — this is a legitimate finding, not a project-ending problem.

### Week 3 — Network 1: construction and splits

**Goal:** clean, normalised, leakage-checked compound–protein network with all four splits defined and stored.

**Gate:** versioned interaction table with canonical identifiers, three-state labels, four split assignments, passing leakage check.

- Standardise molecules with RDKit (canonical SMILES, salt stripping, duplicate resolution via InChIKey). Compute Bemis–Murcko scaffold **now**, before any splitting.
- Resolve every protein to canonical UniProt accession; map onward to gene identifier (needed by Week 8).
- Aggregate repeated measurements (median, retain spread/IQR, flag high-disagreement pairs). Apply the three-state label.
- Build all four splits; store assignment per row. Carve the calibration set from training only.
- Run and pass an explicit leakage check across all four splits. EDA on the final network.

**Risk:** identifier mismatches between/within sources. **Fallback:** restrict to cleanly-mapping records; report the coverage loss honestly rather than forcing an uncertain match.

### Week 4 — Representation: frozen embeddings and baselines

**Goal:** cache every embedding once; establish a classical-model comparison floor.

**Gate:** embeddings cached for every compound and qualifying protein; classical baseline scores recorded on the random split.

- Set up embedding pipeline; confirm ChemBERTa/GNN and ESM-2 load and run on one worked example.
- Build classical baselines (logistic regression, XGBoost on fingerprints); score on random split.
- Batch-embed every compound (log and handle failures, don't silently drop them).
- Batch-embed every qualifying protein sequence — the longest compute job so far; start early. If no GPU is available locally, move this job to available academic/cloud compute rather than forcing it through CPU.
- Sanity-check embeddings (do similar compounds/proteins cluster sensibly?); finalise baseline logging.

**Risk:** protein embedding impractically slow without GPU. **Fallback:** smaller ESM-2 checkpoint, or move the batch job to available HPC/cloud compute.

### Week 5 — The one trained component: the fusion head

**Goal:** train the single genuinely-ours component; working end to end on the random split.

**Gate:** fusion model trains reliably, beats classical baselines on random split, every run logged in MLflow with data version.

- Dataloader over cached embeddings, wired to Week 3's split assignments.
- Implement fusion head (concatenate embeddings → small MLP → sigmoid). Deliberately overfit a tiny subset first to prove the plumbing works.
- Wire MLflow logging thoroughly (hyperparameters, curves, metrics, artefacts, exact data version).
- Full training on random split; tune only the minimum necessary (learning rate, hidden size, dropout, class weighting).
- Compare against Week 4 baselines. If the fusion head doesn't beat them, diagnose (check leakage/label noise first) before proceeding — do not paper over a genuine gap.

**Risk:** trained model doesn't beat classical baselines. **Fallback:** this is a legitimate result, not a failure — check for leakage/noise first; if the gap is real, report it honestly and continue, since the contribution sits downstream of this predictor.

### Week 6 — Honest evaluation under distribution shift

**Goal:** rigorously characterise how the predictor behaves as the task gets realistically harder.

**Gate:** all four splits evaluated and reported per target family; the shift-induced performance gap documented plainly.

- Evaluate drug-cold, target-cold, temporal splits (AUROC/AUPRC/precision/recall).
- Stratify every result by target family, not just pooled. Error analysis on the worst-performing family.
- Write the evaluation section of the eventual report now, while findings are fresh. State the shift gap plainly — it's what justifies Week 7's uncertainty quantification.

**Risk:** performance collapses badly on target-cold. **Fallback:** expected to some degree, and scientifically useful — it's exactly the condition that should make Week 7's conformal predictor honestly uncertain. Report it plainly; a large gap here is evidence the project's central mechanism is needed, not that the project failed.

### Week 7 — Calibrated uncertainty: conformal prediction

**Goal:** wrap the predictor in split conformal prediction; confirm uncertainty rises specifically where Week 6 showed the task getting harder.

**Gate:** empirical coverage matches nominal target on held-out data; singleton-vs-uncertain rate reported across all four splits, showing the expected rise under shift.

- Confirm the calibration set (from Week 3) is genuinely disjoint from every training and test split — airtight before anything else this week.
- Implement split conformal prediction: nonconformity scores, q̂ quantile at target coverage (e.g. 90%), resulting sets `{1}`, `{0,1}`, `{0}`.
- Verify empirical coverage matches nominal target within tolerance. If not, check the exchangeability assumption before adjusting anything else.
- Produce prediction sets across all four splits; count singleton/uncertain/confident-negative rates per split — **this table is the single most important artefact of the week**.
- Implement family-conditioned calibration as a second variant; compare against global calibration.

**Risk:** coverage off-target, or nearly everything uncertain. **Fallback:** check calibration-set exchangeability with the relevant test set first (most common real cause); consider adjusting target coverage and explicitly report the resulting coverage/set-size trade-off rather than silently tuning until numbers look better.

### Week 8 — Network 2: disease anchor, router, and sealing the stress test

**Goal:** extend Network 1 into the full compound–protein–disease network via curated (never predicted) disease association; implement the deterministic router; both query directions working; seal the six retrospective test cases.

**Gate:** forward and reverse queries both run end to end and return ranked, anchored candidates; six cases sealed in `cases/sealed.json`, not reopened until Week 9.

- Pull protein–disease association data (Open Targets / DISGENET) for every qualifying protein, using Week 3's gene mapping. Check coverage.
- Define anchor-strength thresholds (strong/moderate/weak) justified from the actual association-score distribution, not arbitrary. Confirm the disease-anchor table stores only the numeric score/metadata, never the underlying literature text — this keeps the Week 9 evidence agent independent of it.
- Implement forward query path (drug → predicted targets → linked diseases).
- Implement reverse query path (disease → associated proteins → drugs scored on demand). Implement the dual-signal router as plain, independently unit-tested code.
- Select six retrospective stress-test cases: three well-supported (expect CONFIRM), three with documented contradictory/safety evidence (expect CHALLENGE), at least one genuinely borderline. Score candidates against pre-agreed criteria (literature richness × relevance × clear outcome × independence from training data), not by picking famous examples by feel. **Write to `cases/sealed.json` and do not open again until Week 9.**

**Risk:** many qualifying proteins have no disease association in curated resources. **Fallback:** this is itself a reportable coverage finding, and it's exactly what the weak-anchor routing path (INVESTIGATE / LOW_PRIORITY) exists to handle gracefully — absence of a database entry is not evidence of biological irrelevance.

### Week 9 — Evidence system and the central experiment

**Goal:** build policy-conditioned retrieval and grounded synthesis; wire the full pipeline; run the fixed-vs-adaptive ablation the whole thesis rests on; open the sealed cases as the final blind test.

**Gate:** full pipeline runs end to end from query to cited report; fixed-vs-adaptive comparison complete on the same candidates, whichever way the result goes; six sealed cases run and scored.

- Set up literature retrieval (PubTator, NCBI E-utilities). Define the four evidence categories as concrete query templates, not vague labels.
- Build the vector index (ChromaDB) with evidence-category metadata. Build structured evidence extraction (passage → typed record). Confirm UNKNOWN is returned honestly when nothing relevant exists.
- Wire the LangGraph orchestration: router → policy-specific retrieval → extraction → grounded synthesis. Constrain the synthesiser to quote-and-cite only — reject any claim with no matching record.
- Implement the fixed-retrieval control (identical generic query for every candidate). **Open the sealed case file for the first time.** Build hand-curated gold evidence sets for each of the six cases.
- Run both fixed and adaptive retrieval across the same candidate set (documents retrieved, model calls, time per candidate). Score on evidence precision, counter-evidence recall (vs. gold sets), direction-classification accuracy, citation correctness. Run the six sealed cases through the full pipeline: does CONFIRM fire on the three positive cases? Does CHALLENGE fire and surface known counter-evidence on the three negative cases? **Write up the result — whichever way it goes — without adjusting the experiment after seeing the outcome.**

**Risk:** adaptive retrieval doesn't clearly beat fixed retrieval, or a sealed case doesn't behave as expected. **Fallback:** both are legitimate, reportable results. Analyse where and why the policy did or didn't help — do not re-run with different cases or adjusted thresholds after seeing the outcome. A carefully analysed null/mixed result is stronger, more honest science than a suspiciously clean positive one.

### Week 10 — Delivery: interface, write-up, defence

**Goal:** make the system usable, findings readable, defence rehearsed.

**Gate:** working demonstration, complete written report (methods/results/limitations), rehearsed presentation that survives hard questions.

- Build the Streamlit query interface and the evidence/report view.
- Write results and discussion sections from accumulated weekly notes. State limitations plainly, including anything from Week 9 that didn't go as hoped.
- Final figures (family-stratified evaluation, uncertainty-under-shift, fixed-vs-adaptive comparison, sealed-case results). Rehearse the demo script. Prepare answers to hard questions (see Part 6).
- Repository clean-up; confirm `DECISIONS.md` is complete and dated throughout; reproducibility check on a clean environment; final submission assembled.

**Risk:** time runs short. **Fallback priority:** finish the written report first, then the live demonstration, then interface polish last — a well-documented, honestly analysed result outperforms a polished interface with no analysis behind it.

### Weeks 11–12 — Reserved buffer

Not a soft extension of Week 10. Priority order: **(1)** absorb any delay from weeks above — complete any unfinished gate before anything new; **(2)**, only if nothing above is owed, depth (a second independent ablation candidate set; further exploration of family-conditioned calibration; a second literature novelty audit); **(3)** polish, last. **Do not spend buffer time on new scope** — if a new idea surfaces here, record it as future work in the final report rather than building it.

### The one rule that protects the whole project

> The contribution is not the prediction model — it is what happens after the prediction. If a week runs over, protect Week 7 (calibration), Week 8 (router + sealed cases), and Week 9 (the central experiment) before anything else. A modest predictor with rigorous calibration and a clean central experiment is a far stronger submission than an excellent predictor with the evidence layer left half-built.

---

## Part 6 — Questions to be ready to answer

Prepare short, honest answers to these. Every one has already been reasoned through somewhere above — this section collects the sharpest version of each in one place, and you should be able to answer them the same way a human on this project would.

| Question | Short answer |
|---|---|
| Isn't conformal prediction for DTI already published? | Yes — not our novelty claim. Ours is narrower: using the calibrated state to control what an evidence-retrieval agent searches for next, not the calibration method itself. |
| Isn't uncertainty-guided RAG already a known technique? | Yes, as a general pattern (Adaptive-RAG, SUGAR, ConfRAG). Those reason about self-referential uncertainty. Ours is a downstream agent reacting to an *external*, independently calibrated signal about a biological claim — that specific cross-paradigm coupling is the test. |
| How do you know "untested" isn't secretly "inactive"? | We never allow that conflation — enforced at the labelling step (Part 3.3), one of the project's stated methodological pillars. |
| Why should uncertainty estimates be trusted on a protein the model has never seen? | We don't assume they should be — that's exactly what Weeks 6–7 test directly, reporting coverage and set-size honestly, including where they degrade under target-cold shift. |
| What if fixed and adaptive retrieval perform about the same? | Then that's the finding, reported as such, with analysis of why — a null result was planned for, not just tolerated. |
| Isn't this just TxGNN / similar repurposing pipelines? | The novelty isn't the drug–protein–disease network itself (well-established) — it's the uncertainty-to-evidence-policy coupling built on top. |
| Why is the disease anchor not itself a trained model? | Deliberately: predicting protein–disease links would make the system opaque end to end and would be a second full research project. A curated, auditable resource keeps that link checkable and keeps the AI novelty confined to where it belongs. |

---

## Part 7 — Quick reference: what each component IS and IS NOT

| Component | IS | IS NOT |
|---|---|---|
| Fusion head | The one trained neural component; predicts interaction probability from frozen embeddings | A state-of-the-art DTI architecture — it only needs to be good enough and rigorously validated |
| Conformal wrapper | A statistical calibration layer with a coverage guarantee under exchangeability | A claim that any single prediction is correct with that probability |
| Disease anchor | A curated, looked-up biological fact from Open Targets/DISGENET | Predicted, a second model, or derived from the same literature the evidence agent searches |
| Router | Deterministic, unit-tested code combining two signals into one policy | An LLM decision — this is intentional, so the most consequential step is reproducible |
| Evidence agent | A retrieval-and-synthesis system constrained to cite structured records | Free to assert anything without a matching retrieved record |
| UNKNOWN label | An honest statement that nothing relevant was found | The same as CONTRADICT — never silently converted to it |

---

## Part 8 — Running Log

> **Moved (2026-10-03):** new session entries now go in `docs/PROJECT_LOG.md` (newest first), and the current state lives in `docs/STATUS.md`. The entries below are kept unchanged as history.

*(Claude Code: append a dated entry here at the end of every work session. Keep entries short and factual — what was done, what was found, what changed vs. the plan above, what's still open. Do not delete or rewrite earlier entries; this log is itself part of the project's provenance.)*

### [Date to be filled by whoever starts the session]

- Status before this session: Week 1, Day 1 in progress.
- ChEMBL web client (`chembl_webresource_client`) confirmed reachable and working — used to query imatinib (CHEMBL941) activities and ABL1 (CHEMBL1862) target lookup successfully.
- Bulk ChEMBL SQLite download attempted via direct FTP/HTTPS link — failed repeatedly (`ConnectionRefusedError`, network-level block, likely local network/firewall issue, not an EBI outage). Attempted via `chembl_downloader` package on a different network — was progressing successfully as of last check (~1% complete, ETA ~2.5 hours) before this session's context ended. **Status of that download at the start of the next session is unknown — check `data/raw/` for `chembl_37_sqlite.tar.gz` or the `chembl_downloader` cache location, and verify integrity with `tar -tzf` before trusting it.**
- Discovered and noted: filtering ChEMBL activity queries on `pchembl_value__isnull=False` silently excludes many censored (`>`, `<` relation) measurements, since pChEMBL is often left null for inexact potency values. This is now documented in Part 3.4 above — apply this awareness to any future filtering logic in the ingestion pipeline.
- Still open from Day 1: full schema note (`docs/chembl_schema_notes.md`) not yet written up as a standalone file; BindingDB not yet touched (Day 3 task); the censored-relation example from the *raw, unfiltered* activity query for imatinib had not yet been directly inspected by row at the point this session ended — confirm this explicitly before marking Day 1 complete.

### 2026-09-27 — Week 1 completed to gate (Claude Code session 1)

- **Status before:** W1 D1 partial. The ChEMBL tarball on disk was truncated (265 MB of 5.76 GB). The repo lived in OneDrive, and the local and remote histories had diverged.
- **Decisions confirmed by the owner:** universal scope (all human single-protein targets, *not* kinome-only; supersedes the Project Bible), Briefing/Master Plan schedule is authoritative, Week 1 started 2026-09-21, heavy compute on Colab/Kaggle/HPC, free open-weight LLM for W9, push directly to `main`. Recorded as `DECISIONS.md` D-001–D-005.
- **Done:**
  - Moved the working repo to `C:\Users\91701\code\Trust_DTI`; the OneDrive copy is kept untouched as backup.
  - Built a curated env (`requirements.in` + pinned `requirements.txt`).
  - Resumed the ChEMBL 37 download, verified by SHA-256, and extracted it (activities 24,527,044 = release notes). Downloaded BindingDB 202609, MD5 verified.
  - Wrote `data/MANIFEST.md` and `docs/chembl_schema_notes.md`.
  - Closed D1: the imatinib censored row is shown in both the web client and SQLite, and a `!= '='` bug in the notebook was fixed.
  - D2–D5 scripts are in `src/ingest/` with outputs in `reports/stage0/`, and the report is in `docs/stage0_report.md`. Tests: 9 fast plus 1 slow, all passing.
  - A from-scratch re-run reproduced all 16 CSV/JSON outputs byte-for-byte.
- **Found:**
  - 5,738 proteins, 1.56M compounds, 5.06M pairs. Extreme skew: the top 10% of proteins hold 88% of pairs.
  - ChEMBL ↔ BindingDB are mutually imported; the naive overlap is inflated about 13×.
  - PubChem qHTS drives a pChEMBL spike at about 4.5 and **confounds per-family potency distributions** (oxidoreductase median 4.82 overall vs 6.36 without PubChem). This bears directly on §3.5.
  - "Potency" is the largest endpoint. `>>` and `<<` operators exist. 1.73M "inconclusive" rows must not become INACTIVE.
  - About 1.04M pairs look measured-inactive, so the PU fallback may not be needed.
  - 40% of rows lack doc_year, which matters for the temporal split.
- **Changed vs plan:**
  - EBI publishes SHA-256, not MD5, so the checksum type was adjusted.
  - Kinetic endpoints and %-inhibition surfaced as needing an explicit endpoint policy.
  - `DECISIONS.md` D-006–D-010 added.
- **Open for Week 2:** see `docs/stage0_report.md` §7 (nine issues). Owner review of the W1 gate is needed, and in particular the BindingDB recommendation (D-008). The Master Plan also wants the teammate to run the pipeline on their own machine.

---

*(New entries go above this line, most recent last.)*
