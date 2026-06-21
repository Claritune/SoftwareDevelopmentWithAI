"""
Exercise: Structured Extraction Pipeline with LangChain + Ollama
================================================================

Goal: Extract structured, validated data from messy unstructured text
using LangChain prompt templates, output parsers, and Pydantic models.

Prerequisites:
  - pip install langchain langchain-ollama pydantic
  - Ollama running locally with a model pulled:
      ollama pull llama3.1

Architecture:
  Raw Text → Prompt Template → LLM (Ollama) → Output Parser → Pydantic Model
                                                                    ↓
                                                              Validated Data

What you'll learn:
  1. Defining extraction schemas with Pydantic
  2. Using LangChain's PydanticOutputParser to generate format instructions
  3. Building prompt templates that guide the LLM to produce structured output
  4. Chaining components together with LCEL (LangChain Expression Language)
  5. Handling validation errors gracefully
"""

from pydantic import BaseModel, Field, field_validator
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from typing import Optional
import json

# ---------------------------------------------------------------------------
# Step 1: Define extraction schemas with Pydantic
# ---------------------------------------------------------------------------
# These models define WHAT we want to extract and enforce validation rules.
# The Field descriptions guide the LLM on what each field means.

class CompanyInfo(BaseModel):
    """Extracted information about a company from unstructured text."""

    name: str = Field(description="The company name")
    industry: str = Field(description="The industry or sector (e.g., fintech, healthcare, e-commerce)")
    stage: str = Field(description="Company stage: 'startup', 'scaleup', or 'enterprise'")
    employee_count: Optional[int] = Field(
        default=None,
        description="Approximate number of employees, or null if not mentioned"
    )
    tech_stack: list[str] = Field(
        default_factory=list,
        description="Technologies, languages, and frameworks mentioned"
    )
    remote_policy: str = Field(
        default="unknown",
        description="One of: 'remote', 'hybrid', 'onsite', or 'unknown'"
    )
    summary: str = Field(
        description="A one-sentence summary of what the company does"
    )

    # Pydantic validators add a safety net beyond what the LLM produces
    @field_validator("stage")
    @classmethod
    def validate_stage(cls, v: str) -> str:
        allowed = {"startup", "scaleup", "enterprise"}
        v_lower = v.strip().lower()
        if v_lower not in allowed:
            raise ValueError(f"stage must be one of {allowed}, got '{v}'")
        return v_lower

    @field_validator("remote_policy")
    @classmethod
    def validate_remote_policy(cls, v: str) -> str:
        allowed = {"remote", "hybrid", "onsite", "unknown"}
        v_lower = v.strip().lower()
        if v_lower not in allowed:
            raise ValueError(f"remote_policy must be one of {allowed}, got '{v}'")
        return v_lower


# ---------------------------------------------------------------------------
# Step 2: Sample unstructured texts to extract from
# ---------------------------------------------------------------------------

SAMPLE_TEXTS = [
    """
    NeuroGrid is a 3-year-old AI infrastructure company with about 120 engineers
    building distributed training platforms. Their stack is mostly Python and Rust,
    with heavy use of Kubernetes, Ray, and PyTorch. They recently moved to a hybrid
    model — 3 days in their SF office, 2 remote. They've raised Series B and are
    scaling fast in the MLOps space.
    """,

    """
    Just came back from a meetup where I met folks from Payable — they're doing
    something interesting in B2B payments. Small team, maybe 15 people? Very early
    stage, pre-Series A. They're building everything in TypeScript, using Next.js
    and Stripe Connect. Fully remote team spread across Europe. They're trying to
    automate invoice reconciliation for SMBs.
    """,

    """
    GlobalRetail Corp announced they're modernizing their legacy systems. The
    40-year-old retail giant with 50,000+ employees worldwide is migrating from
    their mainframe COBOL systems to a microservices architecture using Java,
    Spring Boot, and AWS. Everyone's back in the office since last year. They
    operate over 2,000 stores and are building a new unified commerce platform.
    """,
]


