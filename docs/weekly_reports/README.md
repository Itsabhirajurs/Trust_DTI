# Weekly reports

One folder per reporting week. Each folder can be uploaded as-is to the shared Google Drive and linked in the
weekly progress form.

| Folder | Theme | Open first |
|---|---|---|
| `week02_dataset_selection/` | Dataset selection, review, attributes, planning | `Week02_Dataset_Selection_Report.pdf` |
| `week03_data_pipeline/` | Coding the data pipeline, results, trial and error | `Week03_Data_Pipeline_Report.pdf` |

Each folder contains:
- `WEEKxx_FORM_ENTRIES.md`: copy-paste text for every field of the progress form, plus the commit URL
- `Weekxx_…_Report.pdf`: a short illustrated summary for the reader
- `W<week>_NN_*.png`: figures (diagrams and charts), numbered in reading order
- `references.md`: data sources, tools and literature used that week

## Week numbering
Report weeks follow the course's reporting calendar. Figures and the roadmap use **project-plan weeks** (W1–W12
from `CLAUDE_CODE_BRIEFING.md`, project week 1 starting 21 Sep 2026). Week 2 and Week 3 reports together cover
project week 1 (data profiling I): planning and dataset review in week 2, then the coded pipeline in week 3.

## Rebuilding the figures and PDFs
Everything is generated from committed files, so numbers can never drift from the data:

```
python -m src.ingest.profile_source_confounding     # only if reports/stage0 changed (needs local data)
python docs/weekly_reports/_build/figures.py        # charts from reports/stage0/*.csv
python docs/weekly_reports/_build/render.py         # diagrams (HTML → PNG) and reports (HTML → PDF) via headless Chrome/Edge
```

- Diagram sources: `_build/diagrams/*.html` (shared style in `style.css`)
- Report sources: `_build/week0X_report.html` (print style in `print.css`)
- For a new week, copy the previous week's report HTML and form file, then add diagrams to `_build/diagrams/` with a
  `<meta name="out">` pointing into the new folder.
