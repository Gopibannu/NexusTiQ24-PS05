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
    while start > 0 and text[start-1] not in ['\n', '\r', '.', ';']:
        start -= 1
    
    end = pos_end
    while end < len(text) and text[end] not in ['\n', '\r', '.', ';']:
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

def get_lease_sentences(lease_text: str) -> list:
    """Split lease text cleanly by lines, newlines, and sentence boundary periods."""
    raw_chunks = re.split(r'[\r\n;\.]+', lease_text)
    cleaned = []
    for c in raw_chunks:
        s = c.strip()
        if len(s) >= 10:
            cleaned.append(s)
    return cleaned

def deterministic_rule_analysis(lease_text: str) -> dict:
    matches = []
    deviations = []
    missing_protections = []
    forbidden_terms = []
    contradictions = []
    comparison_table = []

    text_lower = lease_text.lower()
    sentences = get_lease_sentences(lease_text)

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
                comparison_table.append({
                    "parameter": "Security Deposit Range",
                    "submitted_term": f"{val} months' rent",
                    "standard_policy": "1.0 to 2.0 months' rent",
                    "status": "COMPLIANT"
                })
            else:
                deviations.append({
                    "clause_quote": quote,
                    "deviation_explanation": f"Security deposit requirement of {val} months' rent violates company policy (maximum allowed is 2.0 months).",
                    "standard_rule_violated": "Acceptable Security Deposit Range (1.0 - 2.0 months rent)",
                    "suggested_renegotiation_clause": "Tenant shall pay to Landlord a Security Deposit in the sum equal to one and a half (1.5) months' base monthly rent prior to occupancy, held in accordance with applicable residential leasing standards."
                })
                comparison_table.append({
                    "parameter": "Security Deposit Range",
                    "submitted_term": f"{val} months' rent",
                    "standard_policy": "1.0 to 2.0 months' rent",
                    "status": "DEVIATION"
                })

    # 2. Termination Notice Period & Contradictions Analysis
    notice_findings = []
    for s in sentences:
        s_lower = s.lower()
        if ("notice" in s_lower or "vacate" in s_lower or "notification" in s_lower) and ("terminate" in s_lower or "non-renewal" in s_lower or "vacate" in s_lower or "expiration" in s_lower):
            if "entry" not in s_lower and "refund of" not in s_lower and "return of" not in s_lower:
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
        comparison_table.append({
            "parameter": "Termination Notice Period",
            "submitted_term": f"Contradictory ({f1['val']} days vs {f2['val']} days)",
            "standard_policy": "30 to 60 days written notice",
            "status": "CONTRADICTION"
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
            comparison_table.append({
                "parameter": "Termination Notice Period",
                "submitted_term": f"{days} days notice",
                "standard_policy": "30 to 60 days written notice",
                "status": "COMPLIANT"
            })
        else:
            deviations.append({
                "clause_quote": quote,
                "deviation_explanation": f"Notice period of {days} days violates company policy requirement (30 to 60 days).",
                "standard_rule_violated": "Acceptable Termination Notice Period (30 - 60 days)",
                "suggested_renegotiation_clause": "Either party may terminate or elect not to renew this Lease Agreement upon the expiration of the initial term by delivering thirty (30) days prior written notice to the other party."
            })
            comparison_table.append({
                "parameter": "Termination Notice Period",
                "submitted_term": f"{days} days notice",
                "standard_policy": "30 to 60 days written notice",
                "status": "DEVIATION"
            })

    # 3. Required Protection: Maintenance Responsibility
    has_maint = False
    for s in sentences:
        l_lower = s.lower()
        if ("landlord" in l_lower or "lessor" in l_lower or "management" in l_lower) and ("maintain" in l_lower or "repair" in l_lower or "duties" in l_lower or "responsible" in l_lower or "keep" in l_lower):
            if any(k in l_lower for k in ["hvac", "structural", "plumbing", "heating", "cooling", "roof", "electrical", "utilities"]):
                has_maint = True
                quote = s
                matches.append({
                    "clause_quote": quote,
                    "explanation": "Landlord maintenance responsibility for major systems and structural components is explicitly defined."
                })
                comparison_table.append({
                    "parameter": "Maintenance Responsibility",
                    "submitted_term": "Landlord structural/HVAC maintenance included",
                    "standard_policy": "Mandatory Landlord structural & HVAC duty",
                    "status": "COMPLIANT"
                })
                break

    if not has_maint:
        missing_protections.append({
            "missing_protection": "Landlord Maintenance Responsibility Clause",
            "why_it_matters": "The lease agreement entirely omits landlord maintenance obligations for structural, plumbing, heating, and HVAC systems, exposing tenant to unallocated repair liability.",
            "suggested_renegotiation_clause": "Landlord Maintenance Responsibility: Landlord shall be strictly responsible for maintaining the structural integrity of the Premises, roof, foundations, plumbing systems, electrical grids, and central HVAC systems in proper operating condition throughout the Lease term."
        })
        comparison_table.append({
            "parameter": "Maintenance Responsibility",
            "submitted_term": "Omitted (Entirely Silent)",
            "standard_policy": "Mandatory Landlord structural & HVAC duty",
            "status": "MISSING"
        })

    # 4. Required Protection: Return of Security Deposit Timeline
    has_dep_ret = False
    for s in sentences:
        l_lower = s.lower()
        if "deposit" in l_lower and ("refund" in l_lower or "return" in l_lower or "disburse" in l_lower or "pay back" in l_lower):
            d_match = re.search(r'(\b\d+\b|\b(?:twenty-one|twenty-five|thirty|forty-five)\b|\(\d+\))\s*(?:calendar\s*)?days', l_lower)
            if d_match:
                has_dep_ret = True
                quote = s
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
                    comparison_table.append({
                        "parameter": "Deposit Refund Timeline",
                        "submitted_term": f"{days_val} calendar days",
                        "standard_policy": "Maximum 30 calendar days",
                        "status": "COMPLIANT"
                    })
                else:
                    deviations.append({
                        "clause_quote": quote,
                        "deviation_explanation": f"Security deposit return timeframe of {days_val} days exceeds company maximum limit of 30 days.",
                        "standard_rule_violated": "Return of Security Deposit Timeline (Max 30 days)",
                        "suggested_renegotiation_clause": "Within thirty (30) calendar days following the expiration of this Lease and surrender of Premises by Tenant, Landlord shall refund the Security Deposit in full alongside an itemized written statement of lawful deductions."
                    })
                    comparison_table.append({
                        "parameter": "Deposit Refund Timeline",
                        "submitted_term": f"{days_val} calendar days",
                        "standard_policy": "Maximum 30 calendar days",
                        "status": "DEVIATION"
                    })
                break

    if not has_dep_ret:
        missing_protections.append({
            "missing_protection": "Return of Security Deposit Timeline Clause",
            "why_it_matters": "The lease agreement omits a fixed maximum timeframe for returning the security deposit following lease expiration or property surrender.",
            "suggested_renegotiation_clause": "Security Deposit Return: Landlord shall refund the Security Deposit alongside a written itemized accounting of any lawful deductions within thirty (30) calendar days following key surrender and tenancy conclusion."
        })
        comparison_table.append({
            "parameter": "Deposit Refund Timeline",
            "submitted_term": "Omitted (Entirely Silent)",
            "standard_policy": "Maximum 30 calendar days",
            "status": "MISSING"
        })

    # 5. Forbidden Terms Analysis
    auto_ren_match = re.search(r'automatically renew[^\.\r\n]*?(without|no notice|no right to cancel)', text_lower)
    if auto_ren_match:
        quote = get_sentence_quote(lease_text, auto_ren_match.start(), auto_ren_match.end())
        forbidden_terms.append({
            "clause_quote": quote,
            "explanation": "Clause mandates automatic lease renewal for a full multi-month/annual term without requiring prior advance written notice or option to terminate.",
            "suggested_renegotiation_clause": "Tenancy Renewal: Upon expiration of the initial term, this Lease Agreement shall convert to a month-to-month tenancy, terminable by either party upon thirty (30) days advance written notice."
        })
        comparison_table.append({
            "parameter": "Lease Renewal Mechanism",
            "submitted_term": "Automatic 1-Year Renewal without notice",
            "standard_policy": "Explicit prior notice required; no forced auto-renewal",
            "status": "FORBIDDEN"
        })

    waiver_match = re.search(r'waive[^\.\r\n]*?(right to withhold rent|withhold rent)', text_lower)
    if waiver_match:
        quote = get_sentence_quote(lease_text, waiver_match.start(), waiver_match.end())
        forbidden_terms.append({
            "clause_quote": quote,
            "explanation": "Clause forces tenant to waive statutory right to withhold rent or seek remedy for uninhabitable conditions.",
            "suggested_renegotiation_clause": "Tenant Remedies: Nothing in this Agreement shall operate to waive any statutory rights or legal remedies available to Tenant under applicable local and state residential housing codes."
        })
        comparison_table.append({
            "parameter": "Tenant Legal Remedies",
            "submitted_term": "Waiver of right to withhold rent",
            "standard_policy": "Zero tolerance for waiver of statutory tenant rights",
            "status": "FORBIDDEN"
        })

    plain_summary = [
        "Base monthly rent payment schedule and security deposit obligations.",
        "Required written notice period for non-renewal or lease termination.",
        "Landlord structural and utility system maintenance duties.",
        "Security deposit refund timeframe and itemized deduction rules."
    ]

    return {
        "matches": matches,
        "deviations": deviations,
        "missing_protections": missing_protections,
        "forbidden_terms": forbidden_terms,
        "contradictions": contradictions,
        "comparison_table": comparison_table,
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
2. "deviations": array of items {{"clause_quote": "<VERBATIM snippet from lease>", "deviation_explanation": "<plain language explanation>", "standard_rule_violated": "<rule title/ref>", "suggested_renegotiation_clause": "<replacement clause>"}}
3. "missing_protections": array of items {{"missing_protection": "<what required clause is missing>", "why_it_matters": "<why it matters>", "suggested_renegotiation_clause": "<suggested clause to add>"}}
4. "forbidden_terms": array of items {{"clause_quote": "<VERBATIM snippet from lease>", "explanation": "<why forbidden>", "suggested_renegotiation_clause": "<replacement clause>"}}
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
                parsed_val = json.loads(clean_json)
                if isinstance(parsed_val, list):
                    if len(parsed_val) > 0 and isinstance(parsed_val[0], dict):
                        parsed_res = parsed_val[0]
                elif isinstance(parsed_val, dict):
                    parsed_res = parsed_val
        except Exception as e:
            print(f"[Warning] Gemini API call exception: {e}. Falling back to deterministic engine.")

    if not isinstance(parsed_res, dict):
        parsed_res = det_res

    # --- DETERMINISTIC QUOTE VERIFICATION ---
    verified_matches = []
    for m in parsed_res.get("matches", []):
        if isinstance(m, dict):
            quote = m.get("clause_quote", "")
            if is_quote_in_source(quote, lease_text):
                verified_matches.append(m)

    verified_deviations = []
    for d in parsed_res.get("deviations", []):
        if isinstance(d, dict):
            quote = d.get("clause_quote", "")
            if is_quote_in_source(quote, lease_text):
                verified_deviations.append(d)

    verified_forbidden = []
    for f in parsed_res.get("forbidden_terms", []):
        if isinstance(f, dict):
            quote = f.get("clause_quote", "")
            if is_quote_in_source(quote, lease_text):
                verified_forbidden.append(f)

    verified_contradictions = []
    for c in parsed_res.get("contradictions", []):
        if isinstance(c, dict):
            q1 = c.get("clause_quote_1", "")
            q2 = c.get("clause_quote_2", "")
            if is_quote_in_source(q1, lease_text) and is_quote_in_source(q2, lease_text):
                verified_contradictions.append(c)

    missing_protections = parsed_res.get("missing_protections", [])
    if not isinstance(missing_protections, list):
        missing_protections = []

    plain_summary = parsed_res.get("plain_language_summary", det_res["plain_language_summary"])
    if not isinstance(plain_summary, list):
        plain_summary = det_res["plain_language_summary"]

    comparison_table = parsed_res.get("comparison_table", det_res.get("comparison_table", []))
    if not isinstance(comparison_table, list):
        comparison_table = det_res.get("comparison_table", [])

    # Fallback merge if LLM output missed findings present in deterministic rule output
    if not verified_deviations and det_res["deviations"]:
        verified_deviations = det_res["deviations"]
    if not missing_protections and det_res["missing_protections"]:
        missing_protections = det_res["missing_protections"]
    if not verified_forbidden and det_res["forbidden_terms"]:
        verified_forbidden = det_res["forbidden_terms"]
    if not verified_contradictions and det_res["contradictions"]:
        verified_contradictions = det_res["contradictions"]
    if not comparison_table and det_res["comparison_table"]:
        comparison_table = det_res["comparison_table"]

    verified_matches = [m for m in verified_matches if isinstance(m, dict) and m.get("clause_quote")]
    verified_deviations = [d for d in verified_deviations if isinstance(d, dict) and d.get("clause_quote")]
    verified_forbidden = [f for f in verified_forbidden if isinstance(f, dict) and f.get("clause_quote")]

    financial_risk = 100 - (len(verified_deviations) * 30 + len(verified_forbidden) * 20)
    financial_risk = max(0, financial_risk)

    legal_risk = 100 - (len(verified_forbidden) * 50 + len(verified_contradictions) * 35)
    legal_risk = max(0, legal_risk)

    operational_risk = 100 - (len(missing_protections) * 40 + len(verified_deviations) * 15)
    operational_risk = max(0, operational_risk)

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
        "risk_breakdown": {
            "financial_score": financial_risk,
            "legal_score": legal_risk,
            "operational_score": operational_risk
        },
        "comparison_table": comparison_table,
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
