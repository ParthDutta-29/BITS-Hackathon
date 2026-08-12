import json
import re

def test_cv():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    cv_docs = {k: v for k, v in corpus.items() if v['doc_type'] == 'cv'}

    parsed = []
    for doc_id, doc in cv_docs.items():
        text = doc['content']
        em = (re.search(r'Name\s+([A-Za-z\s]+?)\s+Employee ID', text) or
              re.search(r'CurriCulum Vitae\s+([A-Za-z\s]+?)\s+Designation', text))
        parsed.append({
            'doc_id': doc_id,
            'employee_name': em.group(1).strip() if em else None
        })

    print(f"Total CVs: {len(cv_docs)}")
    print(f"Matched employees: {sum(1 for p in parsed if p['employee_name'])}/{len(parsed)}")

if __name__ == '__main__':
    test_cv()
