import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.analyzer import analyze_lease_agreement

def run_all_lease_tests():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'leases'))
    
    test_specs = [
        {"file": "lease_01_clean.txt", "expected_status": "CLEAN", "desc": "Clean lease 1"},
        {"file": "lease_02_clean.txt", "expected_status": "CLEAN", "desc": "Clean lease 2"},
        {"file": "lease_03_deviation_deposit.txt", "expected_status": "FLAGGED FOR HUMAN REVIEW", "check_key": "deviations_count", "desc": "Deposit 3.5 months deviation"},
        {"file": "lease_04_deviation_notice.txt", "expected_status": "FLAGGED FOR HUMAN REVIEW", "check_key": "deviations_count", "desc": "Notice 15 days deviation"},
        {"file": "lease_05_missing_maintenance.txt", "expected_status": "FLAGGED FOR HUMAN REVIEW", "check_key": "missing_protections_count", "desc": "Missing maintenance clause"},
        {"file": "lease_06_missing_deposit_return.txt", "expected_status": "FLAGGED FOR HUMAN REVIEW", "check_key": "missing_protections_count", "desc": "Missing deposit return timeline"},
        {"file": "lease_07_forbidden_autorenew.txt", "expected_status": "FLAGGED FOR HUMAN REVIEW", "check_key": "forbidden_terms_count", "desc": "Forbidden auto-renewal"},
        {"file": "lease_08_internal_contradiction.txt", "expected_status": "FLAGGED FOR HUMAN REVIEW", "check_key": "contradictions_count", "desc": "Internal contradiction (30 vs 90 days)"}
    ]

    print("==================================================")
    print("   RUNNING SYNTHETIC LEASE INTEGRATION TESTS")
    print("==================================================")

    passed_count = 0
    total_count = len(test_specs)

    for idx, spec in enumerate(test_specs, 1):
        file_path = os.path.join(data_dir, spec["file"])
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = analyze_lease_agreement(content)
        status = result["status"]
        summary = result["summary"]

        status_ok = (status == spec["expected_status"])
        
        check_ok = True
        if "check_key" in spec:
            check_ok = (summary.get(spec["check_key"], 0) > 0)

        is_success = status_ok and check_ok

        print(f"\n[Test {idx}/8] {spec['file']} ({spec['desc']})")
        print(f" -> Result Status: '{status}' (Expected: '{spec['expected_status']}')")
        print(f" -> Counts: Deviations={summary['deviations_count']}, Missing={summary['missing_protections_count']}, Forbidden={summary['forbidden_terms_count']}, Contradictions={summary['contradictions_count']}, Matches={summary['matches_count']}")
        
        if is_success:
            print(" -> Outcome: PASSED")
            passed_count += 1
        else:
            print(" -> Outcome: FAILED")

    print("\n==================================================")
    print(f" TEST SUMMARY: {passed_count}/{total_count} LEASES PASSED")
    print("==================================================")

    assert passed_count == total_count, f"Failed {total_count - passed_count} lease integration tests!"

if __name__ == "__main__":
    run_all_lease_tests()
