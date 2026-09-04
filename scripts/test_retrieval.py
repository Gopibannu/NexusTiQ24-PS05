import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.rag import RAGStore

def test_retrieval():
    rag = RAGStore()
    assert len(rag.get_all_rules()) == 8, f"Expected 8 rules, got {len(rag.get_all_rules())}"

    test_cases = [
        {
            "clause": "Tenant agrees to pay a security deposit equal to three and a half (3.5) months' monthly rent prior to occupancy.",
            "expected_category": "deposit_range"
        },
        {
            "clause": "Either party may terminate this agreement by delivering fifteen (15) days written notice prior to the end of the term.",
            "expected_category": "notice_period"
        },
        {
            "clause": "Upon expiration of the Initial Term, this Lease Agreement shall automatically renew for an additional full term of twelve (12) months without notice.",
            "expected_category": "forbidden_term"
        },
        {
            "clause": "Landlord shall be strictly responsible for maintaining the structural integrity, heating, plumbing, electrical, and HVAC systems.",
            "expected_category": "required_clause"
        }
    ]

    print("--- Running RAG Retrieval Tests ---")
    for idx, tc in enumerate(test_cases, 1):
        clause = tc["clause"]
        top_matches = rag.search_relevant_rules(clause, top_k=1)
        best = top_matches[0]
        print(f"\n[Test {idx}] Query Clause: '{clause[:60]}...'")
        print(f" -> Top Matched Rule: [{best['id']}] {best['title']}")
        print(f" -> Rule Category: {best['category']}")
        assert best["category"] == tc["expected_category"], f"Expected {tc['expected_category']}, got {best['category']}"

    print("\n[SUCCESS] All RAG retrieval standalone tests PASSED successfully!")

if __name__ == "__main__":
    test_retrieval()
