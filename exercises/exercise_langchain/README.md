# Structured Extraction Pipeline — LangChain + Ollama

Extract structured, validated data from messy unstructured text using a local LLM.

## Architecture

```
Raw Text → Prompt Template → LLM (Ollama) → Output Parser → Pydantic Model
                                                                  ↓
                                                            Validated Data
```

## Prerequisites

```bash
pip install langchain langchain-ollama pydantic
ollama pull llama3.1
```

## What's Implemented

The exercise provides a complete working pipeline that extracts company information from unstructured text.

### Pydantic Schema

A `CompanyInfo` model defines the extraction target — company name, industry, stage, employee count, tech stack, remote policy, and a one-sentence summary. Field descriptions guide the LLM on what to extract. Pydantic validators enforce allowed values for `stage` and `remote_policy`, acting as a safety net beyond what the LLM produces.

### Extraction Chain (LCEL)

Three components wired together with LangChain Expression Language pipe syntax:

```python
chain = prompt | llm | parser
```

- `PydanticOutputParser` — generates JSON format instructions from the Pydantic schema automatically
- `ChatPromptTemplate` — injects the raw text and format instructions into a system+human message pair
- `ChatOllama` — local LLM with `temperature=0` for deterministic extraction

### Sample Texts

Three texts of varying difficulty:

1. A clean VC-style company blurb (NeuroGrid, MLOps)
2. A casual meetup conversation (Payable, B2B payments)
3. A corporate press release (GlobalRetail Corp, enterprise migration)

### Error Handling

Parsing failures are caught gracefully, with a placeholder for retry/fallback logic.

## Running

```bash
python structured_extraction_exercise.py
```

The pipeline extracts structured `CompanyInfo` from each sample text and prints the results.

## Challenges

### Challenge 1 — Add a Field

Add a `funding_stage` field to `CompanyInfo` with allowed values: `pre-seed`, `seed`, `series-a`, `series-b`, `series-c`, `growth`, `public`, `unknown`. Write a validator that normalizes the value (e.g., "Series B" → "series-b").

### Challenge 2 — Text Type Router

Create a second Pydantic model, for example `JobPosting` (title, company, required skills, salary range, seniority level). Build a two-step chain: the first LLM call classifies the input text as either "company-description" or "job-posting", then routes to the appropriate extraction model. This bridges into the routing chain pattern.

### Challenge 3 — Retry with Error Feedback

When parsing fails, feed the LLM's raw output and the validation error message back into a second LLM call, asking it to fix the JSON. This is a common agentic pattern — the error becomes an observation that drives the next action.

### Challenge 4 — Model Comparison

Run the same pipeline across different Ollama models (llama3.1, mistral, gemma2). Compare extraction quality: which models follow format instructions best? Which hallucinate field values? Build a simple scoring function that checks each field against expected values.

### Challenge 5 — Real-World Input

Copy a real company "About" page or a LinkedIn job posting and run it through the pipeline. Observe where it breaks and adjust the prompt template to handle messier, longer, more ambiguous input.