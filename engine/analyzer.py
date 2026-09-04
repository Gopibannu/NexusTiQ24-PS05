import os
import re
import json
import time
import requests
from engine.rag import RAGStore

def normalize_text(t: str) -> str:
    """Normalize text by collapsing whitespace and lowercasing for fuzzy verification."""
    return re.sub(r'\s+', ' ', t).strip().lower()

def is_quote_in_source(quote: str, source_text: str) -> bool:
    """Deterministically checks if a quoted snippet exists in the raw lease document."""
    if not quote or quote.strip() in ["N/A", "N/A (Missing from lease)"]:
        return True # Silence findings do not require document quote match
    
    # 1. Exact string match
    if quote in source_text:
        return True
    
    # 2. Normalized whitespace match
    norm_quote = normalize_text(quote)
    norm_source = normalize_text(source_text)
    if norm_quote in norm_source:
        return True

    # 3. Substring fragment match (if quote is long and slightly truncated)
    if len(norm_quote) > 30 and norm_quote[:30] in norm_source:
        return True

    return False

def deterministic_fallback_analysis(lease_text: str, rag_store: RAGStore) -> dict:
    """
    Deterministic rule-based analyzer used as fallback or verification baseline.
    Checks lease text against standard position rules.
    """
    matches = []
    deviations = []
    missing_protections = []
    forbidden_terms = []
    contradictions = []

    text_lower = lease_text.lower()
    norm_text = normalize_text(lease_text)

    # 1. Check Security Deposit Range
    # Match numbers like $3,000.00 (equal to 1.5 months' rent) or 3.5 months'
    dep_match = re.search(r'security deposit[^\.\n]*?(\d+(?:\.\d+)?)\s*months?', text_lower)
    if not dep_match:
        dep_match = re.search(r'deposit[^\.\n]*?(\d+(?:\.\d+)?)\s*months?', text_lower)
    
    if dep_match:
        val = float(dep_match.group(1))
        # Find sentence for quote
        start = max(0, dep_match.start() - 50)
        end = min(len(lease_text), dep_match.end() + 50)
        quote_snippet = lease_text[start:end].strip()
        
        if 1.0 <= val <= 2.0:
            matches.append({
                "clause_quote": quote_snippet,
                "explanation": f"Security deposit of {val} months rent is within the acceptable 1.0 to 2.0 months range."
            })
        else:
            deviations.append({
                "clause_quote": quote_snippet,
                "deviation_explanation": f"Security deposit of {val} months rent exceeds acceptable maximum of 2.0 months.",
                "standard_rule_violated": "Acceptable Security Deposit Range (1.0 - 2.0 months rent)"
            })

    # 2. Check Termination Notice Period
    notice_matches = list(re.finditer(r'(\d+)\s*\(\d+\)\s*days[^\.\n]*?notice|(\d+)\s*days[^\.\n]*?notice|notice[^\.\n]*?(\d+)\s*days', text_lower))
    found_notices = []
    for nm in notice_matches:
        days = int(nm.group(1) or nm.group(2) or nm.group(3))
        start = max(0, nm.start() - 40)
        end = min(len(lease_text), nm.end() + 40)
        found_notices.append((days, lease_text[start:end].strip()))

    if found_notices:
        # Check internal contradiction if multiple distinct notice periods exist
        notice_days_set = set(n[0] for n in found_notices)
        if len(notice_days_set) > 1:
            quote1 = found_notices[0][1]
            quote2 = found_notices[1][1]
            contradictions.append({
                "clause_quote_1": quote1,
                "clause_quote_2": quote2,
                "explanation": f"Lease contains contradictory termination notice requirements ({found_notices[0][0]} days vs {found_notices[1][0]} days)."
            })
        else:
            days, quote_snippet = found_notices[0]
            if 30 <= days <= 60:
                matches.append({
                    "clause_quote": quote_snippet,
                    "explanation": f"Termination notice period of {days} days is within the acceptable 30 to 60 days range."
                })
            else:
                deviations.append({
                    "clause_quote": quote_snippet,
                    "deviation_explanation": f"Notice period of {days} days violates standard position requirement of 30 to 60 days.",
                    "standard_rule_violated": "Acceptable Termination Notice Period (30 - 60 days)"
                })

    # 3. Check Required Clause: Maintenance Responsibility
    if "maintain" in norm_text or "repair" in norm_text or "hvac" in norm_text:
        # Check if landlord obligations mentioned
        if "landlord" in norm_text or "lessor" in norm_text or "property management" in norm_text:
            m_match = re.search(r'(landlord|lessor)[^\.\n]*?(strictly responsible|responsible|agrees|maintains)[^\.\n]*?(hvac|structural|repair|plumbing)', text_lower)
            if m_match:
                start = max(0, m_match.start() - 20)
                end = min(len(lease_text), m_match.end() + 40)
                matches.append({
                    "clause_quote": lease_text[start:end].strip(),
                    "explanation": "Landlord maintenance obligations for major structural and systemic repairs are explicitly defined."
                })
    else:
        missing_protections.append({
            "missing_protection": "Landlord Maintenance Responsibility Clause",
            "why_it_matters": "The lease entirely omits landlord maintenance obligations for major structural, HVAC, and plumbing repairs, exposing tenant to ambiguous liability."
        })

    # 4. Check Required Clause: Deposit Return Timeline
    dep_ret_match = re.search(r'(refund|return)[^\.\n]*?deposit[^\.\n]*?(\d+)\s*(calendar\s*)?days|deposit[^\.\n]*?(refund|return)[^\.\n]*?(\d+)\s*days', text_lower)
    if dep_ret_match:
        start = max(0, dep_ret_match.start() - 20)
        end = min(len(lease_text), dep_ret_match.end() + 40)
        quote_snippet = lease_text[start:end].strip()
        days_str = dep_ret_match.group(2) or dep_ret_match.group(5)
        days_val = int(days_str) if days_str else 30
        if days_val <= 30:
            matches.append({
                "clause_quote": quote_snippet,
                "explanation": f"Deposit return timeline of {days_val} days complies with maximum 30 calendar days rule."
            })
        else:
            deviations.append({
                "clause_quote": quote_snippet,
                "deviation_explanation": f"Deposit return timeline of {days_val} days exceeds maximum allowable 30 days.",
                "standard_rule_violated": "Return of Security Deposit Timeline (Max 30 days)"
            })
    else:
        missing_protections.append({
            "missing_protection": "Return of Security Deposit Timeline Clause",
            "why_it_matters": "The lease omits a maximum timeframe for returning the security deposit post-tenancy."
        })

    # 5. Check Forbidden Terms: Automatic Renewal Without Notice
    auto_ren = re.search(r'automatically renew[^\.\n]*?(without|no right to cancel|additional full term)', text_lower)
    if auto_ren:
        start = max(0, auto_ren.start() - 30)
        end = min(len(lease_text), auto_ren.end() + 60)
        forbidden_terms.append({
            "clause_quote": lease_text[start:end].strip(),
            "explanation": "Clause mandates automatic lease renewal without requiring prior advance written notice or right to opt out."
        })

    plain_summary = [
        "Base monthly rent and payment terms.",
        "Security deposit amount and refund conditions.",
        "Termination notice period and renewal procedure.",
        "Landlord vs. Tenant maintenance obligations."
    ]

    return {
        "matches": matches,
        "deviations": deviations,
        "missing_protections": missing_protections,
        "forbidden_terms": forbidden_terms,
        "contradictions": contradictions,
        "plain_language_summary": plain_summary
    }

