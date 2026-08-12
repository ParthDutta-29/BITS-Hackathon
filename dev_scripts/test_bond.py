import json
import re

def test_bond():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    bond_docs = {k: v for k, v in corpus.items() if v['doc_type'] == 'performance_bond'}

    parsed = []
    for doc_id, doc in bond_docs.items():
        text = doc['content']

        # Client / Employer
        cm = (re.search(r'To:\s*(.*?)(?=\s+Subject|\s+India|\s+The Employer|$)', text) or
              re.search(r'To,\s*(.*?)(?=\s+Subject|$)', text))

        # Project / Tender Ref
        pm = (re.search(r'Subject:\s*Performance Bond\s+([A-Za-z0-9\s\-\(\)]+?)(?=\s+Dear|\s+Subject|\s+Value|$)', text) or
              re.search(r'Tender Ref:\s*([A-Za-z0-9\-\s]+?)(?=\s+Dear|\s+Subject|\s+Value|$)', text) or
              re.search(r'work of\s+([A-Za-z0-9\s,\-]+?)(?=\s*,|\s+and WHEREAS|$)', text))

        # Bond Value
        vm = re.search(r'(?:exceeding|amount of|not exceeding)\s+(Rs\.\s+[\d\.]+\s+[A-Za-z]+|INR\s+[\d\.]+\s+[A-Za-z]+|Rs\.\s+[\d\.,]+)', text)

        parsed.append({
            'doc_id': doc_id,
            'client_name': cm.group(1).strip() if cm else None,
            'project_name': pm.group(1).strip() if pm else None,
            'bond_value': vm.group(1).strip() if vm else None
        })

    print(f"Total performance bonds: {len(bond_docs)}")
    print(f"Matched clients: {sum(1 for p in parsed if p['client_name'])}/{len(parsed)}")
    print(f"Matched projects: {sum(1 for p in parsed if p['project_name'])}/{len(parsed)}")
    print(f"Matched values: {sum(1 for p in parsed if p['bond_value'])}/{len(parsed)}")

if __name__ == '__main__':
    test_bond()
