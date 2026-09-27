# Stage 0 report — Week 1 (data profiling I)

*2026-09-27 · ChEMBL 37 + BindingDB 202609 · all numbers regenerate from `src/ingest/*` (see `data/MANIFEST.md`).
Detail tables and plots: `reports/stage0/`.*

This report describes what exists. **It makes no Week 2 decisions** (thresholds, labels, inclusion rules);
it gives Week 2 the numbers to make them.

## 1. Universe after the Briefing §3.2 restriction (human, SINGLE PROTEIN)

| | Count |
|---|---|
| Activity rows | **8,299,186** (of 24,527,044 in ChEMBL 37) |
| Proteins (UniProt accessions) with ≥1 activity | **5,738** (targets defined: 5,869; 0 with >1 component) |
| Compounds (molregno) | **1,559,417**; InChIKey missing for 2,166 |
| Compound–protein pairs with ≥1 activity record | **5,064,882** |
| … with a pChEMBL value | 1,943,313 (38%) |
| … with an exact (`=`) numeric value | 2,502,902 |
| Approved drugs (max_phase = 4) in the universe | 2,685 |
| Censored rows (`>`, `<`, `>=`, `<=`, `>>`, `<<`) | 810,994, **every one with null pChEMBL** |

**Skew is extreme** (`skew_interactions.png`). Median partners per protein = 9. 2,883 proteins have <10 partners,
while 1,761 have ≥100. The top 10% of proteins hold **88%** of all pairs. Median partners per compound = 1
(805k compounds are seen against only one protein).

## 2. Target families (`family_table.csv`, `family_l1_counts.csv`)

| Level 1 | Proteins | Pairs |
|---|---|---|
| Enzyme | 2,396 | 2,546,363 |
| Membrane receptor | 455 | 718,858 |
| Epigenetic regulator | 171 | 526,599 |
| **Unclassified protein** | **1,658** | 441,257 |
| Transcription factor | 184 | 328,642 |
| Ion channel / Transporter | 185 / 168 | 105,561 / 100,492 |
| Other (8 classes + 39 "Multiple") | — | ~298k |

The two densest level-2 families are **Kinase** (443 proteins, 914k pairs, median 1,165 pairs/protein) and
**Family A GPCR** (277 proteins, 507k pairs). **29% of proteins are unclassified**, but they are sparse
(median 2 pairs/protein).

## 3. Assay quality and endpoints (D4 tables)

- **confidence_score is only ever 8 or 9** in this universe: 9 = 5.40M rows, 8 = 2.90M. The single-protein filter
  already implies ≥8, so a "confidence floor" in Week 2 is really a choice between 8 and 9.
- assay_type: Binding 4.94M, Functional 3.22M, ADMET 135k.
- The top endpoint is **"Potency" (2.69M rows, mostly PubChem qHTS)**, ahead of IC50 1.74M, then k_off/k_on
  (~686k each; kinetics, not affinity), Ki 634k, Inhibition 619k, EC50 214k, AC50 211k, Kd 182k.
- Missingness: pChEMBL 69%, standard_relation 30%, standard_value 22%, **doc_year 40%**.
- 313k rows are flagged `potential_duplicate`; 74k carry a data-validity warning (mostly "Outside typical range").

## 4. Where the data comes from (`d4_sources.csv`)

| Source (src_id) | Rows | Pairs | doc_year missing |
|---|---|---|---|
| PubChem BioAssay (7) | 2.96M | 2.58M | **100%** |
| Scientific literature (1) | 2.32M | 1.53M | ~0% |
| BindingDB patents (37) | 2.24M | 0.57M | 0% |
| GSK PKIS (16), DrugMatrix (15), others | ~0.8M | — | mixed |

## 5. Measured-inactive estimate (not the Week 2 count)

- Comment says inactive / not active: 798k rows. "Inhibition <50% @ 10 µM, no curve": 149k rows.
  Censored ≥10 µM (IC50/Ki/Kd/EC50, `>`/`>=`/`>>`): 344k rows.
- Union: **1.19M rows → ~1.04M pairs**, of which 559k are at confidence 9.
- **Not counted as inactive: "inconclusive" (1.73M rows)**, "not determined", "nd". These are closer to UNTESTED.

