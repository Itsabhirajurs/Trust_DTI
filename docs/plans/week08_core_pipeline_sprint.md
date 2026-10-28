# Week 8 Core-Pipeline Sprint — Working Plan

**Started:** 28 October 2026  
**Aim:** maximize implementation progress in one focused week, while preserving the distinction between code completion and scientific validation.

## Definition of “90%”

For this sprint, 90% means a demonstrable, documented prototype through the main architectural path—not that every experiment is scientifically conclusive. A system is marked complete only when relevant code runs, tests pass, outputs are saved, and limitations are recorded.

## Ordered work packages

| Order | Work package | Acceptance gate | State at sprint kickoff |
|---:|---|---|---|
| 0 | Reconcile Week 7 output artifacts | Seven locally verified pilot files committed; clean local tree | Documentation committed remotely; output arrays/CSV still need the separate local push |
| 1 | Classical DTI baseline | Reproducible Morgan + protein-family baseline using existing split columns, saved metrics/predictions, integrity checks, tests | Implementation planned; first local data-backed run pending |
| 2 | Evaluate split behavior | Run random, drug-cold, target-cold and temporal splits; compare ROC-AUC, PR-AUC, balanced accuracy, Brier/ECE, and empirical set coverage | Pending data-backed runs |
| 3 | Calibration | Fit calibration only on calibration partition; report coverage and set sizes; don't claim guarantees where exchangeability is unverified | Pending |
| 4 | Curated protein–disease network | Resolve stable target IDs, retrieve a cited source, preserve score/evidence/source/version, verify duplicates and missing mappings | Not started |
| 5 | Deterministic router | Unit-tested mapping from conformal set × anchor strength to policy; UNKNOWN remains UNKNOWN; curated and predicted edges stay separate | Not started |
| 6 | Literature retrieval prototype | Cited records with source URL, retrieval date, query/policy, evidence type and direction; robust empty/error handling | Not started |
| 7 | Matched-budget comparison | Fixed vs uncertainty-only vs disease-anchor-only vs combined routing at identical retrieval budgets; counter-evidence recall and efficiency measured | Not started |
| 8 | Integrated demo and write-up | Repeatable CLI or lightweight UI, clear setup, tested path, report and limitations | Not started |

## Resource strategy

- Keep the first model run bounded by deterministic row caps; expand after runtime and memory are measured.
- Use local data files (never commit raw/interim/processed datasets) and cloud GPU for expensive encoder workloads.
- The Week 7 encoder sample proves inference works on small inputs only. It does not supply the one-million-compound embedding cache.
- Evidence records must keep retrievable citations; a model-generated answer alone is not evidence.
- Do not open sealed evaluation cases early; the blinding rule in `AGENTS.md` remains in force.

## Sprint success criteria

Minimum success:
1. Baseline training and metrics reproducibly run against Network 1.
2. All tests pass and split checks block unsafe training.
3. Calibration and router contracts have unit tests and explicit assumptions.
4. Protein–disease and evidence interfaces retain provenance.
5. At least one end-to-end demo is runnable with a small, clearly labelled sample.
6. The matched-budget experiment produces measured results or is explicitly marked pending because inputs/runtime are missing.

Stretch goal:
- Batch embeddings at full Network 1 scale, with resumable checkpoints and measured throughput. Do not call this done until all intended keys have a verified embedding and coverage report.
