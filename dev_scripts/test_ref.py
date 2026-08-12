import json
import re

def test_ref():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)

    ref_docs = {k: v for k, v in corpus.items() if v['doc_type'] == 'reference_letter'}

    parsed = []
    for doc_id, doc in ref_docs.items():
        text = doc['content']
        
        # Project Name
        pm = (re.search(r'Project Name\s+(.*?)(?=\s+(?:Scope|Nature|Contract|Date|$))', text) or
              re.search(r'work\s+([A-Za-z0-9\s\-]+?)\s*\(', text) or
              re.search(r'Work Executed\s+([A-Za-z0-9\s\-]+?)\s+(?:Value|Completed)', text) or
              re.search(r'Subject: Performance of M/s National Infrastructure Corp\. Ltd\.\s+([A-Za-z0-9\s\-]+)', text))
        
        # Client Name
        cm = (re.search(r'^(.*?)\s+(?:Letter of Recommendation|government|PSU CLIENT|PRIVATE CLIENT|Ref:)', text, re.MULTILINE) or
              re.search(r'For\s+(.*?)\s+DOC-REF', text) or
              re.search(r'Contact for Verification\s+[A-Za-z\s]+\s+([A-Za-z0-9\s,\.]+?)\s+DOC-REF', text))

        parsed.append({
            'doc_id': doc_id,
            'project_name': pm.group(1).strip() if pm else None,
            'client_name': cm.group(1).strip() if cm else None
        })

    print(f"Total reference letters: {len(ref_docs)}")
    print(f"Matched projects: {sum(1 for p in parsed if p['project_name'])}/{len(parsed)}")
    print(f"Matched clients: {sum(1 for p in parsed if p['client_name'])}/{len(parsed)}")

    unmatched_proj = [p for p in parsed if not p['project_name']]
    if unmatched_proj:
        print("\nSample unmatched ref projects:")
        for p in unmatched_proj[:3]:
            print(p['doc_id'], ref_docs[p['doc_id']]['content'][:200])

if __name__ == '__main__':
    test_ref()
