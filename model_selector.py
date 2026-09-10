"""
OpenRouter Free Model Selector
Fetches ALL currently available free models from OpenRouter API at runtime,
displays them as a numbered list, and lets the user pick one interactively.
"""

import os
import sys
import json
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.prompt import IntPrompt
from rich.panel import Panel
from rich.text import Text

load_dotenv()

console = Console()

# Load API key from environment — never hardcode secrets
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"

# Cache file to avoid re-fetching on every run
_CACHE_FILE = Path("./logs/model_cache.json")
_CACHE_MAX_AGE_HOURS = 6


def fetch_free_models(use_cache: bool = True) -> list[dict]:
    """
    Query the OpenRouter /models endpoint and return only the free models.
    Caches results for _CACHE_MAX_AGE_HOURS hours to speed up subsequent runs.
    A model is free if prompt pricing is "0"/"0.0" OR its ID ends with ':free'.

    Returns:
        List of dicts: [{id, name, context_length, description}, ...]
        Sorted alphabetically by name.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        console.print("[bold yellow]OPENROUTER_API_KEY not set — using fallback model list.[/bold yellow]")
        return _fallback_models()

    # Try cache first
    if use_cache and _CACHE_FILE.exists():
        age_hours = (time.time() - _CACHE_FILE.stat().st_mtime) / 3600
        if age_hours < _CACHE_MAX_AGE_HOURS:
            try:
                with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                console.print(f"[dim]Using cached model list ({age_hours:.1f}h old).[/dim]")
                return cached
            except Exception:
                pass

    with console.status("[bold cyan]Fetching available models from OpenRouter...", spinner="dots"):
        try:
            response = httpx.get(
                OPENROUTER_MODELS_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://github.com/ocr-to-word",
                    "X-Title": "OmniDoc Studio",
                },
                timeout=15,
            )
            response.raise_for_status()
            all_models = response.json().get("data", [])
        except httpx.HTTPStatusError as e:
            console.print(f"[bold red]HTTP error fetching models: {e}[/bold red]")
            return _fallback_models()
        except Exception as e:
            console.print(f"[bold red]Network error: {e}[/bold red]")
            return _fallback_models()

        free_models = []
        for model in all_models:
            model_id = model.get("id", "")
            pricing = model.get("pricing", {})
            prompt_price = str(pricing.get("prompt", "1"))
            completion_price = str(pricing.get("completion", "1"))
            is_free = (
                model_id.endswith(":free")
                or (prompt_price in ("0", "0.0") and completion_price in ("0", "0.0"))
            )
            if is_free:
                free_models.append({
                    "id": model_id,
                    "name": model.get("name", model_id),
                    "context_length": model.get("context_length", 0),
                    "description": (model.get("description") or "").strip()[:120],
                })

        free_models.sort(key=lambda m: m["name"].lower())
        console.print(f"[bold green]Found {len(free_models)} free model(s).[/bold green]\n")

        # Save to cache
        try:
            _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(free_models, f)
        except Exception:
            pass

        return free_models


def _fallback_models() -> list[dict]:
    """Return a hardcoded list of known free models if the API call fails."""
    console.print("[bold yellow]Using fallback model list.[/bold yellow]\n")
    return [
        {"id": "google/gemini-2.0-flash-exp:free",    "name": "Google Gemini 2.0 Flash (free)",       "context_length": 1048576, "description": "Google's fast multimodal model."},
        {"id": "google/gemma-3-27b-it:free",           "name": "Google Gemma 3 27B (free)",             "context_length": 131072,  "description": "Google open weights model."},
        {"id": "meta-llama/llama-3.3-70b-instruct:free","name": "Meta Llama 3.3 70B Instruct (free)",  "context_length": 131072,  "description": "Meta's latest Llama 3 instruction model."},
        {"id": "microsoft/mai-ds-r1:free",             "name": "Microsoft MAI DS R1 (free)",            "context_length": 163840,  "description": "Microsoft reasoning model."},
        {"id": "deepseek/deepseek-chat-v3-0324:free",  "name": "DeepSeek Chat V3 (free)",               "context_length": 163840,  "description": "DeepSeek V3 chat model."},
        {"id": "qwen/qwen3-235b-a22b:free",            "name": "Qwen3 235B (free)",                     "context_length": 131072,  "description": "Alibaba's large Qwen3 model."},
        {"id": "mistralai/mistral-7b-instruct:free",   "name": "Mistral 7B Instruct (free)",            "context_length": 32768,   "description": "Mistral's compact instruction model."},
    ]


def display_and_select_model() -> str:
    """
    Fetch free models, display a numbered list, and prompt the user to pick one.

    Returns:
        The selected model ID string (e.g. 'google/gemini-2.0-flash-exp:free').
    """
    models = fetch_free_models()

    if not models:
        console.print("[bold yellow]No free models found. Defaulting to gemini-2.0-flash.[/bold yellow]")
        return "google/gemini-2.0-flash-exp:free"

    table = Table(title="Available FREE Models on OpenRouter", title_style="bold magenta", show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Model Name", style="green")
    table.add_column("Context", justify="right", style="yellow")
    table.add_column("Description", style="dim")

    for i, m in enumerate(models, 1):
        ctx = f"{m['context_length'] // 1000}K" if m["context_length"] >= 1000 else str(m["context_length"])
        name = m["name"][:42]
        desc = (m.get("description") or "")[:60]
        table.add_row(str(i), name, ctx, desc)

    console.print(table)

    try:
        idx = IntPrompt.ask(
            f"\nSelect a model",
            choices=[str(i) for i in range(1, len(models) + 1)],
            default=1,
            show_choices=False
        ) - 1
    except KeyboardInterrupt:
        console.print(f"\n[bold yellow]Selection cancelled. Using default (1).[/bold yellow]")
        idx = 0

    chosen = models[idx]
    
    info_text = Text()
    info_text.append(f"Selected: ", style="bold")
    info_text.append(f"{chosen['name']}\n", style="green")
    if chosen["description"]:
        info_text.append(f"Info    : ", style="bold")
        info_text.append(f"{chosen['description']}\n", style="yellow")
    info_text.append(f"Model ID: ", style="bold")
    info_text.append(f"{chosen['id']}", style="cyan")
    
    console.print(Panel(info_text, title="Model Selection", expand=False, border_style="green"))
    
    return chosen["id"]


if __name__ == "__main__":
    # Quick standalone test
    selected = display_and_select_model()
    console.print(f"You selected: [bold green]{selected}[/bold green]")
