import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.analyzer import analyze_lease_agreement

def build_reports_cache():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    leases_dir = os.path.join(data_dir, 'leases')
    cache_file = os.path.join(data_dir, 'sample_reports_cache.json')

    lease_files = [
        "lease_01_clean.txt",
        "lease_02_clean.txt",
        "lease_03_deviation_deposit.txt",
        "lease_04_deviation_notice.txt",
        "lease_05_missing_maintenance.txt",
        "lease_06_missing_deposit_return.txt",
        "lease_07_forbidden_autorenew.txt",
        "lease_08_internal_contradiction.txt"
    ]

    print("==================================================")
    print("   PRECOMPUTING SAMPLE LEASES ANALYSIS CACHE")
    print("==================================================")

    reports_cache = {}

    for f_name in lease_files:
        f_path = os.path.join(leases_dir, f_name)
        if not os.path.exists(f_path):
            continue

        with open(f_path, 'r', encoding='utf-8') as f:
            content = f.read()

        print(f" -> Precomputing analysis for {f_name}...")
        report = analyze_lease_agreement(content)

        # Add diff_view objects for deviations and forbidden terms
        for d in report["findings"].get("deviations", []):
            d["diff_view"] = {
                "submitted_clause": d.get("clause_quote", ""),
                "required_standard_clause": d.get("suggested_renegotiation_clause", "")
            }
        for f_item in report["findings"].get("forbidden_terms", []):
            f_item["diff_view"] = {
                "submitted_clause": f_item.get("clause_quote", ""),
                "required_standard_clause": f_item.get("suggested_renegotiation_clause", "")
            }

        reports_cache[f_name] = report

    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(reports_cache, f, indent=2)

    print(f"Successfully generated precomputed analysis cache at {cache_file}")

if __name__ == "__main__":
    build_reports_cache()
