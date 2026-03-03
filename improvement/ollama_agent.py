"""
OllamaAgent — Base Ollama wrapper for improvement agents.
Adapted from BookAgent/agents/base.py.
"""

import time
import ollama

OLLAMA_MODEL = "gpt-oss:120b-cloud"


class OllamaAgent:
    name: str = "ImprovementAgent"
    temperature: float = 0.4
    system_prompt: str = "You are an expert software improvement assistant."

    def call(self, user_content: str) -> str:
        """Send a message to Ollama and return the response text. Retries 3 times."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user",   "content": user_content},
        ]
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = ollama.chat(
                    model=OLLAMA_MODEL,
                    messages=messages,
                    options={"temperature": self.temperature},
                )
                return response["message"]["content"].strip()
            except Exception as exc:
                last_exc = exc
                err = str(exc).lower()
                if "connection" in err or "refused" in err or "unreachable" in err:
                    if attempt < 2:
                        time.sleep(5)
                        continue
                    raise RuntimeError(
                        f"Ollama is unreachable after 3 attempts. "
                        f"Make sure Ollama is running: http://localhost:11434\n"
                        f"Error: {exc}"
                    ) from exc
                if "model" in err and ("not found" in err or "does not exist" in err):
                    raise RuntimeError(
                        f"Model '{OLLAMA_MODEL}' not found in Ollama. "
                        f"Pull it with: ollama pull {OLLAMA_MODEL}\n"
                        f"Error: {exc}"
                    ) from exc
                if attempt < 2:
                    time.sleep(5)
                    continue
        raise RuntimeError(f"{self.name} failed after 3 attempts: {last_exc}") from last_exc
