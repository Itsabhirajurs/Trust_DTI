# Week 11 retrieval diagnostics — 22 November 2026

## Purpose

This note records why the first live Europe PMC run is being treated as an interim baseline rather than a completed evidence-retrieval experiment. It uses the local command outputs supplied from the Windows workstation.

## 1. Initial four-policy run

| Strategy | Allocated slots | Returned candidate–strategy–publication records | Candidate coverage |
|---|---:|---:|---:|
| fixed | 45 | 3 | 3 |
| uncertainty_only | 30 | 0 | 0 |
| disease_only | 45 | 8 | 3 |
| combined | 30 | 4 | 2 |
| **Total** | **150** | **15** | — |

The raw maximum from 9 candidates × 4 strategies × 5 documents is 180. The router allocated 150 because INACTIVE_ONLY candidates receive zero slots under uncertainty_only and combined. This is intended STOP behaviour; it must not be counted as an API failure.

All 15 returned records carried DISEASE_CONTEXT as their returned intent. None were returned for MECHANISTIC, COUNTER or GENERAL. There were eight distinct candidate–publication pairs across the four policy arms; the 15 records are policy exposures and can include the same candidate/publication in multiple strategies.

## 2. Publication metadata and annotation status

- Missing titles: 0
- Missing abstracts: 0
- Missing publication IDs: 0
- Records not marked UNANNOTATED: 0
- Human direction labels: none

The retrieval pipeline correctly kept the records unannotated. Query intent is not an evidence-direction label.

## 3. API failures

Two requests failed with ReadTimeout after the 45-second read timeout:

1. PTH1R candidate `f894b1679dbcb915`, combined policy, DISEASE_CONTEXT:
   `TITLE_ABS:("PTH1R" AND "metaphyseal chondrodysplasia, Jansen type")`
2. IRAK4 candidate `0830087a069c8cad`, uncertainty_only policy, COUNTER:
   `TITLE_ABS:("compound KZQFVVXWGJWYKK-JOCQHMNTSA-N" AND "IRAK4" AND (resistan* OR ineffective OR "no effect" OR "failed to inhibit" OR "does not bind" OR "lack of activity"))`

These are technical network failures. They are not biological evidence and must not be recoded as inactive, CONTRADICT or UNKNOWN annotations.

## 4. Compound identity follow-up

The candidate builder resolved 8 PubChem compound titles and left one candidate on a key-based fallback. A PubChem synonym lookup returned eight HTTP 200 responses and one HTTP 404. The corrected ChEMBL lookup then queried the nine ChEMBL molecule IDs and compared each returned standard InChIKey to the candidate InChIKey.

All 9/9 comparisons were exact matches. ChEMBL's returned preferred-name field was empty for all nine; the inspected molecule-synonym lists were also empty. The exact ChEMBL identifiers are preserved in the progress report. This verifies compound identity, not a drug's clinical status or interaction with the selected protein.

## 5. Europe PMC synonym probe

Three representatives were selected: DRD2, PTH1R and IRAK4. For each, the probe queried:
- chemical name + target gene, synonym=false
- chemical name + target gene, synonym=true
- ChEMBL molecule ID + target gene, synonym=false
- ChEMBL molecule ID + target gene, synonym=true

All 12 hit counts were zero.

### Interpretation

This result is specific to the tested TITLE_ABS query formulations. It does not prove that no publications exist. The current query terms may be too restrictive, particularly where long systematic chemical names are quoted exactly or the ChEMBL ID is not written in article titles/abstracts.

## 6. Next controlled experiment

1. Keep the nine-candidate table and initial JSONL/failure/metadata files frozen.
2. Test a small number of clearly documented query forms for the same representative candidates: validated alternate compound terms if found, target gene/protein names and carefully controlled broader combinations.
3. Record the exact query string, search parameters, hit count, returned identifiers and timestamps for every test.
4. Screen for false-positive disease-only articles; more hits are not automatically better.
5. Once query forms are defensible, rerun all four strategies on the same nine candidates with the same cap, writing to new versioned outputs.
6. Only then prepare the blind worksheet and perform human evidence review.

Do not silently increase the document budget, alter the candidate set or change the policy weights to make a strategy look stronger. A query improvement should be applied consistently and documented as a protocol revision.
