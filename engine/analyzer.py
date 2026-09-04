import os
import re
import json
import time
import requests
from engine.rag import RAGStore

NUMBER_WORDS = {
    "one": 1.0, "one and a half": 1.5, "two": 2.0, "two and a half": 2.5,
    "three": 3.0, "three and a half": 3.5, "four": 4.0,
    "fifteen": 15, "twenty": 20, "twenty-one": 21, "twenty five": 25, "twenty-five": 25,
    "thirty": 30, "forty-five": 45, "forty five": 45, "sixty": 60, "ninety": 90
}

def get_sentence_quote(text: str, pos_start: int, pos_end: int) -> str:
    start = pos_start
    while start > 0 and text[start-1] not in ['\n', '.', ';']:
        start -= 1
    
    end = pos_end
    while end < len(text) and text[end] not in ['\n', '.', ';']:
        end += 1
    if end < len(text) and text[end] in ['.', ';']:
        end += 1
        
    return text[start:end].strip()

def normalize_text(t: str) -> str:
    return re.sub(r'\s+', ' ', t).strip().lower()

def is_quote_in_source(quote: str, source_text: str) -> bool:
    if not quote or quote.strip() in ["N/A", "N/A (Missing from lease)"]:
        return True
    
    if quote in source_text:
        return True
    
    norm_quote = normalize_text(quote)
    norm_source = normalize_text(source_text)
    if norm_quote in norm_source:
        return True

    if len(norm_quote) > 25 and norm_quote[:25] in norm_source:
        return True

    return False

