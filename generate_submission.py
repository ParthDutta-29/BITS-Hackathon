import os
import json
import csv
import subprocess
import sys
import argparse
from tqdm import tqdm
from reasoning_engine import answer_question


def main():
    parser = argparse.ArgumentParser(description="Generate submission CSV from questions JSON")
    parser.add_argument("--questions", default="questions.json", help="Path to questions json file")
    parser.add_argument("--out", default="submission.csv", help="Path to output CSV file")
    args = parser.parse_args()

    questions_file = args.questions
    output_csv = args.out

    if not os.path.exists(questions_file):
        print(f"Error: {questions_file} not found.")
        return

    with open(questions_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    total_q = len(questions)
    print(f"Loaded {total_q} questions from {questions_file}.")

    submission_rows = []

    for q in tqdm(questions, desc="Generating Answers"):
        qid = q.get("qid")
        qtext = q.get("question")
        atype = q.get("answer_type", "count")

        try:
            val, _ = answer_question(qtext, atype)
            if val is None:
                val = 0 if atype != "percent" else 0.0
        except Exception as e:
            print(f"\nWarning: Exception on {qid}: {e}. Defaulting to fallback value.")
            val = 0 if atype != "percent" else 0.0

        if atype == "percent":
            ans_str = f"{float(val):.2f}"
        else:
            ans_str = str(int(round(float(val))))

        submission_rows.append({"question_id": qid, "answer": ans_str})

    print(f"\nWriting {len(submission_rows)} rows to {output_csv}...")
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question_id", "answer"])
        writer.writeheader()
        writer.writerows(submission_rows)

    print(f"Successfully generated {output_csv}!")

    print("\nRunning evaluate.py self-test verification...")
    res = subprocess.run(
        [sys.executable, "evaluate.py", "--self-test"], capture_output=True, text=True
    )
    print(res.stdout)
    if res.stderr:
        print(res.stderr)

    if res.returncode == 0:
        print("Format self-test PASSED successfully!")


if __name__ == "__main__":
    main()