def analyze_lease_agreement(lease_text: str, api_key: str = None) -> dict:
    """
    Main review pipeline.
    Combines Gemini LLM reasoning (`gemini-3.5-flash-lite`) with RAG vector search,
    deterministic quote verification, and deterministic final status gating.
    """
    start_time = time.time()
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    rag_store = RAGStore()
    std_rules = rag_store.get_all_rules()

    # Pre-generate deterministic baseline fallback
    fallback_res = deterministic_fallback_analysis(lease_text, rag_store)

    parsed_res = None

    if api_key:
        try:
            # Construct LLM prompt with RAG standard rules context & lease text
            rules_context = "\n".join([f"- [{r['id']}] {r['title']}: {r['content']}" for r in std_rules])
            
            prompt = f"""You are an expert legal contract analyst for a property management company.
Review the following lease agreement against our standard property management positions.

### STANDARD POSITIONS RULEBOOK:
{rules_context}

### RAW LEASE AGREEMENT TO REVIEW:
\"\"\"
{lease_text}
\"\"\"

### INSTRUCTIONS:
Analyze the lease clause-by-clause and generate a JSON report with exact keys:
1. "matches": array of items {{"clause_quote": "<VERBATIM snippet from lease>", "explanation": "<why it matches>"}}
2. "deviations": array of items {{"clause_quote": "<VERBATIM snippet from lease>", "deviation_explanation": "<plain language explanation>", "standard_rule_violated": "<rule title/ref>"}}
3. "missing_protections": array of items {{"missing_protection": "<what required clause is missing>", "why_it_matters": "<why it matters>"}} (State clearly if maintenance responsibility or return-of-deposit timeline is missing entirely).
4. "forbidden_terms": array of items {{"clause_quote": "<VERBATIM snippet from lease>", "explanation": "<why forbidden>"}}
5. "contradictions": array of items {{"clause_quote_1": "<VERBATIM quote 1>", "clause_quote_2": "<VERBATIM quote 2>", "explanation": "<why contradictory>"}}
6. "plain_language_summary": array of 3-4 plain-language strings summarizing key terms a signer must understand.

CRITICAL RULE:
- Every "clause_quote", "clause_quote_1", and "clause_quote_2" MUST BE A VERBATIM EXACT QUOTE directly from the lease text above! Do not paraphrase quotes.

Return ONLY valid raw JSON without markdown formatting or code blocks.
"""
            # Call Gemini model "gemini-3.5-flash-lite"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }
            
            # Timeout set to 45s (well within 60s limit)
            r = requests.post(url, headers=headers, json=payload, timeout=45)
            if r.status_code == 200:
                resp_json = r.json()
                text_out = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                # Clean code blocks if present
                clean_json = re.sub(r'^```json\s*|\s*```$', '', text_out.strip(), flags=re.MULTILINE)
                parsed_res = json.loads(clean_json)
            else:
                print(f"[Warning] Gemini API returned status {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[Warning] Gemini API call exception: {e}. Falling back to deterministic engine.")

    # Merge or fallback
    if not parsed_res:
        parsed_res = fallback_res

    # --- DETERMINISTIC QUOTE VERIFICATION ---
    verified_matches = []
    for m in parsed_res.get("matches", []):
        quote = m.get("clause_quote", "")
        if is_quote_in_source(quote, lease_text):
            verified_matches.append(m)
        else:
            print(f"[Quote Verification Dropped Hallucinated Match Quote]: '{quote}'")

    verified_deviations = []
    for d in parsed_res.get("deviations", []):
        quote = d.get("clause_quote", "")
        if is_quote_in_source(quote, lease_text):
            verified_deviations.append(d)
        else:
            print(f"[Quote Verification Dropped Hallucinated Deviation Quote]: '{quote}'")

    verified_forbidden = []
    for f in parsed_res.get("forbidden_terms", []):
        quote = f.get("clause_quote", "")
        if is_quote_in_source(quote, lease_text):
            verified_forbidden.append(f)
        else:
            print(f"[Quote Verification Dropped Hallucinated Forbidden Quote]: '{quote}'")

    verified_contradictions = []
    for c in parsed_res.get("contradictions", []):
        q1 = c.get("clause_quote_1", "")
        q2 = c.get("clause_quote_2", "")
        if is_quote_in_source(q1, lease_text) and is_quote_in_source(q2, lease_text):
            verified_contradictions.append(c)
        else:
            print(f"[Quote Verification Dropped Hallucinated Contradiction Quotes]: '{q1}' | '{q2}'")

    missing_protections = parsed_res.get("missing_protections", [])
    plain_summary = parsed_res.get("plain_language_summary", fallback_res["plain_language_summary"])

    # Enforce deterministic fallback findings if LLM missed obvious issues detected by rule engine
    if not verified_deviations and fallback_res["deviations"]:
        verified_deviations = fallback_res["deviations"]
    if not missing_protections and fallback_res["missing_protections"]:
        missing_protections = fallback_res["missing_protections"]
    if not verified_forbidden and fallback_res["forbidden_terms"]:
        verified_forbidden = fallback_res["forbidden_terms"]
    if not verified_contradictions and fallback_res["contradictions"]:
        verified_contradictions = fallback_res["contradictions"]

    # --- DETERMINISTIC COMPLIANCE GATE ---
    # CLEAN strictly requires zero deviations, zero missing protections, zero forbidden terms, zero contradictions
    is_clean = (
        len(verified_deviations) == 0 and
        len(missing_protections) == 0 and
        len(verified_forbidden) == 0 and
        len(verified_contradictions) == 0
    )

    final_status = "CLEAN" if is_clean else "FLAGGED FOR HUMAN REVIEW"

    elapsed_ms = int((time.time() - start_time) * 1000)

    return {
        "status": final_status,
        "is_clean": is_clean,
        "summary": {
            "matches_count": len(verified_matches),
            "deviations_count": len(verified_deviations),
            "missing_protections_count": len(missing_protections),
            "forbidden_terms_count": len(verified_forbidden),
            "contradictions_count": len(verified_contradictions)
        },
        "findings": {
            "matches": verified_matches,
            "deviations": verified_deviations,
            "missing_protections": missing_protections,
            "forbidden_terms": verified_forbidden,
            "contradictions": verified_contradictions
        },
        "plain_language_summary": plain_summary,
        "processing_time_ms": elapsed_ms
    }
