"""
Main CLI Entry Point
Orchestrates the full pipeline:
  0. Interactive FREE model selection from OpenRouter (live fetch)
  1. PDF -> Images (pdf_converter)
  2. Images -> Raw OCR Elements (ocr_engine)
  3. Raw Elements -> AI-Enhanced Elements (ai_enhancer)
  4. Enhanced Elements -> Word Document (word_generator)

Usage (CLI):
  OmniDocStudio.exe --input "scan.pdf"
  OmniDocStudio.exe --input "scan.pdf" --output "output/result.docx"
  OmniDocStudio.exe --input "scan.pdf" --no-ai

Usage (double-click):
  Just run the exe — it will prompt you for the PDF path interactively.
"""

import argparse
import os
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.text import Text
from rich.rule import Rule

from dotenv import load_dotenv
load_dotenv()

from pdf_converter import pdf_to_images
from ocr_engine import OCREngine
from word_generator import WordGenerator
import sys
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(highlight=False)


def print_banner():
    console.print()
    console.print(Rule("[bold cyan]OmniDoc Studio -- Scanned PDF -> Word Extractor[/bold cyan]"))
    console.print()


def interactive_mode() -> argparse.Namespace:
    """
    Interactive prompt mode — activated when the user double-clicks the exe
    with no command-line arguments. Offers to launch Desktop GUI, Modern Workstation, or CLI.
    """
    console.print(Panel(
        "[bold cyan]OmniDoc Studio — v2.4 Enterprise Workstation[/bold cyan]\n\n"
        "[1] Launch Desktop GUI (CustomTkinter Multi-Tool Suite)\n"
        "[2] Launch Modern Workstation UI (Full Micro-Animations & Stirling Tools)\n"
        "[3] Run in Terminal / CLI Mode (Process PDF directly here)",
        title="[bold]Welcome[/bold]",
        border_style="cyan",
        expand=False,
    ))
    console.print()

    choice = Prompt.ask("[bold cyan]Select launch mode (1, 2, or 3)[/bold cyan]", choices=["1", "2", "3"], default="1")

    if choice == "1":
        try:
            import gui_app
            app = gui_app.App()
            app.mainloop()
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Failed to launch CustomTkinter GUI: {e}[/bold red]")
            console.print("[dim]Falling back to terminal mode...[/dim]")
    elif choice == "2":
        try:
            import run_ui
            run_ui.main()
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]Failed to launch Modern Workstation: {e}[/bold red]")
            console.print("[dim]Falling back to terminal mode...[/dim]")

    # -- Ask for PDF path -----------------------------------------------
    while True:
        raw_path = Prompt.ask("[bold cyan]Enter path to PDF file[/bold cyan]").strip().strip('"').strip("'")
        if os.path.isfile(raw_path) and raw_path.lower().endswith(".pdf"):
            break
        elif os.path.isfile(raw_path):
            console.print("[bold red]  ✗ That file does not appear to be a PDF.[/bold red]")
        else:
            console.print("[bold red]  ✗ File not found. Please check the path and try again.[/bold red]")

    # -- Ask for optional output path -----------------------------------
    target_dir = Path(os.environ.get("OUTPUT_DIR", r"C:\Users\rushi\OneDrive\Desktop\Extracted Files"))
    target_dir.mkdir(parents=True, exist_ok=True)
    default_out = str(target_dir / (Path(raw_path).stem + ".docx"))
    console.print(f"\n[dim]Default output: {default_out}[/dim]")
    custom_out = Prompt.ask("[bold cyan]Output .docx path[/bold cyan] (press Enter for default)", default="").strip().strip('"').strip("'")
    output_path = custom_out if custom_out else None

    # -- Ask for AI toggle ----------------------------------------------
    use_ai = Confirm.ask("\n[bold cyan]Use AI enhancement?[/bold cyan]", default=True)

    # Build a fake namespace identical to what argparse would produce
    ns = argparse.Namespace(
        input=raw_path,
        output=output_path,
        dpi=300,
        lang="en",
        no_ai=not use_ai,
        save_images=False,
        interactive=True,
    )
    return ns


