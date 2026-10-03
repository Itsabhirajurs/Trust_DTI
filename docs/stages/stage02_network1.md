# Stage 2: Network 1 (status: explained, **not coded yet**; planned for project Weeks 2–3)

## Why this stage exists
Stage 1 produced 8.3M measurement records. A model cannot learn from those directly: the same pair appears many times (28.0% of pairs have more than one record, one pair has 1,934), the same molecule is written in several forms, no record yet says ACTIVE/INACTIVE/UNTESTED, and nothing says which records are for training and which are held back. Stage 2 turns records into **one clean row per drug–protein pair**, with one label and a split assignment. A leak between train and test here (near-identical molecules on both sides) would inflate every later accuracy figure and nothing downstream would reveal it.

## What "network" means here
A graph stored as tables. Nodes: compounds and proteins. Edge: a measured pair. Edge attributes: aggregated potency, spread of repeats, label, split, and a `provenance` column. Disease links are **not** here; they come in Network 2 (Stage 7) and live in a separate table.

## Why these tools
| Tool | Job | Why |
|---|---|---|
| RDKit | Canonical SMILES, salt stripping, InChIKey, Murcko scaffolds | Standard open-source cheminformatics; ChEMBL uses it too, so our standardisation matches the source. Installed (2026.03.6) |
| pandas + Parquet | Aggregate, label, store | Same stack as Stage 1; keeps pinned column types |
| UniProt accession (already in ChEMBL) | Protein key | No new download; same key BindingDB uses |
| Plain Python for splits | Four splits + leakage check | A leakage check is only trustworthy if every line can be read; a library would hide the grouping |

## Tasks (briefing Week 3), with what the real data says
Probe: `src/ingest/probe_stage2_issues.py` → `reports/stage0/stage2_probe_output.txt`. Salt and scaffold figures come from a **fixed 40,000-compound sample** (seed 0), not the full universe.

1. **Standardise molecules.** Canonical SMILES, strip salts, resolve duplicates by InChIKey.
   - 3.2% of sampled SMILES are multi-component (salt or mixture). No sampled structure failed to parse.
   - All 1,557,251 InChIKeys are unique, but only 1,487,133 distinct skeleton blocks (first 14 characters) exist: **53,559 skeletons are shared by more than one ChEMBL compound ID**. Example: imatinib (CHEMBL941) and a deuterated imatinib (CHEMBL2386595). *Expected a salt; it was an isotope variant.* If such variants fall on opposite sides of a split, that is leakage. **Decision pending: merge into parent compounds?**
2. **Compute scaffolds before any split.** A scaffold is the core ring system. The drug-cold split holds out whole scaffolds. Computing it after splitting could place relatives on both sides unnoticed. Sample: 31,147 scaffolds in 40,000 compounds; the largest holds 1.4% (the next are 191, 68, 62 compounds). Do **not** quote "87% of scaffolds appear once": that is inflated by sampling.
3. **Resolve proteins** to a canonical UniProt accession and onward to a gene ID (needed for Week 8). All 5,869 targets have exactly one component, so mapping is clean here. Open: isoforms and the gene mapping itself.
4. **Aggregate repeated measurements** (median, keep the spread, flag disagreement). Of 1,347,583 pairs with an exact potency, 22.9% have repeats; typical spread is small (median 0.20 log units), but **23.1% of those pairs differ by at least 1 log unit and 8.2% by at least 2** (100-fold). Keep the spread; do not hide it in an average.
5. **Apply the three-state label** using the Week 2 decisions and the protected censored rows. UNTESTED is never INACTIVE.
6. **Build four splits.**

| Split | Held out | Question |
|---|---|---|
| Random | random pairs | can it interpolate? |
| Drug-cold | whole scaffolds | works on unseen chemistry? |
| Target-cold | whole proteins | works on an unseen protein? (primary test) |
| Temporal | everything after a cutoff | works on future data? (limited by the 40% of rows with no year) |

7. **Carve the calibration set from training data only.** Stage 6 uses it to learn how far to trust the model; overlap with any test split voids the coverage guarantee. Disjointness must be proved.
8. **Leakage check** across all four splits, as a test that fails the build.
9. **Save a versioned, named table** and run EDA. Dataset versions are never overwritten.

## Decisions Week 2 must settle first
Thresholds (controlling for data source); which endpoints count; the measured-inactive rule; minimum data per protein (2,883 of 5,738 proteins have fewer than 10 partners); temporal cutoff; whether to merge isotope/stereo variants. (`docs/STATUS.md`)

## Risk and fallback
Identifier mismatches within or between sources. Fallback: keep only cleanly-mapping records and report the loss; never force an uncertain match.

**Gate:** versioned interaction table with canonical identifiers, three-state labels, four split assignments, and a passing leakage check.

## Not measured
Runtime of standardising all 1.56M molecules; full-universe salt and scaffold counts.

## Be able to explain
- Why the scaffold must be computed before splitting.
- Why two compound IDs for "the same molecule" can leak across a split.
- Why repeated measurements need their spread kept.
- Why the calibration set must be disjoint from every test set.
