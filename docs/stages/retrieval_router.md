# Deterministic retrieval router and literature evidence prototype

## Purpose

The router is an explicit policy layer between a Network 1 prediction and literature retrieval. It uses two inputs only:

1. The saved DTI prediction set: `ACTIVE`, `INACTIVE`, or `ACTIVE|INACTIVE`.
2. A curated Network 2 disease-anchor tier: `STRONG`, `MODERATE`, `WEAK`, or `NONE`.

No LLM chooses the policy. No article's truth is inferred from query wording.

## Seven policies

| Prediction set | Disease anchor | Policy | Retrieval priority |
|---|---|---|---|
| ACTIVE | STRONG | CONFIRM | Mechanistic evidence, then disease context |
| ACTIVE | MODERATE | CONTEXTUALISE | Disease linkage, mechanism secondary |
| ACTIVE | WEAK/NONE | INVESTIGATE | General background and target mechanism |
| ACTIVE+INACTIVE | STRONG | CHALLENGE | Counter-evidence and safety first |
| ACTIVE+INACTIVE | MODERATE | CHALLENGE_CONTEXT | Counter-evidence, then disease linkage |
| ACTIVE+INACTIVE | WEAK/NONE | LOW_PRIORITY | Small, low-priority search |
| INACTIVE | Any | STOP | No adaptive retrieval |

`UNKNOWN` is an evidence-direction label, not a prediction-set state. A missing result or missing annotation is never converted into `CONTRADICT`.

## Anchor score source

Use Open Targets 26.09 `association_overall_direct` as the overall target–disease score. This is kept separate from `association_by_datasource_direct`, whose source-specific scores remain provenance records. Open Targets' overall score aggregates evidence across data sources and is still a prioritisation/association score, not a causal probability. The prototype uses the 25th and 75th percentiles of observed overall-direct association scores to define weak/moderate/strong tiers. Those cutoffs are a transparent engineering convention, not biological truths; they must be frozen before policy evaluation.

## Literature retrieval

The first retrieval backend is the Europe PMC REST search API. Four query intents are generated:

- `MECHANISTIC`: drug + gene + interaction terms
- `COUNTER`: drug + gene + resistance/failure/no-effect terms
- `DISEASE_CONTEXT`: gene + disease
- `GENERAL`: drug + gene

Each result stores a stable source identifier, PMID/PMCID/DOI where available, title, abstract, publication metadata, source URL, exact query and retrieval timestamp. The initial direction is always `UNANNOTATED`; retrieval intent is not biological evidence direction.

## Comparison design

The same fixed candidate table is evaluated under:

- `fixed`
- `uncertainty_only`
- `disease_only`
- `combined`

Each has the same maximum per-candidate document budget. STOP can intentionally use zero of that budget. Publications are deduplicated within candidate × strategy, while multiple query intents are retained.

## Human annotation protocol

Annotate the paper's content, not the search query.

- `SUPPORT`: relevant content that supports the stated drug–protein/disease hypothesis.
- `CONTRADICT`: relevant content that directly weakens or challenges the stated hypothesis.
- `UNKNOWN`: the article is retrieved, but the available title/abstract does not permit a defensible directional decision or it is not relevant.
- Evidence categories: `MECHANISTIC`, `DISEASE_CONTEXT`, `COUNTER`, `SAFETY`, `OTHER`.

Use a short rationale. The preparation script deduplicates each candidate–publication pair so a paper retrieved by multiple policies is annotated once. The worksheet hides strategy, search query, retrieval intent, prediction confidence and anchor tier. Keep `retrieval_strategy_manifest.csv` and `retrieval_strategy_key.csv` away from annotators until labels are complete; the evaluator uses them to expand one blinded annotation back onto all strategy exposures. Resolve disagreements before calculating metrics.

## Metrics and limitations

- Relevant-evidence precision = (SUPPORT + CONTRADICT) / all retrieved records.
- Annotation coverage = direction-labelled records / all retrieved records.
- Counter-evidence share = CONTRADICT / (SUPPORT + CONTRADICT).
- Pooled candidate-set counter-evidence recall = the share of all distinct CONTRADICT-labelled publications found by each strategy, where the denominator is the union of counter-labelled publications retrieved by the four policies for the same fixed candidates.

The pooled recall denominator is **not the whole literature corpus**. It is a within-experiment comparative diagnostic and must not be called exhaustive literature recall. A later, externally adjudicated candidate/evidence set is needed for stronger recall claims. The policies must never be described as improving retrieval until measured results support that conclusion.
