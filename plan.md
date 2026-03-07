# Plan: Thesis-Aware Analysis — Document-Driven Trading Agent Pipeline

## Overview

Add a new pre-processing stage that accepts a document (file path or raw text) as an "investment thesis," extracts ticker ideas from it, and injects the thesis context into every agent's prompt so all analysis is grounded in the thesis — not just raw financial data.

Two new capabilities:
1. **Thesis → Ticker extraction**: An LLM reads the document and proposes tickers to analyze
2. **Thesis-aware agent prompts**: Every agent in the pipeline sees the thesis context, allowing it to reason about the stock *in light of* the thesis

---

## Step 1: Add `thesis_context` field to `AgentState`

**File:** `tradingagents/agents/utils/agent_states.py`

Add one new field to the `AgentState` TypedDict:

```python
thesis_context: Annotated[str, "Investment thesis document context provided by the user"]
```

This is the minimal state change — all agents already receive `state`, so they can now optionally read `state["thesis_context"]`.

---

## Step 2: Update `Propagator.create_initial_state()` to accept thesis context

**File:** `tradingagents/graph/propagation.py`

- Add an optional `thesis_context: str = ""` parameter to `create_initial_state()`
- Include it in the returned state dict: `"thesis_context": thesis_context`

---

## Step 3: Update `TradingAgentsGraph.propagate()` to accept thesis context

**File:** `tradingagents/graph/trading_graph.py`

- Add `thesis_context: str = ""` parameter to `propagate()`
- Pass it through to `self.propagator.create_initial_state(company_name, trade_date, thesis_context)`
- Fully backward-compatible: defaults to empty string, existing callers unaffected

---

## Step 4: Add a new `ThesisAnalyzer` class for document ingestion + ticker extraction

**New file:** `tradingagents/graph/thesis_analyzer.py`

This class handles:
1. **Reading a document** from a file path (`.txt`, `.md`, `.pdf`) or accepting raw text
2. **Extracting investment themes** via an LLM call
3. **Generating candidate tickers** for each theme via an LLM call
4. **Returning** a list of `(ticker, theme_summary)` tuples plus the full thesis text

```python
class ThesisAnalyzer:
    def __init__(self, llm):
        self.llm = llm

    def load_document(self, file_path: str) -> str:
        """Read document from file. Supports .txt, .md, .pdf"""

    def extract_tickers(self, document_text: str, trade_date: str) -> dict:
        """Returns {
            "thesis_summary": str,       # Condensed thesis for injection into prompts
            "themes": [                   # Extracted themes
                {
                    "theme": str,
                    "tickers": [str],
                    "rationale": str
                }
            ]
        }"""
```

For PDF support, use `pypdf` (lightweight, already common). For `.txt`/`.md`, just read the file. If the document is very long, chunk it and summarize before ticker extraction.

---

## Step 5: Add `propagate_from_thesis()` method to `TradingAgentsGraph`

**File:** `tradingagents/graph/trading_graph.py`

A new convenience method that orchestrates the full thesis-aware flow:

```python
def propagate_from_thesis(self, thesis_file_or_text: str, trade_date: str, tickers: list[str] | None = None):
    """Run thesis-aware analysis.

    If tickers is None, extract them from the thesis document.
    Returns dict mapping ticker -> (final_state, decision).
    """
    analyzer = ThesisAnalyzer(self.quick_thinking_llm)

    # Load document
    if os.path.isfile(thesis_file_or_text):
        doc_text = analyzer.load_document(thesis_file_or_text)
    else:
        doc_text = thesis_file_or_text

    # Extract tickers if not provided
    extraction = analyzer.extract_tickers(doc_text, trade_date)
    thesis_summary = extraction["thesis_summary"]

    if tickers is None:
        tickers = []
        for theme in extraction["themes"]:
            tickers.extend(theme["tickers"])
        tickers = list(dict.fromkeys(tickers))  # deduplicate, preserve order

    # Run per-ticker analysis with thesis context
    results = {}
    for ticker in tickers:
        final_state, decision = self.propagate(ticker, trade_date, thesis_context=thesis_summary)
        results[ticker] = (final_state, decision)

    return results
```

---

## Step 6: Inject thesis context into all 12 agent prompts

For each agent, add a conditional thesis block to the prompt. When `thesis_context` is empty (standard mode), nothing changes. When populated, agents see it as additional context.

The thesis block to inject (adapted per agent role):

```
Investment Thesis Context: The following thesis document has been provided to frame this analysis. Consider how this company relates to the themes described:
{thesis_context}
```

### Files to modify (12 agents total):

