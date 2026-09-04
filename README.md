TRACK_ID=PS05

# Lease Agreement Review Assistant — Track PS05

An enterprise-grade, deterministic LegalTech lease clause review system built for property management companies and tenants. It reviews lease agreements clause-by-clause against company standard positions using Gemini AI (`gemini-3.5-flash-lite` and `gemini-embedding-001`), RAG vector retrieval, exact quote verification, and deterministic safety rules.

---

## Live Deployment & GitHub Repository

- **Live Web Application (Vercel)**: [https://nexustiq24-ps05.vercel.app](https://nexustiq24-ps05.vercel.app)
- **GitHub Repository**: [https://github.com/Gopibannu/NexusTiQ24-PS05.git](https://github.com/Gopibannu/NexusTiQ24-PS05.git)

---

## Key Highlights & Standout Features

1. **Multi-Format Document Ingestion**:
   - Supports `.txt`, `.md`, `.pdf` (`pypdf`), and `.docx` (`python-docx`) uploads alongside raw text input.

2. **Deterministic Safety Gate & Zero-Hallucination Quote Verification**:
   - Binary compliance output: Strictly **`CLEAN`** or **`FLAGGED FOR HUMAN REVIEW`**.
   - Every quoted snippet in findings is checked against the raw document text. Unverified quotes are automatically discarded.

3. **Sub-5ms SHA-256 In-Memory Caching Engine**:
   - Computes SHA-256 text hashes for instant sub-5ms audit turnarounds on repeated documents.

4. **Automated Counter-Offer & Lease Amendment Exporter**:
   - Generates a ready-to-sign **Lease Amendment Addendum (`.txt`)** formatted with signature blocks and proposed renegotiation clauses.

5. **Client-Side PDF Audit Certificate Generator**:
   - One-click export of executive PDF audit reports directly in the browser via `html2pdf.js`.

6. **Executive UI Inspector & Comparison Matrix**:
   - Side-by-side term comparison matrix.
   - Interactive Source Document Inspector with live quote highlights.
   - Real-Time Policy Rulebook live search.
   - Multi-dimensional risk score breakdown (Financial, Legal, Operational).

---

## Quick Start (Local Server Execution)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch Application**:
   ```bash
   python app.py
   ```
   Open **http://localhost:8000** in your browser.

---

## Deploying on Vercel

1. Import repository `https://github.com/Gopibannu/NexusTiQ24-PS05.git` on Vercel ([vercel.com/new](https://vercel.com/new)).
2. Add Environment Variable:
   - `GEMINI_API_KEY`: Your Gemini API key.
3. Click **Deploy**. Vercel will build serverless functions automatically using `vercel.json` and `api/index.py`.

---

## Synthetic Scenarios Included

- `data/standard_positions.md`: Pre-indexed baseline policy rulebook.
- `data/leases/`: 8 synthetic lease agreements covering:
  1. `lease_01_clean.txt` — Fully compliant standard lease
  2. `lease_02_clean.txt` — Compliant lease (alternate phrasing)
  3. `lease_03_deviation_deposit.txt` — Excess deposit (3.5 months rent)
  4. `lease_04_deviation_notice.txt` — Inadequate notice (15 days)
  5. `lease_05_missing_maintenance.txt` — Missing landlord maintenance duty
  6. `lease_06_missing_deposit_return.txt` — Missing deposit refund timeline
  7. `lease_07_forbidden_autorenew.txt` — Forbidden automatic renewal clause
  8. `lease_08_internal_contradiction.txt` — Contradictory notice clauses (30 vs 90 days)

---

## Integration Test Suite

Run full automated validation across all 8 synthetic lease scenarios and multi-format files:
```bash
python scripts/test_leases.py
python scripts/test_uploads.py
```
