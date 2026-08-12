import os
import json
import csv
import subprocess
import sys
from tqdm import tqdm
from reasoning_engine import answer_question

QUESTIONS_FILE = "questions.json"
OUTPUT_CSV = "submission.csv"


def main():
    if not os.path.exists(QUESTIONS_FILE):
        print(f"Error: {QUESTIONS_FILE} not found.")
        return

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    total_q = len(questions)
    print(f"Loaded {total_q} questions from {QUESTIONS_FILE}.")

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

    print(f"\nWriting {len(submission_rows)} rows to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["question_id", "answer"])
        writer.writeheader()
        writer.writerows(submission_rows)

    print(f"Successfully generated {OUTPUT_CSV}!")

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
