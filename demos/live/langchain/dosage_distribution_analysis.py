"""
Analyze dosage distribution for Fear Conditioning experiments (mice vs. men)
using LangChain + OpenAI structured output.

Requires: OPENAI_API_KEY environment variable
"""

import os
import random
from typing import Literal

import matplotlib.pyplot as plt
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Reproduce Fear Conditioning data (same seed/logic as generate_experiments_pdf.py)
# ---------------------------------------------------------------------------

random.seed(42)

CATEGORIES_ORDER = [
    "Behavioral", "Pharmacological", "Genetic / Genomic",
    "Neurological", "Immunological",
]

BEHAVIORAL_TYPES = [
    "Open Field Test", "Morris Water Maze", "Elevated Plus Maze",
    "Fear Conditioning", "Forced Swim Test", "Rotarod Performance Test",
    "Passive Avoidance Test", "Novel Object Recognition",
    "Y-Maze Spontaneous Alternation", "Social Interaction Test",
]

OUTCOMES = ["Completed", "Completed", "Completed", "Inconclusive", "Pending Review"]
SUBJECTS_MEN = [f"HM-{100 + i}" for i in range(50)]
SUBJECTS_MICE = [f"MM-{200 + i}" for i in range(50)]

from datetime import date, timedelta

BASE_DATE = date(2025, 1, 1)


def random_date():
    return (BASE_DATE + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d")


def build_all_behavioral_runs():
    """Reproduce all Behavioral runs so RNG state matches the PDF generator."""
    rows = []
    cat_index = 0  # Behavioral is index 0
    for exp_index, exp_type in enumerate(BEHAVIORAL_TYPES):
        for run in range(1, 6):
            subject_pool = SUBJECTS_MEN if run % 2 == 0 else SUBJECTS_MICE
            subject = subject_pool[(cat_index * 10 + exp_index + run) % len(subject_pool)]
            species = "Human" if subject.startswith("HM") else "Mouse"
            dose = random.randint(5, 100)
            duration = random.randint(1, 28)
            exp_date = random_date()
            outcome = OUTCOMES[run - 1]
            rows.append({
                "experiment_type": exp_type,
                "run": run,
                "subject_id": subject,
                "species": species,
                "dose_mg_kg": dose,
                "duration_days": duration,
                "date": exp_date,
                "outcome": outcome,
            })
    return rows


all_rows = build_all_behavioral_runs()
df_all = pd.DataFrame(all_rows)

# Filter only Fear Conditioning rows
df_fc = df_all[df_all["experiment_type"] == "Fear Conditioning"].copy()
df_fc = df_fc.reset_index(drop=True)

print("=" * 60)
print("Fear Conditioning — raw data")
print("=" * 60)
print(df_fc[["run", "subject_id", "species", "dose_mg_kg", "duration_days", "outcome"]].to_string(index=False))
print()

# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

class SpeciesDosageStats(BaseModel):
    species: Literal["Human", "Mouse"]
    n: int = Field(description="Number of experiments")
    min_dose: float = Field(description="Minimum dose in mg/kg")
    max_dose: float = Field(description="Maximum dose in mg/kg")
    mean_dose: float = Field(description="Mean dose in mg/kg")
    median_dose: float = Field(description="Median dose in mg/kg")
    std_dose: float = Field(description="Standard deviation of dose in mg/kg")
    distribution_shape: str = Field(
        description="Brief description of the distribution shape, e.g. 'roughly uniform', 'right-skewed'"
    )
    clinical_note: str = Field(
        description="One-sentence note on whether the dose range appears safe/appropriate for the species"
    )


class FearConditioningDosageReport(BaseModel):
    experiment: str = Field(default="Fear Conditioning")
    humans: SpeciesDosageStats
    mice: SpeciesDosageStats
    comparative_summary: str = Field(
        description="2-3 sentence comparison of dosage distributions between humans and mice"
    )


# ---------------------------------------------------------------------------
# Build LangChain chain
# ---------------------------------------------------------------------------

def dataframe_to_text(df: pd.DataFrame) -> str:
    lines = []
    for _, row in df.iterrows():
        lines.append(
            f"  Run {row['run']}: {row['species']} {row['subject_id']}, "
            f"dose={row['dose_mg_kg']} mg/kg, duration={row['duration_days']} days, "
            f"outcome={row['outcome']}"
        )
    return "\n".join(lines)


data_text = dataframe_to_text(df_fc)

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a biostatistician specializing in preclinical and clinical research. "
        "Analyze the provided Fear Conditioning experiment data and return a structured "
        "dosage distribution report. Compute exact statistics from the data — do not invent values.",
    ),
    (
        "human",
        "Here are the 5 Fear Conditioning experiment runs:\n\n{data}\n\n"
        "Provide the dosage distribution statistics separately for Human and Mouse subjects.",
    ),
])