The positive-unlabelled fallback in Briefing Week 2 may not be needed: there appear to be enough measured negatives.
But see issue 2 before trusting that.

## 6. ChEMBL ↔ BindingDB overlap (D3; `d3_*`)

The two databases **import from each other**: 52% of BindingDB's human single-chain rows are curated from ChEMBL,
and 2.23M ChEMBL rows are "BindingDB patent" data.

| Comparison (pairs keyed on InChIKey × UniProt) | Both | ChEMBL-only | BDB-only |
|---|---|---|---|
| Naive, all vs all | 872,761 | 4,181,809 | 754,419 |
| Independent vs independent | **66,145** | 4,453,291 | 705,983 |

The naive overlap is inflated about 13× by construction. Against all of ChEMBL, independent BindingDB adds about
**426k pairs (≈8%)**: US patents 353k, PubChem 36k, BindingDB literature curation 26k, PDSP 5k.
Potency agreement on 40,988 exact overlapping pairs: median |Δp| = 0.00, 88.5% within 0.5 log, 95.6% within 1 log.
The 20-pair spot-check is in `d3_potency_spotcheck_20.csv`. A median of exactly 0 suggests many "independent"
overlaps are really the same underlying measurement reached by different routes.

**Recommendation (for review, not locked):** build Network 1 v1 from **ChEMBL only**. Revisit BindingDB in Week 2
for one specific reason: its extra patent pairs are probably *recent* (BindingDB 202609 postdates ChEMBL 37),
which could strengthen the temporal test set.

## 7. Open-issue list for Week 2

1. **Family-vs-source confounding of potency.** 80% of pChEMBL values in the 4.25–5.0 spike are PubChem qHTS.
   Oxidoreductase median pChEMBL is 4.82 overall but 6.36 without PubChem (Kinase 7.09 → 7.25; GPCR-A 6.86 → 7.12).
   Per-family thresholds (Briefing §3.5) must control for source/endpoint, or they will encode HTS artifacts as biology.
   Full per-family table: `reports/stage0/pchembl_source_confounding.csv` (7 families shift by more than 1 log unit).
2. **Which endpoints count?** "Potency" (qHTS) is the largest endpoint but is single-series HTS data.
   Decide IC50/Ki/Kd/EC50-only versus including Potency/AC50, and exclude kinetics (k_on/k_off) and %-inhibition from thresholding.
3. **Measured-inactive rules.** Settle which comment and censored patterns count as INACTIVE, at what concentration,
   and confirm "inconclusive" maps to UNTESTED.
4. **Temporal split.** 40% of rows have no doc_year (all PubChem, PKIS, DrugMatrix). Options: exclude them from temporal
   evaluation, or date them by PubChem AID deposition. Candidate cutoffs must be checked against post-2020 volume (1.77M rows in 2020–24).
5. **Sparse and unclassified proteins.** 2,883 proteins have <10 partners and 1,658 are unclassified.
   A minimum-pairs rule is needed for a meaningful target-cold split, and the report should say how much of the universe it removes.
6. **Confidence floor** is effectively 8 vs 9 (35% of rows are conf 8).
7. **Duplicates and validity.** Decide how to treat 313k `potential_duplicate` rows and 74k validity-flagged rows before aggregation (W3).
8. **BindingDB integration.** ChEMBL-only is recommended for v1; see §6.
9. **Identifier mapping.** 2,166 compounds lack an InChIKey (likely biologics or polymers); 42 proteins have
   conflicting family links (labelled "Multiple"). BindingDB: 210 rows without InChIKey, 0 without UniProt.

## 8. Week 1 gate checklist

- [x] Raw extracts on disk with versions, sizes and publisher checksums recorded (`data/MANIFEST.md`); both verified.
- [x] Table of protein counts by target family (`family_table.csv`, `family_l1_counts.csv`).
- [x] Profiling runs end to end and reproduces: a from-scratch re-extract plus re-profile gave **byte-identical** outputs (16 CSV/JSON files, SHA-256).
- [x] Open-issue list written (§7).
- [x] D1 censored-measurement check done on real rows (`docs/chembl_schema_notes.md`, notebook 01).
- [ ] Teammate runs the pipeline on their own machine (the Master Plan asks that *both* members can run it). Pending, on the human side.
