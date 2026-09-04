TRACK_ID=PS05

# Lease Agreement Review Assistant

An intelligent, deterministic lease clause review system built for property managers and tenants. It reviews lease agreements clause-by-clause against standard property management positions using the Gemini API (`gemini-3.5-flash-lite` for LLM reasoning and `gemini-embedding-001` for vector embeddings).

## Quick Start (Two Commands)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**:
   ```bash
   python app.py
   ```
   Open [http://localhost:8000](http://localhost:8000) in your browser.

## Features & Verification
- **Clause-by-Clause RAG & LLM Analysis**: Vector search retrieves relevant policy standards and Gemini evaluates clauses for matches, deviations, missing protections, forbidden terms, and internal contradictions.
- **Deterministic Quote Verification**: Every quote returned by the system is checked against the raw lease text. Unverifiable quotes are discarded to prevent hallucinations.
- **Deterministic Compliance Gate**: Status is strictly `"CLEAN"` (only if zero deviations, zero missing protections, zero forbidden terms, zero contradictions) or `"FLAGGED FOR HUMAN REVIEW"`.
- **Precomputed Embedding Cache**: Standard rules vector embeddings are precomputed at `data/standard_positions_index.json` for lightning-fast startup without runtime embedding latency.

## Synthetic Datasets Generated
- `data/standard_positions.md`: Baseline rulebook (deposit limits: 1-2 months, notice period: 30-60 days, mandatory maintenance, mandatory return of deposit within 30 days, strictly forbidden terms).
- `data/leases/`: 8 synthetic lease agreements testing distinct scenarios:
  1. `lease_01_clean.txt` - Fully compliant lease
  2. `lease_02_clean.txt` - Fully compliant lease (different wording)
  3. `lease_03_deviation_deposit.txt` - 3.5 months deposit (exceeds standard max)
  4. `lease_04_deviation_notice.txt` - 15 days notice (below standard min)
  5. `lease_05_missing_maintenance.txt` - Entirely omits maintenance responsibility
  6. `lease_06_missing_deposit_return.txt` - Entirely omits return of deposit timeline
  7. `lease_07_forbidden_autorenew.txt` - Contains forbidden automatic 1-year renewal
  8. `lease_08_internal_contradiction.txt` - Clause 5 (30 days notice) contradicts Clause 14 (90 days notice)

## Demo Video
[Demo Video Link Placeholder]
