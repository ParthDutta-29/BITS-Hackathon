import sqlite3
import json
import re

def test_samples():
    conn = sqlite3.connect('construction_archive.db')
    cursor = conn.cursor()

    with open('sample_questions.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    questions = data.get('questions', [])
    print(f"Loaded {len(questions)} sample questions.")

    for q in questions:
        qid = q['qid']
        qtext = q['question']
        atype = q['answer_type']
        expected = q['answer']
        shape = q.get('shape')

        print(f"\n--- [{qid}] ({shape}, {atype}) ---")
        print(f"Q: {qtext}")
        print(f"Expected Answer: {expected}")

if __name__ == '__main__':
    test_samples()
