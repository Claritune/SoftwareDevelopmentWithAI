"""Custom LangChain LLM that uses GitHub Copilot CLI as the backend."""

import subprocess
from typing import Any

from langchain_core.language_models.llms import LLM


class CopilotLLM(LLM):
    """LangChain LLM wrapper around GitHub Copilot CLI (non-interactive mode)."""

    model: str = "claude-sonnet-5"
    timeout: int = 60

    @property
    def _llm_type(self) -> str:
        return "copilot-cli"

    def _call(self, prompt: str, stop: list[str] | None = None, **kwargs: Any) -> str:
        result = subprocess.run(
            [
                "copilot",
                "-p", prompt,
                "-s",
                "--model", self.model,
                "--no-auto-update",
            ],
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Copilot CLI failed: {result.stderr}")
        return result.stdout.strip()
