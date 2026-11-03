# Thesis-aware analysis: rebuild plan (v2, on v0.7.1)

*Status: draft for review. Branch `claude/document-agent-inputs-0lEtE`, based on upstream v0.7.1. v1 (March, on v0.2.0) is kept in this branch's history for reference only; none of its code carries over.*

## Goal

Give TradingAgents a long investment document, such as Leopold Aschenbrenner's *Situational Awareness*, and get back:

1. **A thesis brief.** The document's investable claims, its time horizon, who benefits and who loses, and the signposts that would show it is wrong.
2. **Ranked ticker ideas.** Each idea comes with the specific claim that ties it to the thesis.
3. **Full TradingAgents runs on the strongest candidates.** The thesis is a hypothesis the agents test, not a premise they adopt.
4. **A basket summary.** The ratings side by side, how concentrated the bet is, and what to watch.

## What v1 got wrong, and the guard against each

| v1 failure | v2 guard |
|---|---|
| The social and fundamentals analysts crashed whenever a thesis was supplied (`tuple += str`). Only a syntax check had been run. | Thesis text reaches prompts only through one helper and is never appended onto upstream prompt variables. A test runs every agent node with and without a thesis. Nothing is reported done without one live run. |
| Documents were cut off at 15,000 characters (about 5 pages). | A chunked digest reads the whole document. |
| The CLI put the raw document into every prompt. | Only the size-capped brief ever reaches an agent. |
| If the model wrote any prose before its JSON, the run produced zero tickers and no warning. | Upstream's structured output is used, and an extraction that comes back empty raises an error. |
| A pasted thesis longer than 255 characters crashed the CLI's "is this a file?" check. | An explicit `--thesis PATH` option. The CLI never guesses whether text is a path. |
| Model-suggested tickers were never validated. | Every candidate passes a spelling check and an as-of-date existence check before anything runs on it. |

## What v0.7.1 already provides (reuse, don't rebuild)

- **Caller-supplied context.** `portfolio_context` is the pattern thesis context will follow: a state field rendered once at run start and read through a helper in `agents/context.py`. The trader, the three risk debaters and the Portfolio Manager already read it.
- **Structured output.** `bind_structured()` and `invoke_structured()` in `agents/structured.py`, with Pydantic schemas in `agents/schemas.py` and a free-text fallback.
- **Point-in-time discipline.** `is_historical()`, dated tools that take the run date from state, and fundamentals served as filed.
- **Cheap, deterministic market data.** `build_verified_market_snapshot(symbol, as_of_date)` gives the latest prices and common indicators as of a date, with no LLM call. `get_company_profile()` adds sector, industry, market cap and P/E, but describes the company only as it is today.
- **Ticker spelling checks.** `normalize_symbol()` and `safe_ticker_component()` in `dataflows/symbols.py`, which the CLI's ticker check (#1604) wraps. They make no network call, so they can't tell whether a ticker exists. v2 adds an existence check (see Candidates).
- **Parallel analysts.** A ticker's four analysts already run in parallel, each with its own tool history, alongside a memory step.
- **Backtesting.** `run_backtest(tickers, dates, config, ..., portfolio, run_id)` runs a ticker × date grid. Its cells run one after another, and each backtest gets its own results folder and memory log. `summarize()` scores the settled decisions, and `--run-id` resumes an interrupted grid.
- **Decision memory.** A Markdown log at `memory_log_path` holds one entry per (ticker, date), with the rating and the decision text. Each entry is later settled with its realized return and a reflection, and the Portfolio Manager reads past lessons from the log. Writes are file-locked, so the log is safe across processes.
- **Reports.** `save_reports()` writes Markdown plus a self-contained HTML page from one `_SECTIONS` table in `reporting.py`, so a new report section is one row.
- **A provider per model tier.** The quick and deep tiers can run on different providers.
- **A healthy baseline.** The synced v0.7.1 suite passes here: 1,412 passed, 1 skipped (optional AWS library) and 1 deselected (opt-in live test).

## Pipeline

```
document → 1 Ingest → 2 Digest → 3 Candidates → 4 Screen → 5 Deep runs → 6 Synthesis
           text, hash,  ThesisBrief  tickers + link  cheap rank,   top K tickers,   basket
           pub. date    (cached)     (validated)     keep top K    thesis-aware     report
```