# ---------------------------------------------------------------------------
# Step 3: Build the extraction chain
# ---------------------------------------------------------------------------

def build_extraction_chain(model_name: str = "llama3.1"):
    """
    Construct a LangChain chain that extracts CompanyInfo from raw text.

    Components:
      - PydanticOutputParser: generates format instructions from the schema
      - ChatPromptTemplate: injects the text + format instructions into a prompt
      - ChatOllama: the local LLM
      - Chain: prompt | llm | parser  (LCEL pipe syntax)
    """

    # The parser generates format instructions from the Pydantic model
    # and knows how to parse the LLM's response back into a CompanyInfo object
    parser = PydanticOutputParser(pydantic_object=CompanyInfo)

    # The prompt template includes the format instructions so the LLM
    # knows exactly what JSON structure to produce
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a data extraction assistant. "
            "Extract structured information from the provided text. "
            "Respond ONLY with the requested JSON format, no other text.\n\n"
            "{format_instructions}"
        ),
        (
            "human",
            "Extract company information from this text:\n\n{text}"
        ),
    ])

    # Local LLM via Ollama
    llm = ChatOllama(
        model=model_name,
        temperature=0,  # deterministic output for extraction tasks
    )

    # LCEL chain: prompt → LLM → parser
    chain = prompt | llm | parser

    return chain, parser


# ---------------------------------------------------------------------------
# Step 4: Run extraction with error handling
# ---------------------------------------------------------------------------

def extract_company_info(text: str, chain, parser) -> CompanyInfo | dict:
    """
    Run the extraction chain on a piece of text.
    Handles parsing failures gracefully with a retry/fallback strategy.
    """
    try:
        result = chain.invoke({
            "text": text,
            "format_instructions": parser.get_format_instructions(),
        })
        return result

    except Exception as e:
        print(f"  ⚠ Extraction failed: {e}")
        print(f"  → In production, you'd retry with a refined prompt or fallback model")
        return {"error": str(e), "raw_text": text[:100] + "..."}


# ---------------------------------------------------------------------------
# Step 5: Main — run the pipeline
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Structured Extraction Pipeline — LangChain + Ollama")
    print("=" * 70)

    chain, parser = build_extraction_chain()

    print(f"\n📋 Format instructions sent to the LLM:\n")
    print(parser.get_format_instructions()[:300] + "...\n")

    for i, text in enumerate(SAMPLE_TEXTS, 1):
        print("-" * 70)
        print(f"📝 Sample {i}:")
        print(text.strip())
        print()

        result = extract_company_info(text, chain, parser)

        if isinstance(result, CompanyInfo):
            print(f"✅ Extracted CompanyInfo:")
            print(f"   Name:         {result.name}")
            print(f"   Industry:     {result.industry}")
            print(f"   Stage:        {result.stage}")
            print(f"   Employees:    {result.employee_count}")
            print(f"   Tech Stack:   {', '.join(result.tech_stack)}")
            print(f"   Remote:       {result.remote_policy}")
            print(f"   Summary:      {result.summary}")
        else:
            print(f"❌ Failed: {result}")

        print()

    print("=" * 70)
    print("Done!")


# ---------------------------------------------------------------------------
# Challenges:
# ---------------------------------------------------------------------------
# 1. Add a new field: funding_stage (pre-seed, seed, series-a, series-b, etc.)
#    with a validator that normalizes the value.
#
# 2. Create a second Pydantic model (e.g., JobPosting) and build a "router"
#    that first classifies the text type, then picks the right extraction model.
#    (This bridges into the Option C routing chain concept.)
#
# 3. Add a retry mechanism: if parsing fails, feed the error message back to
#    the LLM and ask it to fix its output. This is a common agentic pattern.
#
# 4. Compare extraction quality across different Ollama models
#    (llama3.1 vs mistral vs gemma2). Which handles the format instructions best?
#
# 5. Try with a real-world text: copy a company's "About" page or a LinkedIn
#    job posting and see how well the pipeline handles truly messy input.
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    main()