def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments. If no arguments are provided (double-click),
    launch the modern graphical workstation directly.
    """
    # Double-click or run without arguments: launch Modern Workstation UI directly
    if len(sys.argv) == 1:
        import run_ui
        run_ui.main()
        sys.exit(0)

    parser = argparse.ArgumentParser(
        description="OmniDoc Studio with AI gap-filling via OpenRouter",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--input", "-i", default=None, help="Path to input scanned PDF.")
    parser.add_argument("--output", "-o", default=None, help="Path for output .docx file.")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for PDF rendering. (default: 300)")
    parser.add_argument("--lang", default="en", help="OCR language code. (default: en)")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI enhancement.")
    parser.add_argument("--save-images", action="store_true", help="Save page images for debugging.")
    parser.add_argument("--batch", "-b", default=None, help="Path to folder: process all PDFs inside.")
    parser.add_argument("--gui", action="store_true", help="Launch CustomTkinter Desktop GUI.")
    parser.add_argument("--ui", action="store_true", help="Launch Modern Workstation UI.")
    parser.add_argument("--cli", action="store_true", help="Launch interactive CLI mode.")
    args = parser.parse_args()

    if args.gui:
        import gui_app
        app = gui_app.App()
        app.mainloop()
        sys.exit(0)

    if args.ui:
        import run_ui
        run_ui.main()
        sys.exit(0)

    if args.cli:
        return interactive_mode()

    if not args.input and not args.batch:
        import run_ui
        run_ui.main()
        sys.exit(0)

    args.interactive = False
    return args


def resolve_output_path(input_path: str, output_arg: str | None) -> str:
    if output_arg:
        return output_arg
    pdf_name = Path(input_path).stem
    # Place output in the specified extracted files folder
    target_dir = Path(os.environ.get("OUTPUT_DIR", r"C:\Users\rushi\OneDrive\Desktop\Extracted Files"))
    target_dir.mkdir(parents=True, exist_ok=True)
    return str(target_dir / f"{pdf_name}.docx")


def run_pipeline(args, selected_model: str | None):
    """Main orchestration function."""
    start_time = time.time()

    # -- Validate input -------------------------------------------------
    if not os.path.exists(args.input):
        console.print(f"[bold red]ERROR: Input file not found:[/bold red] {args.input}")
        _pause_if_interactive(args)
        sys.exit(1)

    output_path = resolve_output_path(args.input, args.output)
    # Make sure the output directory exists
    os.makedirs(Path(output_path).parent, exist_ok=True)

    image_output_dir = None
    if getattr(args, "save_images", False):
        image_output_dir = str(Path(output_path).parent / "ocr_images")
        os.makedirs(image_output_dir, exist_ok=True)

    settings_text = (
        f"[bold]Input:[/bold]    {args.input}\n"
        f"[bold]Output:[/bold]   {output_path}\n"
        f"[bold]DPI:[/bold]      {args.dpi}\n"
        f"[bold]Language:[/bold] {args.lang}\n"
    )
    if args.no_ai:
        settings_text += "[bold]AI Mode:[/bold]  [yellow]DISABLED[/yellow]"
    else:
        settings_text += "[bold]AI Mode:[/bold]  [green]ENABLED[/green]\n"
        settings_text += f"[bold]AI Model:[/bold] {selected_model}"

    console.print(Panel(settings_text, title="Configuration", border_style="blue", expand=False))

    # -- Phase 1: PDF -> Images -----------------------------------------
    console.print("\n[bold magenta]Phase 1/4:[/bold magenta] Converting PDF pages to images...")
    try:
        with console.status("[bold cyan]Converting PDF...", spinner="dots"):
            page_images = pdf_to_images(
                pdf_path=args.input,
                dpi=args.dpi,
                output_folder=image_output_dir,
            )
    except Exception as e:
        console.print(f"[bold red]ERROR in PDF conversion:[/bold red] {e}")
        console.print("[yellow]Make sure Poppler is installed and on your PATH.[/yellow]")
        _pause_if_interactive(args)
        sys.exit(1)

    total_pages = len(page_images)
    console.print(f"  [green]✓ {total_pages} page(s) converted.[/green]")

    # -- Phase 2: OCR Init ----------------------------------------------
    console.print("\n[bold magenta]Phase 2/4:[/bold magenta] Initializing OCR Engine (PaddleOCR)...")
    try:
        with console.status("[bold cyan]Loading OCR models...", spinner="dots"):
            ocr = OCREngine(language=args.lang, use_gpu=False)
        console.print("  [green]✓ Engine initialized.[/green]")
    except Exception as e:
        console.print(f"[bold red]ERROR initializing OCR:[/bold red] {e}")
        _pause_if_interactive(args)
        sys.exit(1)

    # -- Phase 3: OCR Extraction ----------------------------------------
    raw_pages = []
    console.print("\n[bold magenta]Phase 3/4:[/bold magenta] Extracting text from each page...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]OCR Progress...", total=total_pages)
        for i, img in enumerate(page_images):
            try:
                elements = ocr.extract_page(img)
            except Exception as e:
                elements = []
                progress.console.print(f"    [red]Page {i + 1}: OCR error – {e}[/red]")
            raw_pages.append(elements)
            progress.console.print(f"    Page {i + 1}: {len(elements)} block(s) found.")
            progress.advance(task)

    # -- Phase 3b: AI Enhancement ---------------------------------------
    if args.no_ai:
        enhanced_pages = raw_pages
        console.print("\n[bold yellow]Phase 3b/4: AI Enhancement SKIPPED.[/bold yellow]")
    else:
        console.print("\n[bold magenta]Phase 3b/4:[/bold magenta] Enhancing pages with AI (OpenRouter)...")
        try:
            from ai_enhancer import AIEnhancer
            enhancer = AIEnhancer(model_id=selected_model)
            enhanced_pages = []
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]AI Enhancement...", total=total_pages)
                for i, raw_elements in enumerate(raw_pages):
                    try:
                        enhanced = enhancer.enhance_page(i, raw_elements)
                    except Exception as e:
                        enhanced = raw_elements
                        progress.console.print(f"    [yellow]Page {i + 1}: AI error, using raw – {e}[/yellow]")
                    enhanced_pages.append(enhanced)
                    progress.advance(task)
        except Exception as e:
            console.print(f"\n  [bold red]WARNING: AI enhancer failed: {e}[/bold red]")
            console.print("  [yellow]Falling back to raw OCR output.[/yellow]")
            enhanced_pages = raw_pages

    # -- Phase 4: Word Document Generation ------------------------------
    console.print("\n[bold magenta]Phase 4/4:[/bold magenta] Building Word document...")
    try:
        with console.status("[bold cyan]Generating .docx...", spinner="dots"):
            generator = WordGenerator()
            # Generate Table of Contents if multiple titles found
            generator.generate_toc(enhanced_pages)
            for page_idx, elements in enumerate(enhanced_pages):
                generator.add_page(page_idx, elements)
            generator.save(output_path)
        console.print("  [green]✓ Document saved.[/green]")
    except Exception as e:
        console.print(f"[bold red]ERROR saving document:[/bold red] {e}")
        _pause_if_interactive(args)
        sys.exit(1)

    elapsed = time.time() - start_time
    abs_out = os.path.abspath(output_path)
    summary_text = (
        f"Processed [bold]{total_pages}[/bold] page(s) in [bold]{elapsed:.1f}s[/bold]\n"
        f"Output: [bold green]{abs_out}[/bold green]"
    )
    console.print()
    console.print(Panel(summary_text, title="[bold green]✓ Completed[/bold green]", border_style="green", expand=False))

    _pause_if_interactive(args)


def _pause_if_interactive(args):
    """If the user double-clicked the exe, hold the terminal open so they can read the output."""
    if getattr(args, "interactive", False):
        console.print()
        input("  Press Enter to exit...")


if __name__ == "__main__":
    args = parse_args()
    print_banner()

    # -- Step 0: Model selection ----------------------------------------
    selected_model = None
    if not args.no_ai:
        console.print(Panel(
            "[bold cyan]Step 1 of 2: Select Your AI Model[/bold cyan]",
            border_style="cyan",
            expand=False,
        ))
        selected_model = display_and_select_model()

    if getattr(args, "batch", None):
        from batch_processor import BatchProcessor
        bp = BatchProcessor(
            input_dir=args.batch,
            output_dir=args.output,
            dpi=args.dpi,
            lang=args.lang,
            use_ai=not args.no_ai,
            selected_model=selected_model,
        )
        bp.run()
        _pause_if_interactive(args)
        sys.exit(0)

    run_pipeline(args, selected_model)
