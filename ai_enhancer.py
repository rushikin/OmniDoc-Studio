"""
AI Enhancement Module (OpenRouter)
Takes raw OCR output for the current page, along with context from previous pages,
and uses an LLM to correct errors and fill in missing content intelligently.
"""

import json
import os
import time
from typing import List, Dict, Any

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Load API key from environment — never hardcode secrets in source files
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")


# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert document restoration AI. Your job is to receive raw OCR output extracted from a scanned document page, which may contain:
- OCR misreads and garbled characters
- Incomplete or missing words/numbers
- Partially recognised table cells (empty or containing "???", "—", or gibberish)

You will be given:
1. CONTEXT: A summary of what has appeared on previous pages.
2. RAW_ELEMENTS: A JSON list of the current page's extracted elements.

Your task is to return a CORRECTED version of RAW_ELEMENTS as a valid JSON array, where:
- Text content is cleaned up and grammatically corrected.
- Missing table cell values are filled in intelligently based on context (e.g., sequential numbers, derived values, totals).
- You NEVER invent completely new facts. You only restore what is logically implied.
- Table structure (number of rows/columns) must be preserved exactly.
- Return ONLY the raw JSON array, no markdown, no explanation.

Each element in your output must have:
- "type": same as input ("text", "title", "table", "header", "footer")
- "content": for text/title types, a clean string.
                for table type, a 2D array (list of lists of strings).
"""

# ─── Context Manager ──────────────────────────────────────────────────────────

class ContextManager:
    """Maintains a rolling summary of previous pages for LLM context."""

    def __init__(self, max_pages: int = 5):
        self.max_pages = max_pages
        self._history: List[str] = []

    def add_page(self, page_index: int, elements: List[Dict[str, Any]]) -> None:
        """Summarize the current page and add it to history."""
        summary_parts = [f"--- Page {page_index + 1} ---"]
        for el in elements:
            if el["type"] in ("text", "title", "header"):
                summary_parts.append(f"[{el['type'].upper()}] {el['content'][:300]}")
            elif el["type"] == "table":
                rows = el.get("content", [])
                summary_parts.append(f"[TABLE] {len(rows)} row(s), {len(rows[0]) if rows else 0} col(s). Header: {rows[0] if rows else 'N/A'}")
        self._history.append("\n".join(summary_parts))

        # Keep only the last N pages
        if len(self._history) > self.max_pages:
            self._history.pop(0)

    def get_context(self) -> str:
        """Return a combined context string from the rolling history."""
        if not self._history:
            return "This is the first page of the document. No previous context available."
        return "\n\n".join(self._history)


# ─── OpenRouter Client ────────────────────────────────────────────────────────

class AIEnhancer:
    """
    Uses an LLM via OpenRouter to correct and enhance raw OCR-extracted elements.
    """

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 2.0  # seconds

    def __init__(self, model_id: str):
        """
        Args:
            model_id: The OpenRouter model ID selected interactively at startup.
        """
        if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Please add it to your .env file. "
                "Get a free key at https://openrouter.ai/keys"
            )
        self.model = model_id
        self.client = OpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://github.com/ocr-to-word",
                "X-Title": "OmniDoc Studio",
            },
        )
        self.context_manager = ContextManager(max_pages=5)
        print(f"[AI Enhancer] Ready. Model: {model_id}")

    def enhance_page(
        self,
        page_index: int,
        raw_elements: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Send raw OCR elements to the LLM for cleaning and gap-filling.

        Args:
            page_index: 0-based page number.
            raw_elements: The raw list of elements from OCREngine.

        Returns:
            A cleaned, AI-enhanced list of elements in the same format.
        """
        context = self.context_manager.get_context()

        # Prepare a simplified version of elements for the LLM
        simplified = self._simplify_for_llm(raw_elements)

        user_message = (
            f"CONTEXT (previous pages):\n{context}\n\n"
            f"RAW_ELEMENTS (current page {page_index + 1}):\n"
            f"{json.dumps(simplified, indent=2, ensure_ascii=False)}"
        )

        print(f"[AI Enhancer] Enhancing page {page_index + 1}...")

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.1,
                    max_tokens=8000,
                )

                raw_json = response.choices[0].message.content.strip()

                # Strip any accidental markdown fences
                if raw_json.startswith("```"):
                    parts = raw_json.split("```")
                    raw_json = parts[1] if len(parts) > 1 else raw_json
                    if raw_json.startswith("json"):
                        raw_json = raw_json[4:]
                raw_json = raw_json.strip()

                enhanced = json.loads(raw_json)
                print(f"[AI Enhancer] Page {page_index + 1}: {len(enhanced)} element(s) restored.")
                self.context_manager.add_page(page_index, enhanced)
                return enhanced

            except json.JSONDecodeError as e:
                print(f"[AI Enhancer] WARNING: JSON parse error on page {page_index + 1}: {e}")
                # Attempt partial JSON recovery
                try:
                    start = raw_json.index('[')
                    end = raw_json.rindex(']') + 1
                    enhanced = json.loads(raw_json[start:end])
                    print(f"[AI Enhancer] Recovered partial JSON for page {page_index + 1}.")
                    self.context_manager.add_page(page_index, enhanced)
                    return enhanced
                except Exception:
                    pass
                print("[AI Enhancer] Falling back to raw OCR output for this page.")
                self.context_manager.add_page(page_index, raw_elements)
                return raw_elements

            except Exception as e:
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))
                    print(f"[AI Enhancer] Error page {page_index + 1} (attempt {attempt}/{self.MAX_RETRIES}): {e}")
                    print(f"[AI Enhancer] Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                else:
                    print(f"[AI Enhancer] ERROR page {page_index + 1} after {self.MAX_RETRIES} attempts: {e}")
                    self.context_manager.add_page(page_index, raw_elements)
                    return raw_elements

        self.context_manager.add_page(page_index, raw_elements)
        return raw_elements

    def _simplify_for_llm(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Strip heavyweight fields (bbox, raw_html) before sending to LLM."""
        simplified = []
        for el in elements:
            simplified.append({
                "type": el.get("type", "text"),
                "content": el.get("content", ""),
            })
        return simplified
