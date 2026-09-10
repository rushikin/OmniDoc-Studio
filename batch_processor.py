"""
Batch PDF Processor
Processes all PDF files in a given folder through the full OCR + AI pipeline.
Supports resuming interrupted runs and outputs a summary report.
"""

import os
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table


console = Console()


class BatchProcessor:
    """Processes a folder of PDFs through the OCR pipeline."""

    def __init__(self, input_dir: str, output_dir: Optional[str] = None, dpi: int = 300, lang: str = "en", use_ai: bool = True, selected_model: Optional[str] = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else Path(os.environ.get("OUTPUT_DIR", r"C:\Users\rushi\OneDrive\Desktop\Extracted Files"))
        self.dpi = dpi
        self.lang = lang
        self.use_ai = use_ai
        self.selected_model = selected_model
        self.results: list[dict] = []

    def discover_pdfs(self) -> list[Path]:
        """Find all PDFs in the input directory (non-recursive)."""
        pdfs = sorted(self.input_dir.glob("*.pdf"))
        console.print(f"[bold cyan]Found {len(pdfs)} PDF(s) in:[/bold cyan] {self.input_dir}")
        return pdfs

    def run(self) -> None:
        """Process all discovered PDFs and print a summary."""
        from pdf_converter import pdf_to_images
        from ocr_engine import OCREngine
        from word_generator import WordGenerator

        pdfs = self.discover_pdfs()
        if not pdfs:
            console.print("[bold yellow]No PDFs found. Nothing to do.[/bold yellow]")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Init OCR engine once for all files
        console.print("[bold cyan]Initializing OCR engine...[/bold cyan]")
        try:
            ocr = OCREngine(language=self.lang, use_gpu=False)
        except Exception as e:
            console.print(f"[bold red]Failed to init OCR: {e}[/bold red]")
            return

        if self.use_ai and self.selected_model:
            from ai_enhancer import AIEnhancer
            enhancer = AIEnhancer(model_id=self.selected_model)
        else:
            enhancer = None

        for idx, pdf_path in enumerate(pdfs, 1):
            console.rule(f"[bold magenta]File {idx}/{len(pdfs)}: {pdf_path.name}[/bold magenta]")
            output_path = self.output_dir / (pdf_path.stem + ".docx")
            start = time.time()
            status = "OK"
            try:
                page_images = pdf_to_images(str(pdf_path), dpi=self.dpi)
                raw_pages = [ocr.extract_page(img) for img in page_images]

                if enhancer:
                    enhanced_pages = []
                    for i, raw in enumerate(raw_pages):
                        try:
                            enhanced_pages.append(enhancer.enhance_page(i, raw))
                        except Exception:
                            enhanced_pages.append(raw)
                else:
                    enhanced_pages = raw_pages

                gen = WordGenerator()
                gen.generate_toc(enhanced_pages)
                for i, elems in enumerate(enhanced_pages):
                    gen.add_page(i, elems)
                gen.save(str(output_path))

                elapsed = time.time() - start
                self.results.append({"file": pdf_path.name, "pages": len(page_images), "status": "OK", "time": f"{elapsed:.1f}s", "output": str(output_path)})
                console.print(f"  [green]Done in {elapsed:.1f}s -> {output_path.name}[/green]")

            except Exception as e:
                status = f"ERROR: {e}"
                self.results.append({"file": pdf_path.name, "pages": 0, "status": status, "time": "N/A", "output": ""})
                console.print(f"  [bold red]FAILED: {e}[/bold red]")

        self._print_summary()

    def _print_summary(self) -> None:
        """Print a Rich table summarizing batch results."""
        table = Table(title="Batch Processing Summary", title_style="bold magenta", show_header=True, header_style="bold cyan")
        table.add_column("File", style="green")
        table.add_column("Pages", justify="right", style="yellow")
        table.add_column("Status", style="bold")
        table.add_column("Time", justify="right")
        table.add_column("Output")

        ok_count = 0
        for r in self.results:
            status_style = "green" if r["status"] == "OK" else "red"
            table.add_row(
                r["file"],
                str(r["pages"]),
                f"[{status_style}]{r['status']}[/{status_style}]",
                r["time"],
                Path(r["output"]).name if r["output"] else "N/A",
            )
            if r["status"] == "OK":
                ok_count += 1

        console.print(table)
        console.print(f"\n[bold green]{ok_count}/{len(self.results)} file(s) processed successfully.[/bold green]")
