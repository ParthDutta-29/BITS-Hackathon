import json
import re

def test_pcert():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    pcert_docs = {k: v for k, v in corpus.items() if v['doc_type'] == 'personnel_certificate'}

    parsed = []
    for doc_id, doc in pcert_docs.items():
        text = doc['content']

        # Employee Name
        em = (re.search(r'conferred upon\s+([A-Za-z\s]+?)\s+of', text) or
              re.search(r'certify that\s+([A-Za-z\s]+?)\s+Employee ID', text) or
              re.search(r'Registrar\s+([A-Za-z\s]+?)\s+(?:PMI|ASQ)', text) or
              re.search(r'Name\s+([A-Za-z\s]+?)\s+Employee ID', text))

        # Certification Type
        ctm = (re.search(r'Credential Type\s+([A-Za-z0-9\s]+?)(?=\s+Credential ID|\s+Issuing|$)', text) or
               re.search(r'(PMP|Six Sigma Black Belt|ISO 9001 Lead Auditor|PRINCE2 Practitioner|LEED AP)', text, re.IGNORECASE) or
               re.search(r'([A-Za-z0-9\s]+?)\s+CERTIFICATION', text))

        # Issue Date
        dtm = re.search(r'(?:Issued|Date of Issue)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})', text)

        parsed.append({
            'doc_id': doc_id,
            'employee_name': em.group(1).strip() if em else None,
            'cert_type': ctm.group(1).strip() if ctm else None,
            'issue_date': dtm.group(1).strip() if dtm else None
        })

    print(f"Total pcerts: {len(pcert_docs)}")
    print(f"Matched employees: {sum(1 for p in parsed if p['employee_name'])}/{len(parsed)}")
    print(f"Matched cert types: {sum(1 for p in parsed if p['cert_type'])}/{len(parsed)}")
    print(f"Matched issue dates: {sum(1 for p in parsed if p['issue_date'])}/{len(parsed)}")

if __name__ == '__main__':
    test_pcert()
