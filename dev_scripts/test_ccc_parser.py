import json
import re

def test_extract():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    ccc_docs = [v for v in corpus.values() if v['doc_type'] == 'company_completion_certificate']
    print(f"Total CCC docs: {len(ccc_docs)}")

    parsed = []
    for doc in ccc_docs:
        text = doc['content']
        # Work
        work_m = re.search(r'Work\s+(.*?)\s+Client', text)
        client_m = re.search(r'Client\s+(.*?)\s+Category', text)
        cat_m = re.search(r'Category\s+(.*?)\s+Executed Value', text)
        val_m = re.search(r'Executed Value\s+(.*?)\s+Completion', text)
        comp_m = re.search(r'Completion\s+(.*?)\s+Project Lead', text)
        lead_m = re.search(r'Project Lead\s+(.*?)\s+Defect Liability', text)

        parsed.append({
            'doc_id': doc['filename'].split('/')[-1].replace('.pdf', ''),
            'work': work_m.group(1) if work_m else None,
            'client': client_m.group(1) if client_m else None,
            'category': cat_m.group(1) if cat_m else None,
            'val_raw': val_m.group(1) if val_m else None,
            'completion': comp_m.group(1) if comp_m else None,
            'lead': lead_m.group(1) if lead_m else None,
        })

    print(f"Successfully extracted work from CCC: {sum(1 for p in parsed if p['work'] is not None)}/{len(parsed)}")
    print("Sample parsed CCC:")
    print(json.dumps(parsed[:5], indent=2))

if __name__ == '__main__':
    test_extract()