### 1. Ingest
`load_document(path)` returns `ThesisDocument(text, title, sha256, published_on)`.
- Formats: txt, md and pdf. Nothing in the project reads PDFs today, so `pypdf` becomes an optional `thesis` extra, imported lazily with an error that names `pip install "tradingagents[thesis]"`. That follows the `bedrock` extra's precedent and keeps CI's clean-install job, which imports the package without extras, passing. HTML can come later.
- `published_on` comes from the PDF metadata or a `--thesis-date` option. It is required for historical runs (see point-in-time below).

### 2. Digest (map, then reduce)
- Split the text into chunks of about 8k tokens, at headings or paragraph breaks.
- **Map**, on the quick tier with chunks processed in parallel: each chunk becomes structured `ChunkNotes` covering claims, figures, named companies and sectors, timelines and risks.
- **Reduce**, on the deep tier: all the notes become one `ThesisBrief` with:
  - `summary` (200 words at most)
  - `horizon`
  - `claims` (each with the statement, the document's evidence and a confidence level)
  - `themes` (each with a mechanism, direct and second-order beneficiaries, and losers)
  - `signposts` (observable events that would confirm or refute the thesis)
  - `falsifiers`
- The prompts tell the model to use only what the document says. That keeps outside, later knowledge out of historical runs.
- The brief is cached on disk, keyed by document hash, model and prompt version. Later runs on new dates reuse it at no cost.
- The rendered brief has a hard token cap (default 1,200 tokens), so prompt cost does not grow with document length.

### 3. Candidates
- **Generation** on the deep tier, as a structured `CandidateList`. Each ticker gets its theme, its specific linkage claim, an exposure type (pure play, diversified, second-order or loser) and the evidence that would confirm the link.
- The prompt asks explicitly for second-order beneficiaries and losers, not only the famous names.
- **Validation** in two steps:
  - Spelling, through `safe_ticker_component(normalize_symbol(t))`.
  - Existence as of the run date. A ticker with no price rows on or before that date in the verified market snapshot is dropped, which also catches companies that listed later. The same fetch feeds the screen, so the check costs nothing extra.

  Each dropped ticker is reported with its reason, duplicates are removed, and the list is capped at N (default 20).
- Tickers you supply yourself skip generation, but still get a linkage claim written for them.

### 4. Screen (new, and the main cost saver)
- Gather cheap facts per candidate from the deterministic snapshot and, for live runs only, the company profile. Historical runs get no present-day profile, matching upstream.
- One quick-tier structured call scores every candidate on four things: how pure its exposure is, how strong its link is, how much is already priced in, and liquidity. The candidates are ranked and the top K are kept (default 5).
- The CLI shows the scored table, and you can change the selection before the expensive runs start.

### 5. Deep runs
- Each selected ticker runs `propagate(ticker, date, thesis=ThesisInput(brief, link))`, mirroring `portfolio=`.
- If you pass a portfolio, every run gets it, so sizing reflects what you already hold.
- Runs proceed concurrently where it is safe to (see "Speed and cost design").
- Each role receives its own thesis block (see "Decision-quality design").

### 6. Synthesis
- One deep-tier call compares the K decisions. It flags concentration (a basket of AI names is really one bet), notes overlap with `portfolio_context`, and lists the signposts to watch.
- Output: a batch report in Markdown and HTML, plus each ticker's normal report with a Thesis section added.

## Plumbing into the graph

- **One way in.** The CLI never calls `propagate()`. It builds its state with `TradingAgentsGraph.create_run_state()`. `propagate()` and `run_backtest()` end up there too, and it is where the portfolio is rendered. The thesis is threaded through that same function as a `thesis=` argument, so every entry point gets it. `run_backtest()` also takes `thesis=`, which the A/B evaluation needs.
- **`agents/state.py`** gains two fields, both empty when there is no thesis:
  - `thesis_brief`, the rendered brief, identical for every ticker in a batch;
  - `thesis_link`, this ticker's linkage claim.
- **`agents/context.py`** gains `get_thesis_context_from_state(state, role)`. It returns that role's block, or `""` when there is no thesis, so a run without one sends exactly v0.7.1's prompts. A test checks this.
  - This differs from `get_portfolio_context_from_state`, which returns a "not provided" notice when there is no portfolio. A missing portfolio is information the agents need to hear about. No thesis is the normal case, so thesis context says nothing.
- **Checkpoints know about the thesis.** Upstream folds a portfolio `fingerprint()` into the run signature, so a changed book counts as a different run. The thesis brief gets the same treatment. Otherwise a resumed run could carry reports built from an older brief.
- **The digester's models come from `create_tier_client()`,** created in `TradingAgentsGraph.__init__` the way the Reflector's is. That keeps the end-to-end tests' single patch point covering them. Thesis code that runs outside the graph wraps itself in `with run_config(self.config):`, as `settle_pending` does.
- **Templates and braces.** Analyst prompts are `ChatPromptTemplate`s, so the thesis text goes in as a partial variable and is never spliced into the template string. Documents contain `{` and `}`.
- **Structured prompts follow upstream's rules,** and convention tests enforce all three:
  - each schema gets a `render_*` function;
  - prompts include `NO_EXTERNAL_TOOLS`;
  - any agent whose output reaches the report calls `get_language_instruction()`.
- **The memory log needs no format change.** It stores the rendered Portfolio Manager decision, so the thesis-alignment fields and signposts travel inside the decision text.
- **Thesis runs get their own results folder and memory log** (`memory/thesis-<hash>.md`), as `run_backtest()` runs do. This does two things:
  - Experiments don't feed lessons into your normal runs.
  - It avoids a real collision. The log keeps only the first decision per ticker and date, and the state JSON is overwritten, so a thesis run on a ticker you had already analyzed that day would otherwise be silently dropped.

  A `thesis_memory_log` option can point live thesis runs at the main log instead.
- **The Portfolio Manager's output.** When a thesis is present, it binds a `ThesisPortfolioDecision` subclass that adds `thesis_alignment` (supports, contradicts or unrelated), `priced_in` and `signposts_to_watch`. Runs without a thesis keep today's `PortfolioDecision` unchanged.
- **Reports.** The brief and this ticker's link become one new `_SECTIONS` row, saved in a `0_thesis` folder so the existing numbered sections, and the tests that reference them, don't change. The CLI's live view lists its sections separately and needs a matching edit. `_log_state` gets the new keys.

## Decision-quality design

Giving the thesis to every agent risks confirmation bias: told the thesis, the agents argue for it. v2 treats the thesis as a hypothesis to test, and keeps the evidence-gathering agents mostly independent of it. Upstream already makes a call like this: the research team never sees the caller's portfolio, so holdings can't anchor the debate, and a test enforces it. v2 adds a similar test for the agents that stay thesis-blind.

| Agent | Thesis input | Why |
|---|---|---|
| Market (technical) analyst | none (decided) | Price action stays independent evidence. |
| Sentiment analyst | none (decided) | Same reason. |
| News analyst | signposts only | Points its searches at the thesis's catalysts; it reports what it finds. |
| Fundamentals analyst | this ticker's linkage claim | Checks the specific claim (for example, data-center revenue share) against the filings. |
| Bull researcher | brief + link | Makes the thesis case. |
| Bear researcher | brief + link, with a mandate to attack the link and the "priced in" question | The counterweight. |
| Research Manager | brief + link | Must say whether the link holds and whether it is already priced in. |
| Trader | link + horizon | The horizon shapes entry and sizing. |
| Aggressive and Neutral debaters | link | |
| Conservative debater | link + falsifiers | Argues from what would break the thesis. |
| Portfolio Manager | brief + link + falsifiers | Produces the structured thesis-alignment fields. |

Other quality changes:
- **A linkage claim per ticker, instead of one vague thesis for all.** Agents test something concrete, such as "this utility benefits because data-center load raises power prices in its market", rather than "AI is big".
- **Exposure purity in the screen**, so diluted mega-caps don't crowd out pure plays.
- **A priced-in check.** The Research Manager and Portfolio Manager compare current valuation with what the thesis implies.
- **Losers as well as winners.** The digest and the candidate list both name who the thesis hurts, which yields avoid and underweight ideas.
- **Signposts in memory.** Decisions record their signposts, so a later run can see whether one has fired.
- **Point-in-time honesty.** A run dated before the document's publication date is refused. In historical runs, LLM-generated candidates carry hindsight (the model knows what went up), so backtests use a frozen candidate list or tickers you supply, and the report says which.
- **Measure, don't assume.** An A/B backtest runs the same tickers and dates with and without the thesis through `run_backtest`, so we can see whether the thesis actually improves decisions.

## Speed and cost design

Ranked by expected impact:

1. **Screen before deep analysis.** A deep run makes about 20–30 LLM calls per ticker: at least 15, and up to about 76 if every analyst uses all its tool rounds. Screening 20 candidates costs about one call plus data lookups, so deep-running 5 instead of 20 removes about three quarters of the cost.
2. **Digest once.** The document is read once and cached, so later runs on other dates skip it. For a book-length document that is roughly 10–20 quick-tier calls, run in parallel, plus one deep-tier call, paid once.
3. **A capped brief, and only for the roles that need it.** Analysts get the least, because their tool loops resend the system prompt on every tool round.
4. **Concurrent tickers.** A ticker's analysts already run in parallel, but `run_backtest()` and any loop over tickers run one ticker at a time. v2 runs the K deep runs in separate worker processes, capped at 2 by default.
   - **One graph per worker,** each built from a `copy.deepcopy` of the config. Building a graph mutates process-wide config, and shallow copies share nested dicts.
   - **Processes, not threads on a shared graph.** Two concurrent runs on one graph instance clobber each other when checkpointing is on. The memory-log locks and the caches' atomic writes already work across processes.
   - **Tickers normalized and deduplicated before dispatch,** because `propagate()` doesn't normalize them.
   - **A low worker cap,** because each run already fans out five ways (four analysts plus the memory step), and Yahoo and Reddit back off under load.
5. **Shared per-date data.** Today only price history and SEC filings are cached. Global news (up to five searches per call), FRED macro series and prediction-market odds don't depend on the ticker, yet every ticker's News Analyst fetches them again. v2 adds a batch-scoped cache for these date-scoped tools, keyed by tool, arguments and run date.
   - With worker processes it lives on disk, using the OHLCV cache's atomic-rename pattern.
   - It touches `dataflows/`, so it belongs to Phase 3 and gets measured.
6. **Prompt order that suits provider caching.** Nothing in the project uses prompt caching today. With the role table, thesis text reaches 13–17 of a ticker's 20–30 calls, 4 of them with the full brief, and every one of those is paid for in full.
   - OpenAI and Gemini cache repeated prompt prefixes automatically. Putting static instructions and the brief ahead of per-ticker content would pay off there with no client changes.
   - Anthropic caches only prefixes marked with cache breakpoints, which here would first mean rebuilding prompts as content blocks.
   - Either way, this reorders every agent's prompt, so it lands as its own measured change. Each provider's current caching rules should be confirmed when it is built.
7. **Resumable batches.** A manifest per thesis run lets a rerun skip finished tickers, on top of per-ticker checkpoints.

## Interfaces

### Python
```python
from tradingagents.thesis import analyze_thesis

result = analyze_thesis(
    "situational-awareness.pdf",
    trade_date="2026-11-03",
    top_k=5,
    config=config,
)
result.brief          # ThesisBrief
result.candidates     # validated, screened and ranked
result.runs["VST"]    # (final_state, rating) for each ticker that got a deep run
result.save("reports/situational-awareness/")
```
`propagate(ticker, date, thesis=...)` remains available for a single ticker.

### CLI
This mirrors `--portfolio`, which is a flag on the bare `tradingagents` command and on `tradingagents backtest`. The file is loaded before the run starts, and a bad file is reported in red with exit code 1.
- `tradingagents --thesis PATH [--thesis-date YYYY-MM-DD] [--top-k 5] [--tickers A,B,C]`. Passing `--tickers` skips generation and uses your list.
- **At a terminal**, once the brief is built, the CLI shows the scored candidate table and lets you change the selection before the deep runs start. That is the only new interactive step.
- **Headless runs** (no terminal) take the top K without asking. The thesis flags are added to upstream's missing-flag check, so a headless run names anything it lacks before it calls a model.
- `tradingagents backtest TICKERS --thesis PATH` runs the A/B evaluation.

### Config
New keys in `build_default_config()`: `thesis_top_k`, `thesis_max_candidates`, `thesis_max_workers`, `thesis_chunk_tokens`, `thesis_brief_max_tokens` and `thesis_cache_dir`. Each gets a `TRADINGAGENTS_THESIS_*` row in `_ENV_OVERRIDES` and a line in `.env.example`. Config keys are hashed into the checkpoint signature by default. `thesis_max_workers` and `thesis_cache_dir` don't change a run's result, so they go in `_NOT_IN_SIGNATURE`.

## Testing

Upstream's conventions apply:
- tests marked `@pytest.mark.unit`;
- a conftest that blocks the network and supplies placeholder API keys;
- `pytest -q` (CI runs it on Python 3.11–3.14) and `ruff check .`.

What gets tested:
- **Ingest:** txt, md and pdf; chunk boundaries; a stable document hash.
- **Digest and candidates.** These run against upstream's `ScriptedModel`, with the new schemas added to its `STRUCTURED` table. A schema missing from that table silently takes the free-text fallback, so a test asserts the typed path was used. An empty extraction raises.
- **Every agent node, with and without a thesis.**
  - No crashes.
  - Thesis text appears only where the role table says it should.
  - Prompts without a thesis are byte-identical to v0.7.1's.
  - The thesis-blind agents get an enforcement test like upstream's portfolio one.
- **Guards and recovery:** the point-in-time guard, candidate validation, the checkpoint signature and the resume manifest.
- **Upstream's convention tests stay green:**
  - translated-output coverage;
  - layering (only `dataflows/` may import yfinance, so the screen goes through the data layer);
  - prompt integrity.
- **One live test,** marked `integration` so it runs only with `pytest -m integration`, on a short document.

## Keeping future upstream syncs easy

Upstream shipped 426 commits in eight months, and this fork will want to keep taking them. The feature should leave as little as possible in files upstream owns:
- **New code goes in a new package,** `tradingagents/thesis/` (ingest, digest, candidates, screen, run, render), with its own tests under `tests/thesis/`.
- **Upstream files get small, mechanical edits only:**
  - two state fields;
  - a `thesis=` argument threaded through `create_run_state()`, `propagate()` and `run_backtest()`;
  - the thesis fingerprint in the run signature;
  - one helper in `context.py`, plus one call to it per agent prompt;
  - the Portfolio Manager's schema switch;
  - one report row;
  - the CLI flags and the new config keys.
- **Nothing is reformatted or reordered** in upstream files as part of this feature. The prompt-order change for caching is the exception, so it stays separate and optional.
- **The design follows upstream's own patterns** (`portfolio_context`, structured output, point-in-time guards), which would also let us offer it upstream as a pull request later.

## Risks

- **Prompt edits shift upstream's tuned behavior.** Mitigation: no prompt changes without a thesis (a byte-identical test guards this), and the A/B backtest measures the effect when there is one.
- **Structured-output support varies by provider and model.** Mitigation: use upstream's fallback path, and fail loudly when the digest or candidate list cannot be read.
- **Rate limits.** Concurrency multiplies LLM and data-vendor calls. Mitigation: a worker cap (default 2) plus the vendors' existing retry logic.
- **Cost overruns on long documents.** Mitigation: a cached digest, a token cap on the brief, and the screen in front of the deep runs. The CLI shows the expected number of deep runs before it starts them.

## Phases

1. **Foundation.** Ingest, digest and cache, state and context plumbing, the role table, schemas and tests. Done when `propagate(ticker, date, thesis=...)` works with a real model.
2. **Ideas.** Candidates, validation, the screen, a sequential `analyze_thesis()` and the batch report.
3. **Speed.** Concurrent tickers, shared per-date data, prompt order for caching, and resume.
4. **CLI and evaluation.** CLI flags and steps, and the A/B backtest.

## Open questions

1. Which provider(s) will you run? That decides the caching approach and how far we can rely on structured output.
2. Do you have a cost or time budget per thesis run? It sets the defaults for N and K.
3. ~~Should the market and sentiment analysts stay thesis-blind?~~ **Decided: yes.** They see no thesis input, and a test enforces it.
4. Should the output include losers and underweight ideas?
5. Will you backtest thesis runs? If so, the point-in-time work moves into Phase 1.