**Analysts (4)** — add thesis to system message:
- `tradingagents/agents/analysts/market_analyst.py` — append to system prompt partial, read from `state["thesis_context"]`
- `tradingagents/agents/analysts/social_media_analyst.py` — same pattern
- `tradingagents/agents/analysts/news_analyst.py` — same pattern
- `tradingagents/agents/analysts/fundamentals_analyst.py` — same pattern

For these 4 analysts, the change is: read `thesis_context = state.get("thesis_context", "")` and if non-empty, append to the system message:
```
\n\nInvestment Thesis Context: The following investment thesis has been provided to frame your analysis. Consider how {ticker} relates to the themes described:\n{thesis_context}
```

**Researchers (2)** — add thesis to f-string prompt:
- `tradingagents/agents/researchers/bull_researcher.py` — add `Investment thesis context: {thesis_context}` to the resources section
- `tradingagents/agents/researchers/bear_researcher.py` — same pattern

**Research Manager (1)**:
- `tradingagents/agents/managers/research_manager.py` — add thesis context to prompt

**Trader (1)**:
- `tradingagents/agents/trader/trader.py` — add thesis context to system message

**Risk Debaters (3)**:
- `tradingagents/agents/risk_mgmt/aggressive_debator.py` — add thesis context to prompt
- `tradingagents/agents/risk_mgmt/conservative_debator.py` — same
- `tradingagents/agents/risk_mgmt/neutral_debator.py` — same

**Risk Manager (1)**:
- `tradingagents/agents/managers/risk_manager.py` — add thesis context to prompt

### Pattern for injection

All agents follow one of two patterns:

**Pattern A (ChatPromptTemplate analysts):** Read `state["thesis_context"]`, build a conditional string, add as a new partial variable:
```python
thesis_context = state.get("thesis_context", "")
thesis_block = ""
if thesis_context:
    thesis_block = f"\n\nInvestment Thesis Context: The following investment thesis has been provided to frame your analysis. Consider how {ticker} relates to the themes described:\n{thesis_context}"
# ... append thesis_block to system_message or add as separate partial
```

**Pattern B (f-string prompt agents):** Add a conditional section:
```python
thesis_context = state.get("thesis_context", "")
thesis_section = ""
if thesis_context:
    thesis_section = f"Investment thesis context framing this analysis: {thesis_context}"
# ... include thesis_section in the f-string prompt
```

---

## Step 7: Update `_log_state()` to include thesis context

**File:** `tradingagents/graph/trading_graph.py`

Add `"thesis_context"` to the logged state dict so analysis results are traceable back to the thesis.

---

## Step 8: Add CLI support for thesis file input

**File:** `cli/main.py` and `cli/utils.py`

Add an optional step before ticker input:
- Ask user: "Would you like to provide an investment thesis document?"
- If yes, prompt for file path
- Extract tickers from thesis (show them to user for confirmation)
- Run thesis-aware analysis loop

This step is optional — if skipped, the CLI works exactly as before.

---

## Summary of files changed

| File | Change |
|------|--------|
| `tradingagents/agents/utils/agent_states.py` | Add `thesis_context` field |
| `tradingagents/graph/propagation.py` | Accept `thesis_context` param |
| `tradingagents/graph/trading_graph.py` | Accept `thesis_context` in `propagate()`, add `propagate_from_thesis()`, update logging |
| `tradingagents/graph/thesis_analyzer.py` | **New file** — document loading + ticker extraction |
| `tradingagents/agents/analysts/market_analyst.py` | Inject thesis into prompt |
| `tradingagents/agents/analysts/social_media_analyst.py` | Inject thesis into prompt |
| `tradingagents/agents/analysts/news_analyst.py` | Inject thesis into prompt |
| `tradingagents/agents/analysts/fundamentals_analyst.py` | Inject thesis into prompt |
| `tradingagents/agents/researchers/bull_researcher.py` | Inject thesis into prompt |
| `tradingagents/agents/researchers/bear_researcher.py` | Inject thesis into prompt |
| `tradingagents/agents/managers/research_manager.py` | Inject thesis into prompt |
| `tradingagents/agents/trader/trader.py` | Inject thesis into prompt |
| `tradingagents/agents/risk_mgmt/aggressive_debator.py` | Inject thesis into prompt |
| `tradingagents/agents/risk_mgmt/conservative_debator.py` | Inject thesis into prompt |
| `tradingagents/agents/risk_mgmt/neutral_debator.py` | Inject thesis into prompt |
| `tradingagents/agents/managers/risk_manager.py` | Inject thesis into prompt |
| `cli/main.py` | Optional thesis file input step |
| `cli/utils.py` | Thesis file prompt helper |

**New files:** 1 (`thesis_analyzer.py`)
**Modified files:** 17
**Backward compatibility:** Full — all changes are additive with empty-string defaults
