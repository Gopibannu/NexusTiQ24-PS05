import os
import json

# Ensure engine path is accessible
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from engine.embedding_utils import get_embedding

def build_index():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
    std_file = os.path.join(data_dir, 'standard_positions.md')
    out_file = os.path.join(data_dir, 'standard_positions_index.json')

    print(f"Reading standard positions from {std_file}...")
    with open(std_file, 'r', encoding='utf-8') as f:
        text = f.read()

    # Rule definitions chunked logically
    rules = [
        {
            "id": "rule_deposit_range",
            "title": "Acceptable Security Deposit Range",
            "category": "deposit_range",
            "content": "Standard Rule: The required security deposit must be between 1.0 month and 2.0 months of base monthly rent. Any deposit requirement less than 1.0 month or exceeding 2.0 months of base monthly rent is an unacceptable deviation."
        },
        {
            "id": "rule_notice_period",
            "title": "Acceptable Termination Notice Period",
            "category": "notice_period",
            "content": "Standard Rule: Written notice for non-renewal or lease termination must be between 30 days and 60 days. Any notice period shorter than 30 days or longer than 60 days is an unacceptable deviation."
        },
        {
            "id": "rule_maintenance_responsibility",
            "title": "Required Protection: Maintenance Responsibility",
            "category": "required_clause",
            "content": "Standard Rule: The lease agreement MUST explicitly mandate that the Landlord is responsible for major structural repairs, heating, HVAC, plumbing, electrical, and major appliances. Absence of landlord maintenance obligations is a Critical Missing Protection."
        },
        {
            "id": "rule_deposit_return_timeline",
            "title": "Required Protection: Return of Security Deposit Timeline",
            "category": "required_clause",
            "content": "Standard Rule: The lease agreement MUST explicitly state a fixed maximum timeframe for returning the Tenant's security deposit post-termination, which cannot exceed 30 calendar days following lease end or property surrender. Absence is a Critical Missing Protection."
        },
        {
            "id": "rule_forbidden_auto_renewal",
            "title": "Forbidden Term: Automatic Renewal Without Notice",
            "category": "forbidden_term",
            "content": "Forbidden Term: Any clause that automatically renews the lease for a multi-month or annual term without requiring advance written notice from the landlord or giving tenant option to cancel."
        },
        {
            "id": "rule_forbidden_waiver_withhold_rent",
            "title": "Forbidden Term: Waiver of Right to Withhold Rent",
            "category": "forbidden_term",
            "content": "Forbidden Term: Any clause forcing the tenant to waive their statutory or legal right to withhold rent or seek remedy if the premises become uninhabitable."
        },
        {
            "id": "rule_forbidden_unilateral_rent_increase",
            "title": "Forbidden Term: Unilateral Rent Increase During Fixed Term",
            "category": "forbidden_term",
            "content": "Forbidden Term: Any clause granting the landlord sole authority to increase monthly rent during an active fixed-term lease without mutual written amendment."
        },
        {
            "id": "rule_forbidden_entry_without_notice",
            "title": "Forbidden Term: Landlord Entry Without 24h Notice",
            "category": "forbidden_term",
            "content": "Forbidden Term: Any clause permitting the landlord or agents to enter the dwelling unit without at least 24 hours prior written notice except active emergency."
        }
    ]

    print("Computing embeddings for standard position rules...")
    indexed_rules = []
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()

    for r in rules:
        emb = get_embedding(r["content"], api_key=api_key)
        rule_item = {
            "id": r["id"],
            "title": r["title"],
            "category": r["category"],
            "content": r["content"],
            "embedding": emb
        }
        indexed_rules.append(rule_item)
        print(f" - Indexed: {r['title']} (Embedding dim: {len(emb)})")

    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(indexed_rules, f, indent=2)

    print(f"Successfully generated precomputed index at {out_file}")

if __name__ == "__main__":
    build_index()
