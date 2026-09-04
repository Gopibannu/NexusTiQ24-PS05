import os
import io
import json
import traceback
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

from engine.analyzer import analyze_lease_agreement
from engine.rag import rag_instance

load_dotenv()

app = Flask(__name__, static_folder='frontend', static_url_path='')

def extract_text_from_file(file_storage) -> str:
    """Extract text from uploaded .txt, .md, .pdf, or .docx file."""
    filename = file_storage.filename.lower()
    content_bytes = file_storage.read()

    # 1. PDF File Extraction
    if filename.endswith('.pdf'):
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            text_pages = [page.extract_text() for page in reader.pages if page.extract_text()]
            return "\n".join(text_pages).strip()
        except Exception as e:
            print("[PDF Extractor Error]:", e)

    # 2. DOCX File Extraction
    if filename.endswith('.docx') or filename.endswith('.doc'):
        try:
            import docx
            doc = docx.Document(io.BytesIO(content_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text]
            return "\n".join(paragraphs).strip()
        except Exception as e:
            print("[DOCX Extractor Error]:", e)

    # 3. Plain Text / Markdown / Fallback
    try:
        return content_bytes.decode('utf-8', errors='ignore').strip()
    except Exception as e:
        return str(content_bytes)

@app.route('/')
def serve_index():
    return send_from_directory('frontend', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "track": "PS05",
        "index_rules_loaded": len(rag_instance.get_all_rules()),
        "supported_file_types": [".txt", ".md", ".pdf", ".docx", ".doc"]
    })

@app.route('/api/leases', methods=['GET'])
def list_sample_leases():
    """Endpoint listing sample synthetic leases for quick UI testing."""
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'leases'))
    if not os.path.exists(data_dir):
        return jsonify([])

    leases = [
        {"id": "lease_01_clean.txt", "name": "Lease 1 — Clean / Fully Compliant", "expected": "CLEAN"},
        {"id": "lease_02_clean.txt", "name": "Lease 2 — Clean (Alternate Wording)", "expected": "CLEAN"},
        {"id": "lease_03_deviation_deposit.txt", "name": "Lease 3 — Deviation: Deposit 3.5 Months", "expected": "FLAGGED"},
        {"id": "lease_04_deviation_notice.txt", "name": "Lease 4 — Deviation: Notice 15 Days", "expected": "FLAGGED"},
        {"id": "lease_05_missing_maintenance.txt", "name": "Lease 5 — Missing Maintenance Clause", "expected": "FLAGGED"},
        {"id": "lease_06_missing_deposit_return.txt", "name": "Lease 6 — Missing Deposit Return Timeline", "expected": "FLAGGED"},
        {"id": "lease_07_forbidden_autorenew.txt", "name": "Lease 7 — Forbidden Auto-Renewal Clause", "expected": "FLAGGED"},
        {"id": "lease_08_internal_contradiction.txt", "name": "Lease 8 — Internal Contradiction (30 vs 90 days)", "expected": "FLAGGED"}
    ]

    # Include test sample files if available
    sample_test_path = os.path.join(os.path.dirname(__file__), 'data', 'sample_lease_test.txt')
    if os.path.exists(sample_test_path):
        leases.append({"id": "sample_lease_test.txt", "name": "Sample Test Lease (Multi-Violation)", "expected": "FLAGGED"})

    return jsonify(leases)

@app.route('/api/leases/<lease_id>', methods=['GET'])
def get_sample_lease_content(lease_id):
    """Endpoint returning text content of a specific sample lease."""
    safe_name = os.path.basename(lease_id)
    
    # Check data/leases/ first, then data/
    data_leases_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'leases'))
    file_path = os.path.join(data_leases_dir, safe_name)
    if not os.path.exists(file_path):
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
        file_path = os.path.join(data_dir, safe_name)

    if not os.path.exists(file_path):
        return jsonify({"error": "Sample lease file not found"}), 404

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    return jsonify({"id": safe_name, "content": content})

@app.route('/api/review', methods=['POST'])
def review_lease():
    """Main REST endpoint to review a lease agreement (text, json, or file upload)."""
    try:
        lease_text = ""
        
        # 1. File Upload (TXT, MD, PDF, DOCX)
        if 'file' in request.files:
            file_storage = request.files['file']
            lease_text = extract_text_from_file(file_storage)

        # 2. JSON payload
        elif request.is_json and request.json:
            lease_text = request.json.get("lease_text", "")

        # 3. Form payload
        elif request.form:
            lease_text = request.form.get("lease_text", "")

        lease_text = lease_text.strip()
        if not lease_text or len(lease_text) < 30:
            return jsonify({
                "error": "Malformed or empty request. Please provide a valid lease agreement text or file (minimum 30 characters)."
            }), 400

        # Run analysis pipeline
        result = analyze_lease_agreement(lease_text)
        return jsonify(result), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Model analysis call failed or timed out. Please check input text/file or try again.",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    print(f"Starting Lease Review Assistant on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
