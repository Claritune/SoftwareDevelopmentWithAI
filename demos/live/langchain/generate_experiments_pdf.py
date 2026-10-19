"""Generate a PDF report of experiments conducted on men and mice."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import date, timedelta
import random

random.seed(42)

# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------

CATEGORIES = {
    "Behavioral": [
        "Open Field Test",
        "Morris Water Maze",
        "Elevated Plus Maze",
        "Fear Conditioning",
        "Forced Swim Test",
        "Rotarod Performance Test",
        "Passive Avoidance Test",
        "Novel Object Recognition",
        "Y-Maze Spontaneous Alternation",
        "Social Interaction Test",
    ],
    "Pharmacological": [
        "Dose-Response Assay",
        "LD50 Determination",
        "Drug Metabolism Study",
        "Receptor Binding Assay",
        "Analgesic Efficacy Test",
        "Anti-inflammatory Screen",
        "Antibiotic Susceptibility Test",
        "CNS Depressant Screen",
        "Cardiovascular Effect Study",
        "Pharmacokinetics Profiling",
    ],
    "Genetic / Genomic": [
        "Genome-Wide Association Study (GWAS)",
        "CRISPR-Cas9 Gene Knockout",
        "RNA Sequencing (RNA-seq)",
        "PCR Genotyping",
        "Western Blot Analysis",
        "Chromatin Immunoprecipitation (ChIP)",
        "Single-Cell Sequencing",
        "Gene Expression Profiling",
        "Transgenic Model Generation",
        "Epigenetic Methylation Analysis",
    ],
    "Neurological": [
        "EEG Recording",
        "Patch-Clamp Electrophysiology",
        "Histological Brain Staining",
        "Cognitive Function Assessment",
        "Seizure Threshold Test",
        "Dopamine Level Assay",
        "Serotonin Receptor Study",
        "Tau Protein Aggregation Assay",
        "Neuroinflammation Marker Panel",
        "Long-Term Potentiation (LTP) Study",
    ],
    "Immunological": [
        "ELISA Cytokine Profiling",
        "Flow Cytometry Panel",
        "T-Cell Proliferation Assay",
        "NK Cell Cytotoxicity Test",
        "Antibody Titer Measurement",
        "Macrophage Phagocytosis Assay",
        "Complement Activation Test",
        "Allergy Challenge Model",
        "Sepsis Survival Model",
        "Vaccine Efficacy Trial",
    ],
}

OUTCOMES = ["Completed", "Completed", "Completed", "Inconclusive", "Pending Review"]
SUBJECTS_MEN = [f"HM-{100 + i}" for i in range(50)]
SUBJECTS_MICE = [f"MM-{200 + i}" for i in range(50)]
BASE_DATE = date(2025, 1, 1)


def random_date(offset_days=365):
    return (BASE_DATE + timedelta(days=random.randint(0, offset_days))).strftime("%Y-%m-%d")


def build_experiment_runs(exp_type_index, cat_index):
    """Return 5 experiment run rows for a given experiment type."""
    rows = []
    for run in range(1, 6):
        subject_pool = SUBJECTS_MEN if run % 2 == 0 else SUBJECTS_MICE
        subject = subject_pool[(cat_index * 10 + exp_type_index + run) % len(subject_pool)]
        species = "Human" if subject.startswith("HM") else "Mouse"
        outcome = OUTCOMES[run - 1]
        dose = f"{random.randint(5, 100)} mg/kg"
        duration = f"{random.randint(1, 28)} days"
        rows.append([
            str(run),
            subject,
            species,
            dose,
            duration,
            random_date(),
            outcome,
        ])
    return rows


# ---------------------------------------------------------------------------
# PDF construction
# ---------------------------------------------------------------------------

def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=20,
        spaceAfter=6,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a3c5e"),
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.grey,
    )
    category_style = ParagraphStyle(
        "CategoryHeading",
        parent=styles["Heading1"],
        fontSize=14,
        spaceBefore=14,
        spaceAfter=6,
        textColor=colors.HexColor("#1a3c5e"),
    )
    exp_type_style = ParagraphStyle(
        "ExpTypeHeading",
        parent=styles["Heading2"],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=4,
        textColor=colors.HexColor("#2e6da4"),
    )

    col_headers = ["Run #", "Subject ID", "Species", "Dose", "Duration", "Date", "Outcome"]
    col_widths = [1.2 * cm, 2.2 * cm, 2.0 * cm, 2.4 * cm, 2.4 * cm, 2.8 * cm, 3.2 * cm]

    def make_table(data_rows):
        table_data = [col_headers] + data_rows
        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3c5e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c0c8d0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return tbl

    story = []

    # Cover / title
    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("Experimental Research Registry", title_style))
    story.append(Paragraph(
        "Experiments Conducted on Human and Murine Subjects — Report Date: " +
        date.today().strftime("%B %d, %Y"),
        subtitle_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a3c5e")))
    story.append(Spacer(1, 0.4 * cm))

    # Summary table
    summary_header = ["Category", "Experiment Types", "Runs per Type", "Total Runs"]
    summary_rows = [
        [cat, "10", "5", "50"] for cat in CATEGORIES
    ]
    summary_rows.append(["TOTAL", str(len(CATEGORIES) * 10), "5",
                          str(len(CATEGORIES) * 10 * 5)])
    summary_tbl = Table(
        [summary_header] + summary_rows,
        colWidths=[5 * cm, 4 * cm, 4 * cm, 3.2 * cm],
    )
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2e6da4")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.HexColor("#f0f4f8"), colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#d0dce8")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c0c8d0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(Paragraph("Overview Summary", styles["Heading2"]))
    story.append(summary_tbl)
    story.append(PageBreak())

    # Per-category sections
    for cat_index, (category, exp_types) in enumerate(CATEGORIES.items()):
        story.append(Paragraph(f"Category: {category}", category_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#2e6da4")))
        story.append(Spacer(1, 0.2 * cm))

        for exp_index, exp_type in enumerate(exp_types):
            story.append(Paragraph(
                f"{exp_index + 1}. {exp_type}", exp_type_style
            ))
            runs = build_experiment_runs(exp_index, cat_index)
            story.append(make_table(runs))
            story.append(Spacer(1, 0.3 * cm))

        if cat_index < len(CATEGORIES) - 1:
            story.append(PageBreak())

    doc.build(story)
    print(f"PDF written to: {output_path}")


if __name__ == "__main__":
    build_pdf("experiments_report.pdf")
