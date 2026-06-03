# Exercise: Automating Report Aggregation with AI Coding Agents

## Overview

In this exercise you will use an AI coding agent (such as Claude, Cursor, GitHub Copilot, or similar) to automate a common organizational task: combining weekly team timesheets from multiple teams into a single monthly report for HR.

You will go through the same three phases that apply to virtually any automation task, regardless of domain.

**Time estimate:** 30–60 minutes

---

## Scenario

You are a team lead managing three development teams: **Alpha**, **Beta**, and **Gamma**. Each team submits a weekly timesheet as an Excel file. All teams use the same spreadsheet format, but the teams differ in size (5–8 people), and the members hold different roles (Senior Developer, Developer, QA Engineer, DevOps).

HR requires you to submit a **combined monthly report** that aggregates hours across all three teams. The monthly report uses a different format from the weekly inputs and includes specific category-mapping rules.

Doing this by hand every month takes roughly two hours. Your goal is to produce a Python script that performs the conversion automatically.

---

## What You Are Given

### Input files (3 Excel workbooks)

Each file contains **four sheets** (one per week of the month). Every sheet has the same columns:

| Column | Description |
|--------|-------------|
| Employee Name | Full name of the team member |
| Role | Senior Developer, Developer, QA Engineer, or DevOps |
| Project | The project the hours are billed to (blank for non-project time) |
| Mon – Fri | Hours logged for each day of the week |
| Hour Type | One of: Development, QA Testing, Vacation, Sick Day, Course, Meetings |

A single employee may appear in **multiple rows** within the same week (for example, working on two projects, or having both work hours and meeting hours recorded separately).

### Output template (1 Excel workbook)

The template contains three sheets:

1. **Hours by Project** — one row per project, columns for each hour category, plus a total.
2. **Hours by Role** — one row per role, same category columns.
3. **Category Mapping** — a lookup table that defines how input hour types translate to report categories.

### Category-mapping rules

These rules are documented on the "Category Mapping" sheet of the template:

| Source Hour Type | Report Category |
|------------------|-----------------|
| Development | Development |
| QA Testing | QA Testing |
| **Vacation** | **Leave** |
| **Sick Day** | **Leave** |
| **Course** | **Training** |
| Meetings | Meetings |

The key transformations are:
- "Vacation" and "Sick Day" are **merged** into a single "Leave" category.
- "Course" is renamed to "Training".

---

## Exercise Steps

### Phase 1 — Research (Understand the data)

Ask your AI agent to examine the input files and the output template. The goal is for the agent (and you) to fully understand:

**Suggested prompts:**

1. > "I've attached three Excel files (Team_Alpha_June_2026.xlsx, Team_Beta_June_2026.xlsx, Team_Gamma_June_2026.xlsx) and a template file (Monthly_Report_Template.xlsx). Please examine all of them and describe the structure of the input files and the expected output format."

2. > "What are all the unique values in the Hour Type, Role, and Project columns across all three input files?"

3. > "Explain the category-mapping rules from the template. Which input categories get combined or renamed?"

**What to look for in the agent's response:**
- Does it correctly identify that each workbook has 4 weekly sheets?
- Does it notice that employees can have multiple rows per week?
- Does it identify the mapping rules (Vacation + Sick Day → Leave, Course → Training)?
- Does it understand that hours need to be summed across Mon–Fri columns first?

### Phase 2 — Processing (Generate the output)

Ask the agent to produce the filled monthly report.

**Suggested prompt:**

> "Using the three input files and the mapping rules from the template, produce the completed Monthly_Report_June_2026.xlsx. Aggregate total hours (Mon through Fri) across all four weeks and all three teams. Group by project on the first sheet and by role on the second sheet. Apply the category mapping: merge Vacation and Sick Day into Leave, rename Course to Training."

**What to verify:**
- Open the output and compare against the reference file provided.
- Check that totals on the "Hours by Project" sheet match the "Hours by Role" sheet (they should — it's the same data sliced differently).
- Confirm that no "Vacation", "Sick Day", or "Course" columns appear — only "Leave" and "Training".

### Phase 3 — Workflow (Create the reusable script)

Ask the agent to produce a standalone Python script that can be run every month.

**Suggested prompt:**

> "Now create a reusable Python script called `aggregate_timesheets.py` that I can run each month. It should:
> 1. Accept a folder path as a command-line argument (the folder will contain the team Excel files).
> 2. Read all .xlsx files in that folder.
> 3. Apply the same aggregation and category mapping.
> 4. Output a file called Monthly_Report.xlsx in the same folder.
> Include error handling and a summary printed to the console."

**Bonus challenges:**
- Ask the agent to add input validation (e.g., reject files with unexpected columns).
- Ask it to add a third sheet to the output that lists per-employee totals.
- Ask it to make the category mapping configurable via a separate JSON or YAML file.

---

## Evaluation Criteria

When you are done, reflect on the following:

| Criterion | What to check |
|-----------|---------------|
| **Correctness** | Does the output match the reference file? Do the numbers add up? |
| **Understanding** | Did the agent correctly interpret the input format without you hand-holding every detail? |
| **Mapping rules** | Were Vacation/Sick Day merged into Leave? Was Course renamed to Training? |
| **Reusability** | Can you drop new team files into a folder and re-run the script next month? |
| **Code quality** | Is the script readable? Does it handle edge cases (missing values, empty rows)? |

---

## Files Included

```
exercise_files/
├── Exercise_Instructions.md          ← This document
├── input/
│   ├── Team_Alpha_June_2026.xlsx     ← Weekly timesheets for Team Alpha
│   ├── Team_Beta_June_2026.xlsx      ← Weekly timesheets for Team Beta
│   ├── Team_Gamma_June_2026.xlsx     ← Weekly timesheets for Team Gamma
│   └── Monthly_Report_Template.xlsx  ← Empty output template with mapping rules
└── reference/
    └── Monthly_Report_June_2026_REFERENCE.xlsx  ← Expected output (for checking your work)
```

---

## Key Takeaways

Regardless of whether the task is timesheet aggregation, financial reconciliation, lab-result formatting, or any other structured-data transformation, the same three-phase pattern applies:

1. **Research** — Feed the AI agent sample input and output formats. Let it discover the structure rather than explaining every column manually. Verify that it understood correctly.
2. **Processing** — Ask for the concrete output. Validate against a known-good reference.
3. **Workflow** — Convert the one-shot processing into a reusable, parameterized script that anyone on your team can run.

The skill is not in writing the code — the agent does that. The skill is in clearly describing the task, verifying the result, and iterating when something is wrong.
