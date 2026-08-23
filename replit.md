# Market Language AI

Deterministic, evidence-traceable market-state analysis from completed OHLCV candles. The current interface is command-line output only; no UI or live-data connector is required.

## Run & Operate

- `python mlai_unified.py audit` — validate the imported knowledge book and raw market corpus
- `python mlai_unified.py translate --index 1308` — translate one completed candle using prior context
- `python mlai_unified.py walk-forward --horizon 4 --start 60 --limit 200` — run causal predict/reveal/learn evaluation
- Add `--persist` to the walk-forward command to write `data/market_experience.bin`
- Add `--resume` to use previously persisted experience as historical evidence
- `python MLAI_V420_PRICE_INTERPRETER.py` — translate the latest causal market state into English with exact OHLC, support/resistance price zones, test counts, evidence, scenarios, and confirmation/invalidation prices
- `python download_market_data.py` — download a separate 50-day, 5-minute `GC=F` snapshot for a 40-day reference / 10-day holdout experiment
- `python generate_xauusd_market_data.py` — reproduce the real XAU/USD 5-minute corpus at `data/market_data_50d.bin`
- `python MLAI_V420_UNSEEN_8_2_VALIDATION.py --report MLAI_V420_UNSEEN_8_2_VALIDATION_REPORT.md` — run every available 5-minute candle in the locked 8-day/2-day test
- Add `--horizon 4`, `--horizon 8`, or `--horizon 16` to run one horizon independently when memory is constrained
- Use `--index N` to explain a specific candle, `--horizon 4|8|16` for historical outcome evidence, `--data PATH` for another pickle, and `--json` for structured output
- The console does not require a database, UI, or external service.

## Stack

- Python 3 standard library for the unified console path
- Auditable pickle-compatible binary knowledge and experience files
- Existing pnpm/TypeScript scaffolding is preserved but is not part of the MLAI console runtime

## Where things live

- `mlai_unified.py` — single integration entry point and causal pipeline
- `data/candle_language_v2.bin` — corrected 179-record foundational knowledge
- `data/market_data.bin` — imported 1,309-candle OHLCV corpus
- `data/market_experience.bin` — generated chronological evidence memory
- `MLAI_ARCHITECTURE.md` — integration contracts and preserved-component policy
- `mlai_market_structure_v*.py` and `MLAI_V418_*`/`MLAI_V420_*` — preserved reference/audit implementations

## Architecture decisions

- Foundational candle knowledge and learned market experience are separate binary contracts.
- The unified path enforces `predict -> reveal -> learn`; future candles are never read before prediction.
- Existing v4.x retrieval and causal implementations are preserved and remain a later comparison layer.
- Evidence is reported with sample size and uncertainty; the engine does not manufacture certainty.

## Product

The console translates completed OHLCV candles into measurable candle language,
market context, historical evidence, probabilistic scenarios, and auditable
human-language explanations.

## User preferences

- The user wants command output only; do not add a UI unless explicitly requested.

## Gotchas

- The imported market corpus currently has four timestamp gaps; `audit` reports them as REVIEW.
- A walk-forward run only persists experience when `--persist` is explicitly supplied.
- Existing v4.x files are reference implementations and should not be modified as part of the unified foundation without a measured comparison.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
