import os
import requests

def test_file_uploads():
    url = "http://localhost:8000/api/review"
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))

    test_files = [
        "sample_lease_test.txt",
        "sample_lease_test.md",
        "sample_lease_test.docx",
        "sample_lease_test.pdf"
    ]

    print("==================================================")
    print("   TESTING FILE UPLOADS (.TXT, .MD, .DOCX, .PDF)")
    print("==================================================")

    for f_name in test_files:
        f_path = os.path.join(data_dir, f_name)
        if not os.path.exists(f_path):
            print(f"File not found: {f_name}")
            continue

        with open(f_path, 'rb') as f:
            files = {'file': (f_name, f)}
            res = requests.post(url, files=files)
            if res.status_code == 200:
                data = res.json()
                print(f"[PASSED] Uploaded '{f_name}' -> Status: {data['status']}, Deviations: {data['summary']['deviations_count']}, Forbidden: {data['summary']['forbidden_terms_count']}")
            else:
                print(f"[FAILED] Uploaded '{f_name}' -> Code: {res.status_code}, Error: {res.text[:100]}")

if __name__ == "__main__":
    test_file_uploads()
