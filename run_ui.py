"""
OmniDoc Studio — Native Webview App Launcher
Runs the ultra-responsive modern HTML5/Tailwind/Material workstation UI
powered by the underlying Stirling + PaddleOCR + OpenRouter Python engines.

Usage:
  python run_ui.py
"""

import os
import sys
from pathlib import Path

try:
    import webview
except ImportError:
    print("pywebview is required to run the native window.")
    print("Run: pip install pywebview")
    sys.exit(1)


def main():
    ui_dir = Path(__file__).parent / "ui"
    index_file = ui_dir / "index.html"

    if not index_file.exists():
        print(f"ERROR: UI index file not found at: {index_file}")
        sys.exit(1)

    window = webview.create_window(
        title="OmniDoc Studio — v2.4 Enterprise Workstation",
        url=str(index_file.resolve()),
        width=1380,
        height=860,
        min_size=(960, 640),
        resizable=True,
    )

    webview.start(debug=False)


if __name__ == "__main__":
    main()
