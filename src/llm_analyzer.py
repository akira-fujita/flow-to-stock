import json
import re
from dataclasses import dataclass

from google import genai
from pydantic import ValidationError

from src.models import AnalysisResult, SlackThread


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

SYSTEM_PROMPT = """You are an expert at analyzing Slack discussions and extracting structured insights.

Given a Slack thread, analyze the discussion and output a JSON object with the following structure:
{
  "theme": "One-line summary of the discussion topic",
  "structure": {
    "premises": ["List of assumptions and preconditions"],
    "key_issues": ["Main points of discussion, disagreements, or unresolved items"],
    "conclusions_or_current_state": ["Current conclusions or state of the discussion"]
  },
  "next_decision_required": "The specific decision that must be made to move forward (not a vague TODO)",
  "suggested_next_action": "Concrete action: who does what by when",
  "suggested_owner": "Person most likely responsible (from thread participants)",
  "new_concepts": ["New terms, concepts, or keywords introduced in this discussion"],
  "strategic_implications": ["Medium/long-term impacts or architectural implications"],
  "risk_signals": ["Undefined risks, misalignments, or uncertainties detected"]
}

Rules:
- Output ONLY valid JSON, no markdown fences, no extra text
- Match the language of the input: if the discussion is in Japanese, output in Japanese
- next_decision_required must be a specific decision, not a generic TODO
- suggested_next_action must include who, what, and when
- Be concise but thorough"""


def format_thread_for_prompt(thread: SlackThread, memo: str | None = None) -> str:
    """Format a SlackThread into a text prompt for the LLM."""
    lines = [f"Channel: #{thread.channel_name}", ""]

    for msg in thread.messages:
        ts_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
        lines.append(f"[{ts_str}] {msg.user}: {msg.text}")

    if memo:
        lines.append("")
        lines.append(f"Additional context from the user: {memo}")

    return "\n".join(lines)


def analyze_thread(
    thread: SlackThread,
    api_key: str,
    memo: str | None = None,
    model: str = "gemini-2.0-flash",
) -> tuple[AnalysisResult, TokenUsage]:
    """Analyze a Slack thread using Gemini and return structured result with token usage."""
    client = genai.Client(api_key=api_key)
    prompt_text = format_thread_for_prompt(thread, memo)

    total_usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

    for attempt in range(2):
        response = client.models.generate_content(
            model=model,
            contents=prompt_text,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=4096,
            ),
        )

        if response.usage_metadata:
            total_usage.prompt_tokens += response.usage_metadata.prompt_token_count or 0
            total_usage.completion_tokens += response.usage_metadata.candidates_token_count or 0
            total_usage.total_tokens += response.usage_metadata.total_token_count or 0

        raw_text = response.text or ""

        # Strip markdown fences (```json ... ``` or ``` ... ```)
        stripped = re.sub(r"^```(?:json)?\s*\n?", "", raw_text.strip())
        stripped = re.sub(r"\n?```\s*$", "", stripped).strip()

        try:
            data = json.loads(stripped)
            return AnalysisResult.model_validate(data), total_usage
        except (json.JSONDecodeError, ValidationError):
            if attempt == 0:
                continue
            raise

    raise RuntimeError("Failed to parse LLM response after retries")
