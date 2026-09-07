"""
Demo: LangChain + GitHub Copilot CLI as the LLM backend.

No API keys needed — uses your existing Copilot subscription via the CLI.

Shows three things:
  1. Custom LLM wrapper around Copilot CLI
  2. Simple chain (prompt template -> LLM -> output parser)
  3. Manual ReAct agent loop with tools

Usage:
    uv run demo.py
"""

import subprocess

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from copilot_llm import CopilotLLM


# ---------------------------------------------------------------------------
# Tools the agent can use
# ---------------------------------------------------------------------------

TOOLS = {
    "shell": lambda cmd: subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    ).stdout.strip() or "(no output)",
    "read_file": lambda path: open(path).read(),
}

TOOL_DESCRIPTIONS = """Available tools:
- shell(command): Run a shell command and return output
- read_file(path): Read contents of a file

To use a tool, respond with EXACTLY this format on its own line:
ACTION: tool_name(argument)

When you have the final answer, respond with:
ANSWER: your final answer here"""


# ---------------------------------------------------------------------------
# Demo 1: Simple Chain
# ---------------------------------------------------------------------------

def demo_chain():
    print("=" * 60)
    print("DEMO 1: Simple LangChain Chain")
    print("=" * 60)

    llm = CopilotLLM()

    prompt = PromptTemplate.from_template(
        "Explain {concept} in one sentence, suitable for a beginner programmer."
    )

    chain = prompt | llm | StrOutputParser()

    result = chain.invoke({"concept": "what a REST API is"})
    print(f"\nResult: {result}\n")


# ---------------------------------------------------------------------------
# Demo 2: ReAct Agent Loop
# ---------------------------------------------------------------------------

def demo_agent():
    print("=" * 60)
    print("DEMO 2: ReAct Agent with Tools")
    print("=" * 60)

    llm = CopilotLLM()

    query = "What Python files are in the current directory? Briefly describe what each one does."

    system_prompt = f"""You are a helpful assistant that can use tools to answer questions.

{TOOL_DESCRIPTIONS}

Think step by step. Use tools to gather information before answering."""

    history = f"{system_prompt}\n\nUser: {query}"
    max_steps = 5

    print(f"\nQuestion: {query}\n")

    for step in range(max_steps):
        response = llm.invoke(history)
        print(f"Step {step + 1}: {response}\n")

        if "ANSWER:" in response:
            answer = response.split("ANSWER:", 1)[1].strip()
            print(f"Final Answer: {answer}")
            break

        if "ACTION:" in response:
            action_line = [l for l in response.split("\n") if "ACTION:" in l][0]
            action = action_line.split("ACTION:", 1)[1].strip()

            tool_name = action.split("(", 1)[0].strip()
            tool_arg = action.split("(", 1)[1].rstrip(")")

            if tool_name in TOOLS:
                print(f"  -> Tool invoked: {tool_name}")
                print(f"     Parameters: {tool_arg!r}")
                print(f"  -> Running tool: {tool_name}")
                result = TOOLS[tool_name](tool_arg)
                print(f"  <- Result: {result[:300]}\n")
                history += f"\n{response}\nOBSERVATION: {result}"
            else:
                history += f"\n{response}\nOBSERVATION: Unknown tool '{tool_name}'"
        else:
            history += f"\n{response}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo_chain()
    print()
    demo_agent()
