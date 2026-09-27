# ChEMBL 37 schema notes (Week 1 D1)

Verified against the local `chembl_37.db` (SQLite, 30.5 GB, release dated 2026-05-01;
`activities` row count 24,527,044 = release notes). Only the tables this project touches.

## Join path used by `src/ingest/chembl_extract.py`

```
activities ──assay_id──► assays ──tid──► target_dictionary ──tid──► target_components ──component_id──► component_sequences (accession)
    │                                                                               └──component_id──► component_class ──► protein_classification (family tree)
    ├──molregno──► molecule_dictionary (chembl_id, max_phase)
    ├──molregno──► compound_structures (standard_inchi_key, canonical_smiles)
    ├──doc_id────► docs (year)
    └──src_id────► source (who deposited the record)
```

## Tables

| Table | Grain | Columns we use | Notes |
|---|---|---|---|
| `activities` | one measurement | `activity_id, assay_id, doc_id, molregno, src_id, standard_type, standard_relation, standard_value, standard_units, standard_flag, pchembl_value, activity_comment, data_validity_comment, potential_duplicate` | `standard_*` are ChEMBL-normalised (nM etc.). `standard_relation` carries the censoring operator (`=`, `>`, `<`, `>=`, `<=`, `~`) — **see trap below**. `activity_comment` holds free-text outcomes such as "Not Active" — the main place measured-inactives live besides censored values. `data_validity_comment` flags suspect values (e.g. outside typical range, potential transcription error). |
| `assays` | one assay | `assay_id, tid, assay_type, confidence_score, src_id` | `assay_type`: B binding, F functional, A ADMET, T toxicity, P physicochemical, U unassigned. `confidence_score` 0–9: 9 = single protein target directly assigned; 8 = homologous single protein; lower = complexes, cells, organisms. |
| `target_dictionary` | one target | `tid, chembl_id, pref_name, target_type, organism` | Scope filter lives here: `target_type='SINGLE PROTEIN'` and `organism='Homo sapiens'` (Briefing §3.2). |
| `target_components` | target ↔ protein component | `tid, component_id` | A SINGLE PROTEIN target should have exactly one component; the extract counts exceptions. |
| `component_sequences` | one protein sequence | `component_id, accession, organism` (+ `sequence`) | `accession` = UniProt accession (Swiss-Prot 2025_03 per `version`). This is the protein key shared with BindingDB. |
| `component_class` / `protein_classification` | protein → family tree | `component_id, protein_class_id`; `protein_class_id, parent_id, pref_name, class_level` | Level 0 = root "Protein class"; **level 1 has 15 classes** (Enzyme, Membrane receptor, Ion channel, Transporter, Transcription factor, Epigenetic regulator, …); level 2 gives e.g. Kinase, Protease, Family A GPCR. We walk each node up to L1/L2 (`src/ingest/families.py`). |
| `molecule_dictionary` | one compound | `molregno, chembl_id, max_phase` | `max_phase = 4` ⇒ approved drug (useful for the repurposing universe later). |
| `compound_structures` | one structure | `molregno, standard_inchi_key` | InChIKey is the cross-database compound key (not SMILES — canonicalisation differs between sources). |
| `docs` | one publication/deposition | `doc_id, year` | `year` drives the temporal split; deposited datasets (e.g. PubChem) often have no year. |
| `source` | one data source | `src_id, src_short_name, src_description` | **src_id 7 = PUBCHEM_BIOASSAY; src_id 37 = BINDINGDB (patent bioactivity data)**. Needed to avoid double counting against BindingDB (D3). |
| `version` | release metadata | `name, creation_date, comments` | 11 rows (ChEMBL + ontology versions); the ChEMBL row is `comments LIKE 'ChEMBL Release%'`. |

## The censored-measurement trap (verified with a real row)

Imatinib (CHEMBL941), web client and SQLite agree:

- Unfiltered: **4,878** activity rows. With `pchembl_value IS NOT NULL`: **833** rows.
- All **1,335** censored rows (`>`, `<`, `>=`, `<=`) have **null** `pchembl_value` → the pChEMBL filter drops every one.
- Example: **activity_id 884645** — IC50 **>** 30,000 nM vs FLT3 (CHEMBL1974). Means "no activity up to 30 µM", not "potency = 30 µM".
- `standard_relation IS NULL` (859 rows for imatinib) is mostly non-potency endpoints (solubility, degradation); test censoring with an explicit operator list, never `!= '='`.

Rule for the pipeline: no extraction step filters on `pchembl_value`; censored rows are kept and handled explicitly by the Week 2 label policy.
