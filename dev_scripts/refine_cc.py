import json
import re

def refine_cc():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    cc_docs = {k: v for k, v in corpus.items() if v['doc_type'] == 'completion_certificate'}

    missing_proj = []
    missing_client = []
    missing_val = []

    for doc_id, doc in cc_docs.items():
        text = doc['content']

        pm = (re.search(r'work of\s+([A-Za-z0-9\s\-]+?)\s*\(', text) or
              re.search(r'Project Name\s+(.*?)(?=\s+(?:Client|Scope|Work|Contract|Completion|Project Manager|$))', text) or
              re.search(r'Work\s+(.*?)(?=\s+(?:Client|Category|Executed Value|Completion|Project Lead|$))', text) or
              re.search(r'Name of Work\s+(.*?)(?=\s+(?:Nature|Category|Contract|Completion|Defect|$))', text) or
              re.search(r'work of\s+([A-Za-z0-9\s\-]+?)\s*,', text))
        
        cm = (re.search(r'^(.*?)\s+(?:Office of|IN No|WORK COMPLETION|Work Completion|Dated)', text, re.MULTILINE) or
              re.search(r'Client\s+(.*?)(?=\s+(?:Scope|Category|Executed Value|Contract|Completion|Project Lead|Manager|$))', text) or
              re.search(r'Executive Engineer\s+(.*?)(?=\s+DOC-|$)', text))

        vm = re.search(r'(?:gross executed value of|Executed Value|Contract Value|Value)\s+(INR\s+[\d\.]+\s+[A-Za-z]+|Rs\.\s+[\d\.]+\s+[A-Za-z]+|[\d\.,]+\s+Crore|[\d\.,]+\s+Lakh|[\d\.,]+)', text, re.IGNORECASE)

        if not pm:
            missing_proj.append((doc_id, text[:250]))
        if not cm:
            missing_client.append((doc_id, text[:250]))
        if not vm:
            missing_val.append((doc_id, text[:250]))

    print(f"CC total: {len(cc_docs)}")
    print(f"Missing Proj: {len(missing_proj)}")
    print(f"Missing Client: {len(missing_client)}")
    print(f"Missing Value: {len(missing_val)}")

    if missing_proj:
        print("\nSample missing project:")
        for doc_id, snippet in missing_proj[:3]:
            print(f"[{doc_id}] {snippet}")

if __name__ == '__main__':
    refine_cc()