api_key = os.environ.get("OPENAI_API_KEY")

# ---------------------------------------------------------------------------
# Run analysis
# ---------------------------------------------------------------------------

report: FearConditioningDosageReport | None = None

if not api_key:
    print("⚠  OPENAI_API_KEY not set — skipping LangChain LLM step.")
    print("   Set the variable and re-run to get the AI-generated report.\n")
else:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    chain = prompt | llm.with_structured_output(FearConditioningDosageReport)
    print("Querying LangChain / OpenAI for dosage distribution analysis...")
    report = chain.invoke({"data": data_text})

if report:
    print()
    print("=" * 60)
    print("LangChain Dosage Distribution Report — Fear Conditioning")
    print("=" * 60)

    for stats in (report.humans, report.mice):
        print(f"\nSpecies : {stats.species}")
        print(f"  N              : {stats.n}")
        print(f"  Min dose       : {stats.min_dose} mg/kg")
        print(f"  Max dose       : {stats.max_dose} mg/kg")
        print(f"  Mean dose      : {stats.mean_dose} mg/kg")
        print(f"  Median dose    : {stats.median_dose} mg/kg")
        print(f"  Std dev        : {stats.std_dose} mg/kg")
        print(f"  Shape          : {stats.distribution_shape}")
        print(f"  Clinical note  : {stats.clinical_note}")

    print(f"\nComparative summary:\n  {report.comparative_summary}")

# ---------------------------------------------------------------------------
# Verify with pandas (ground truth)
# ---------------------------------------------------------------------------

print()
print("=" * 60)
print("Pandas verification (ground truth)")
print("=" * 60)
for species, grp in df_fc.groupby("species"):
    d = grp["dose_mg_kg"]
    print(f"\n{species}  (n={len(d)})")
    print(f"  min={d.min()}  max={d.max()}  mean={d.mean():.1f}  "
          f"median={d.median():.1f}  std={d.std(ddof=1):.2f}")

# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------

fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=False)
fig.suptitle("Fear Conditioning — Dosage Distribution by Species", fontsize=13, fontweight="bold")

colors_map = {"Human": "#2e6da4", "Mouse": "#e07b39"}

for ax, (species, grp) in zip(axes, df_fc.groupby("species")):
    doses = grp["dose_mg_kg"].values
    ax.bar(range(1, len(doses) + 1), doses, color=colors_map[species], alpha=0.85, width=0.5)
    ax.axhline(doses.mean(), color="black", linestyle="--", linewidth=1, label=f"Mean = {doses.mean():.1f}")
    ax.set_title(f"{species} (n={len(doses)})", fontsize=11)
    ax.set_xlabel("Run #")
    ax.set_ylabel("Dose (mg/kg)")
    ax.set_xticks(range(1, len(doses) + 1))
    ax.legend(fontsize=9)
    ax.set_ylim(0, 110)

plt.tight_layout()
plot_path = "fear_conditioning_dosage_distribution.png"
plt.savefig(plot_path, dpi=150)
print(f"\nPlot saved to: {plot_path}")
plt.show()
