# TradingAgents/graph/thesis_analyzer.py

import os
import json
from typing import Dict, Any, List


class ThesisAnalyzer:
    """Analyzes investment thesis documents and extracts actionable tickers."""

    def __init__(self, llm):
        self.llm = llm

    def load_document(self, file_path: str) -> str:
        """Read a thesis document from file.

        Supports .txt, .md, and .pdf files.
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self._load_pdf(file_path)
        else:
            # .txt, .md, and any other text format
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

    def _load_pdf(self, file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                "pypdf is required to read PDF files. "
                "Install it with: pip install pypdf"
            )

        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    def extract_tickers(self, document_text: str, trade_date: str) -> Dict[str, Any]:
        """Extract investment themes and candidate tickers from a thesis document.

        Args:
            document_text: The full text of the thesis document.
            trade_date: The date context for the analysis.

        Returns:
            Dict with keys:
                - thesis_summary: Condensed thesis for injection into agent prompts.
                - themes: List of dicts with theme, tickers, and rationale.
        """
        # Truncate very long documents to avoid context overflow
        max_chars = 15000
        if len(document_text) > max_chars:
            document_text = document_text[:max_chars] + "\n\n[Document truncated...]"

        prompt = f"""You are a financial analyst assistant. Read the following investment thesis document and extract:

1. A concise summary of the thesis (2-4 paragraphs) that captures the key investment themes, market views, and reasoning. This summary will be shared with other analysts to frame their research, so make it clear and actionable.

2. A list of specific investment themes mentioned or implied, along with the most relevant publicly traded stock tickers (US exchanges preferred) for each theme.

Current date for context: {trade_date}

IMPORTANT: Respond with valid JSON only, no other text. Use this exact format:
{{
    "thesis_summary": "...",
    "themes": [
        {{
            "theme": "Theme description",
            "tickers": ["TICKER1", "TICKER2"],
            "rationale": "Why these tickers relate to this theme"
        }}
    ]
}}

If the document does not contain a clear investment thesis, still extract what themes you can and provide relevant tickers. Limit to at most 5 themes and 3 tickers per theme.

---
THESIS DOCUMENT:
{document_text}
---"""

        response = self.llm.invoke(prompt)
        content = response.content.strip()

        # Parse JSON from the response, handling markdown code blocks
        if content.startswith("```"):
            # Strip markdown code fence
            lines = content.split("\n")
            content = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
            content = content.strip()

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: use the raw response as the summary with no extracted tickers
            result = {
                "thesis_summary": content,
                "themes": [],
            }

        # Ensure required keys exist
        if "thesis_summary" not in result:
            result["thesis_summary"] = ""
        if "themes" not in result:
            result["themes"] = []

        return result
