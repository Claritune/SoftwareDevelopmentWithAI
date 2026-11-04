# LangChain Dosage Distribution Demo

Uses LangChain structured output to analyse dosage data from a synthetic
experiments report, then checks the LLM's numbers against pandas.

## Files

| File | Purpose |
|------|---------|
| `experiments_report.pdf` | Input data: synthetic experiments on men and mice (seeded, reproducible) |
| `generate_experiments_pdf.py` | Regenerates `experiments_report.pdf` |
| `dosage_distribution_analysis.py` | Fear Conditioning dosage analysis: LangChain + OpenAI structured output, pandas ground truth, plot |

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...
```

## Run

```bash
python dosage_distribution_analysis.py
```

Prints the raw Fear Conditioning runs, the LLM report (skipped if
`OPENAI_API_KEY` is unset), the pandas verification, and saves
`fear_conditioning_dosage_distribution.png` (gitignored).

To regenerate the input PDF:

```bash
python generate_experiments_pdf.py
```