def deterministic_rule_analysis(lease_text: str) -> dict:
    matches = []
    deviations = []
    missing_protections = []
    forbidden_terms = []
    contradictions = []

    text_lower = lease_text.lower()

    # 1. Security Deposit Range Analysis
    dep_match = re.search(r'(?:equal to|deposit of|sum of)?\s*(\d+(?:\.\d+)?|\b(?:one|two|three|four)(?:\s+and\s+a\s+half)?\b|\(\d+(?:\.\d+)?\))\s*months?[\'\s]*rent', text_lower)
    if not dep_match:
        dep_match = re.search(r'security deposit[^\.\n]*?(\d+(?:\.\d+)?|\b(?:one|two|three|four)(?:\s+and\s+a\s+half)?\b|\(\d+(?:\.\d+)?\))\s*months?', text_lower)

    if dep_match:
        quote = get_sentence_quote(lease_text, dep_match.start(), dep_match.end())
        val_str = dep_match.group(1).lower().strip('()')
        
        val = 0.0
        if val_str in NUMBER_WORDS:
            val = NUMBER_WORDS[val_str]
        else:
            try:
                val = float(val_str)
            except ValueError:
                pass

        if val > 0:
            if 1.0 <= val <= 2.0:
                matches.append({
                    "clause_quote": quote,
                    "explanation": f"Security deposit requirement of {val} months' rent is within acceptable range (1.0 to 2.0 months)."
                })
            else:
                deviations.append({
                    "clause_quote": quote,
                    "deviation_explanation": f"Security deposit requirement of {val} months' rent violates company policy (maximum allowed is 2.0 months).",
                    "standard_rule_violated": "Acceptable Security Deposit Range (1.0 - 2.0 months rent)"
                })

    # 2. Termination Notice Period & Contradictions Analysis
    notice_sentences = []
    for line in lease_text.split('\n'):
        line_clean = line.strip()
        if not line_clean:
            continue
        line_lower = line_clean.lower()
        if ("notice" in line_lower or "vacate" in line_lower or "notification" in line_lower) and ("terminate" in line_lower or "non-renewal" in line_lower or "vacate" in line_lower or "expiration" in line_lower):
            if "entry" not in line_lower and "refund of" not in line_lower and "return of" not in line_lower:
                notice_sentences.append(line_clean)

    notice_findings = []
    for s in notice_sentences:
        s_lower = s.lower()
        d_match = re.search(r'(\b\d+\b|\b(?:fifteen|thirty|forty-five|sixty|ninety)\b|\(\d+\))\s*(?:calendar\s*)?days', s_lower)
        if d_match:
            val_str = d_match.group(1).strip('()').lower()
            val = NUMBER_WORDS.get(val_str)
            if not val:
                try:
                    val = int(val_str)
                except ValueError:
                    pass
            if val and val > 0:
                if not any(f["quote"] == s for f in notice_findings):
                    notice_findings.append({"val": int(val), "quote": s})

    if len(notice_findings) >= 2 and len(set(f["val"] for f in notice_findings)) > 1:
        f1 = notice_findings[0]
        f2 = notice_findings[1]
        contradictions.append({
            "clause_quote_1": f1["quote"],
            "clause_quote_2": f2["quote"],
            "explanation": f"Lease contains contradictory termination notice terms ({f1['val']} days in one clause vs {f2['val']} days in another clause)."
        })
    elif len(notice_findings) >= 1:
        f = notice_findings[0]
        days = f["val"]
        quote = f["quote"]
        if 30 <= days <= 60:
            matches.append({
                "clause_quote": quote,
                "explanation": f"Termination notice period of {days} days is within acceptable range (30 to 60 days)."
            })
        else:
            deviations.append({
                "clause_quote": quote,
                "deviation_explanation": f"Notice period of {days} days violates company policy requirement (30 to 60 days).",
                "standard_rule_violated": "Acceptable Termination Notice Period (30 - 60 days)"
            })

    # 3. Required Protection: Maintenance Responsibility
    has_maint = False
    for line in lease_text.split('\n'):
        l_lower = line.lower()
        if ("landlord" in l_lower or "lessor" in l_lower or "management" in l_lower) and ("maintain" in l_lower or "repair" in l_lower or "duties" in l_lower or "responsible" in l_lower or "keep" in l_lower):
            if any(k in l_lower for k in ["hvac", "structural", "plumbing", "heating", "cooling", "roof", "electrical", "utilities"]):
                has_maint = True
                quote = line.strip()
                matches.append({
                    "clause_quote": quote,
                    "explanation": "Landlord maintenance responsibility for major systems and structural components is explicitly defined."
                })
                break

    if not has_maint:
        missing_protections.append({
            "missing_protection": "Landlord Maintenance Responsibility Clause",
            "why_it_matters": "The lease agreement entirely omits landlord maintenance obligations for structural, plumbing, heating, and HVAC systems, exposing tenant to unallocated repair liability."
        })

    # 4. Required Protection: Return of Security Deposit Timeline
    has_dep_ret = False
    for line in lease_text.split('\n'):
        l_lower = line.lower()
        if "deposit" in l_lower and ("refund" in l_lower or "return" in l_lower or "disburse" in l_lower or "pay back" in l_lower):
            d_match = re.search(r'(\b\d+\b|\b(?:twenty-one|twenty-five|thirty|forty-five)\b|\(\d+\))\s*(?:calendar\s*)?days', l_lower)
            if d_match:
                has_dep_ret = True
                quote = line.strip()
                val_str = d_match.group(1).strip('()').lower()
                days_val = NUMBER_WORDS.get(val_str)
                if not days_val:
                    try:
                        days_val = int(val_str)
                    except ValueError:
                        days_val = 30
                
                if days_val <= 30:
                    matches.append({
                        "clause_quote": quote,
                        "explanation": f"Security deposit return timeframe of {days_val} days complies with maximum 30 calendar days requirement."
                    })
                else:
                    deviations.append({
                        "clause_quote": quote,
                        "deviation_explanation": f"Security deposit return timeframe of {days_val} days exceeds company maximum limit of 30 days.",
                        "standard_rule_violated": "Return of Security Deposit Timeline (Max 30 days)"
                    })
                break

    if not has_dep_ret:
        missing_protections.append({
            "missing_protection": "Return of Security Deposit Timeline Clause",
            "why_it_matters": "The lease agreement omits a fixed maximum timeframe for returning the security deposit following lease expiration or property surrender."
        })

    # 5. Forbidden Terms Analysis
    auto_ren_match = re.search(r'automatically renew[^\.\n]*?(without|no notice|no right to cancel)', text_lower)
    if auto_ren_match:
        quote = get_sentence_quote(lease_text, auto_ren_match.start(), auto_ren_match.end())
        forbidden_terms.append({
            "clause_quote": quote,
            "explanation": "Clause mandates automatic lease renewal for a full multi-month/annual term without requiring prior advance written notice or option to terminate."
        })

    waiver_match = re.search(r'waive[^\.\n]*?(right to withhold rent|withhold rent)', text_lower)
    if waiver_match:
        quote = get_sentence_quote(lease_text, waiver_match.start(), waiver_match.end())
        forbidden_terms.append({
            "clause_quote": quote,
            "explanation": "Clause forces tenant to waive statutory right to withhold rent or seek remedy for uninhabitable conditions."
        })

    plain_summary = [
        "Base monthly rent and security deposit requirements.",
        "Notice period required for lease termination or non-renewal.",
        "Landlord structural and system maintenance obligations.",
        "Security deposit refund timeline post-tenancy."
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
    start_time = time.time()
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    rag_store = RAGStore()
    std_rules = rag_store.get_all_rules()

    det_res = deterministic_rule_analysis(lease_text)

    parsed_res = None

    if api_key:
        try:
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
3. "missing_protections": array of items {{"missing_protection": "<what required clause is missing>", "why_it_matters": "<why it matters>"}}
4. "forbidden_terms": array of items {{"clause_quote": "<VERBATIM snippet from lease>", "explanation": "<why forbidden>"}}
5. "contradictions": array of items {{"clause_quote_1": "<VERBATIM quote 1>", "clause_quote_2": "<VERBATIM quote 2>", "explanation": "<why contradictory>"}}
6. "plain_language_summary": array of 3-4 plain-language strings summarizing key terms a signer must understand.

CRITICAL RULE:
- Every "clause_quote", "clause_quote_1", and "clause_quote_2" MUST BE A VERBATIM EXACT QUOTE directly from the lease text above!

Return ONLY valid raw JSON without markdown formatting.
"""
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }
            
            r = requests.post(url, headers=headers, json=payload, timeout=45)
            if r.status_code == 200:
                resp_json = r.json()
                text_out = resp_json["candidates"][0]["content"]["parts"][0]["text"]
                clean_json = re.sub(r'^```json\s*|\s*```$', '', text_out.strip(), flags=re.MULTILINE)
                parsed_res = json.loads(clean_json)
        except Exception as e:
            print(f"[Warning] Gemini API call exception: {e}. Falling back to deterministic engine.")

    if not parsed_res:
        parsed_res = det_res

    # --- DETERMINISTIC QUOTE VERIFICATION ---
    verified_matches = []
    for m in parsed_res.get("matches", []):
        quote = m.get("clause_quote", "")
        if is_quote_in_source(quote, lease_text):
            verified_matches.append(m)
        else:
            print(f"[Quote Verification Dropped Unverifiable Match Quote]: '{quote}'")

    verified_deviations = []
    for d in parsed_res.get("deviations", []):
        quote = d.get("clause_quote", "")
        if is_quote_in_source(quote, lease_text):
            verified_deviations.append(d)
        else:
            print(f"[Quote Verification Dropped Unverifiable Deviation Quote]: '{quote}'")

    verified_forbidden = []
    for f in parsed_res.get("forbidden_terms", []):
        quote = f.get("clause_quote", "")
        if is_quote_in_source(quote, lease_text):
            verified_forbidden.append(f)
        else:
            print(f"[Quote Verification Dropped Unverifiable Forbidden Quote]: '{quote}'")

    verified_contradictions = []
    for c in parsed_res.get("contradictions", []):
        q1 = c.get("clause_quote_1", "")
        q2 = c.get("clause_quote_2", "")
        if is_quote_in_source(q1, lease_text) and is_quote_in_source(q2, lease_text):
            verified_contradictions.append(c)
        else:
            print(f"[Quote Verification Dropped Unverifiable Contradiction Quote]: '{q1}' | '{q2}'")

    missing_protections = parsed_res.get("missing_protections", [])
    plain_summary = parsed_res.get("plain_language_summary", det_res["plain_language_summary"])

    # Fallback merge if LLM output missed findings present in deterministic rule output
    if not verified_deviations and det_res["deviations"]:
        verified_deviations = det_res["deviations"]
    if not missing_protections and det_res["missing_protections"]:
        missing_protections = det_res["missing_protections"]
    if not verified_forbidden and det_res["forbidden_terms"]:
        verified_forbidden = det_res["forbidden_terms"]
    if not verified_contradictions and det_res["contradictions"]:
        verified_contradictions = det_res["contradictions"]

    verified_matches = [m for m in verified_matches if m.get("clause_quote")]
    verified_deviations = [d for d in verified_deviations if d.get("clause_quote")]
    verified_forbidden = [f for f in verified_forbidden if f.get("clause_quote")]

    # --- DETERMINISTIC FINAL COMPLIANCE GATE ---
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
