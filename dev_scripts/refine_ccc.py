import json
import re

def refine_ccc():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    ccc_docs = {k: v for k, v in corpus.items() if v['doc_type'] == 'company_completion_certificate'}

    missing_proj = []
    missing_client = []
    missing_val = []

    for doc_id, doc in ccc_docs.items():
        text = doc['content']

        # Project Name
        pm = (re.search(r'Project Name\s+(.*?)(?=\s+(?:Client|Scope|Work|Contract|Completion|Project Manager|$))', text) or
              re.search(r'Work\s+(.*?)(?=\s+(?:Client|Category|Executed Value|Completion|Project Lead|$))', text) or
              re.search(r'work of\s+(.*?)\s*\([^\)]+\)', text) or
              re.search(r'work of\s+(.*?)\s*,', text) or
              re.search(r'work of\s+(.*?)\s+awarded to', text))
        
        # Client Name
        cm = (re.search(r'Client\s+(.*?)(?=\s+(?:Scope|Category|Executed Value|Contract|Completion|Project Lead|Manager|$))', text) or
              re.search(r'Issued by\s+(.*?)(?=\s+REF|Ref|Date|$)', text) or
              re.search(r'Office of the Executive Engineer\s+(.*?)(?=\s+IN No|Dated|$)', text) or
              re.search(r'for\s+(.*?)\s+completed \d{4}', text))

        # Value
        vm = re.search(r'(?:Executed Value|Contract Value|gross executed value of|Value)\s+(INR\s+[\d\.]+\s+[A-Za-z]+|Rs\.\s+[\d\.]+\s+[A-Za-z]+|[\d\.,]+\s+Crore|[\d\.,]+\s+Lakh|[\d\.,]+)', text, re.IGNORECASE)

        if not pm:
            missing_proj.append((doc_id, text[:200]))
        if not cm:
            missing_client.append((doc_id, text[:200]))
        if not vm:
            missing_val.append((doc_id, text[:200]))

    print(f"CCC total: {len(ccc_docs)}")
    print(f"Missing Proj: {len(missing_proj)}")
    print(f"Missing Client: {len(missing_client)}")
    print(f"Missing Value: {len(missing_val)}")

    if missing_proj:
        print("\nSample missing project:")
        for doc_id, snippet in missing_proj[:3]:
            print(f"[{doc_id}] {snippet}")

if __name__ == '__main__':
    refine_ccc()
