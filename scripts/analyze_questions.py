"""Analyze the provided question JSONs to extract example reasoning and answer-type mappings.

Usage:
    python scripts/analyze_questions.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def summarize_sample(sample):
    print('Sample questions file:', sample.get('domain'))
    for q in sample.get('questions', []):
        if q.get('qid') == 'HS-IC-0003':
            print('\nExample QID HS-IC-0003 reasoning_steps:')
            for step in q.get('reasoning_steps', []):
                print('-', step)
            print('\nFields implied by steps: Employee name, Certificate type/date, Project name, Date span target')
            break

def map_answer_types(questions):
    mapping = {}
    for q in questions.get('questions', []):
        at = q.get('answer_type')
        if at:
            mapping.setdefault(at, 0)
            mapping[at] += 1
    print('\nAnswer type counts in questions.json:')
    for k, v in mapping.items():
        print(f'- {k}: {v}')
    print('\nExpected formats:')
    print("- money: integer (e.g. 1544600000)")
    print("- count: integer (e.g. 3)")
    print("- days: integer (e.g. 646)")
    print("- percent: float rounded to two decimals (e.g. 33.33)")

def main():
    sample_path = ROOT / 'sample_questions.json'
    questions_path = ROOT / 'questions.json'
    if not sample_path.exists() or not questions_path.exists():
        print('Expected files sample_questions.json and questions.json in repo root')
        return
    sample = load(sample_path)
    questions = load(questions_path)
    summarize_sample(sample)
    map_answer_types(questions)

if __name__ == '__main__':
    main()
