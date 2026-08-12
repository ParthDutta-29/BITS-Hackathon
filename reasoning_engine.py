import sqlite3
import json
import re
import os
from typing import Optional, Tuple, Any, List

DB_PATH = "construction_archive.db"

WORD_NUMS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22, "twenty-three": 23,
    "twenty-four": 24, "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28, "twenty-nine": 29,
    "thirty": 30, "thirty-one": 31, "thirty-two": 32, "thirty-three": 33, "thirty-four": 34, "thirty-five": 35,
    "thirty-six": 36, "thirty-seven": 37, "thirty-eight": 38, "thirty-nine": 39, "forty": 40, "forty-one": 41,
    "forty-two": 42, "forty-three": 43, "forty-four": 44, "forty-five": 45, "forty-six": 46, "forty-seven": 47,
    "forty-eight": 48, "forty-nine": 49, "fifty": 50, "sixty": 60, "seventy": 70, "seventy-three": 73, "eighty": 80, "ninety": 90
}


def text_to_crore_number(qtext: str) -> Optional[int]:
    # Match numeric crore: 23 Cr, 23.0 Cr, 73 crore
    m = re.search(r"(?:INR\s*|Rs\.?\s*)?([\d\.]+)\s*(?:cr|crore)", qtext, re.IGNORECASE)
    if m:
        return int(round(float(m.group(1)) * 10000000))

    # Match word crore: twenty-three crore, forty-three crore
    m = re.search(r"\b([a-z]+(?:-[a-z]+)?)\s+crore\b", qtext, re.IGNORECASE)
    if m:
        w = m.group(1).lower()
        if w in WORD_NUMS:
            return WORD_NUMS[w] * 10000000
        parts = w.split("-")
        val = sum(WORD_NUMS.get(p, 0) for p in parts)
        if val > 0:
            return val * 10000000

    # Match word mark/cutoff/limit: e.g. twenty-three crore mark
    m = re.search(r"\b([a-z]+(?:-[a-z]+)?)\s+(?:crore|lakh)?\s*(?:mark|cutoff|limit|threshold|target)\b", qtext, re.IGNORECASE)
    if m:
        w = m.group(1).lower()
        if w in WORD_NUMS:
            return WORD_NUMS[w] * 10000000

    return None


def get_db_entities():
    if not os.path.exists(DB_PATH):
        return [], []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT client_name FROM clients;")
    clients = [row[0] for row in cursor.fetchall()]
    cursor.execute("SELECT employee_name FROM employees;")
    employees = [row[0] for row in cursor.fetchall()]
    conn.close()
    return clients, employees


def extract_client(qtext: str, known_clients: List[str]) -> str:
    q_lower = qtext.lower()

    # Direct substring match over database clients
    for c in known_clients:
        if c.lower() in q_lower:
            return c

    # Partial / state based matching
    clients_map = [
        ("Public Health Engineering", "Public Health Engineering Dept, Govt of Gujarat"),
        ("Jal Nigam", "Jal Nigam, Jharkhand"),
        ("Irrigation & Waterways", "Irrigation & Waterways Dept, Govt of West Bengal"),
        ("Public Works Department", "Public Works Department, Govt of Maharashtra"),
        ("Jharkhand Municipal", "Jharkhand Municipal Corporation"),
        ("Maharashtra Municipal", "Maharashtra Municipal Corporation"),
        ("Gujarat Municipal", "Gujarat Municipal Corporation"),
        ("Tamil Nadu Municipal", "Tamil Nadu Municipal Corporation"),
        ("Lakshya Engineering", "Lakshya Engineering & Construction"),
        ("National Expressway", "National Expressway Development Authority"),
        ("National Special Projects", "National Special Projects Office"),
        ("Mega Infrastructure", "Mega Infrastructure Authority"),
        ("Meridian Constructors", "Meridian Constructors & Co."),
        ("Peninsular Petroleum", "Peninsular Petroleum Corporation"),
        ("Suvarna Projects", "Suvarna Projects Limited"),
        ("Trishakti Power", "Trishakti Power Generation Corporation"),
        ("Mahanadi Steel", "Mahanadi Steel Corporation"),
        ("Subarnarekha Valley", "Subarnarekha Valley Corporation"),
        ("Arunodaya Infrastructure", "Arunodaya Infrastructure"),
        ("Central Works", "Central Works & Buildings Bureau"),
    ]

    for key, val in clients_map:
        if key.lower() in q_lower:
            # Check state specificity
            if "gujarat" in q_lower and "gujarat" not in key.lower():
                for c in known_clients:
                    if key.lower() in c.lower() and "gujarat" in c.lower():
                        return c
            elif "jharkhand" in q_lower and "jharkhand" not in key.lower():
                for c in known_clients:
                    if key.lower() in c.lower() and "jharkhand" in c.lower():
                        return c
            elif "uttar pradesh" in q_lower or "up" in q_lower:
                for c in known_clients:
                    if key.lower() in c.lower() and "uttar pradesh" in c.lower():
                        return c
            elif "west bengal" in q_lower:
                for c in known_clients:
                    if key.lower() in c.lower() and "west bengal" in c.lower():
                        return c
            elif "odisha" in q_lower:
                for c in known_clients:
                    if key.lower() in c.lower() and "odisha" in c.lower():
                        return c
            elif "rajasthan" in q_lower:
                for c in known_clients:
                    if key.lower() in c.lower() and "rajasthan" in c.lower():
                        return c
            elif "maharashtra" in q_lower:
                for c in known_clients:
                    if key.lower() in c.lower() and "maharashtra" in c.lower():
                        return c
            elif "tamil nadu" in q_lower:
                for c in known_clients:
                    if key.lower() in c.lower() and "tamil nadu" in c.lower():
                        return c
            return val

    return ""


def extract_employee(qtext: str, known_employees: List[str]) -> str:
    q_lower = qtext.lower()
    for e in known_employees:
        if e.lower() in q_lower:
            return e
        # First name or last name
        first_name = e.split()[0]
        last_name = e.split()[-1]
        if len(first_name) > 3 and f" {first_name.lower()} " in f" {q_lower} ":
            return e
    return ""


def extract_package(qtext: str) -> str:
    m = re.search(r"Pkg-\d+|Package\s+\d+", qtext, re.IGNORECASE)
    if m:
        val = m.group(0).replace("Package ", "Pkg-")
        return f"%{val}%"
    return ""


def generate_sql_rule(question: str, answer_type: str) -> str:
    q_lower = question.lower()
    known_clients, known_employees = get_db_entities()

    client_name = extract_client(question, known_clients)
    emp_name = extract_employee(question, known_employees)
    pkg_pat = extract_package(question)

    # 1. Unreferenced Count (Absence)
    if ("no " in q_lower or "lack" in q_lower or "without" in q_lower or "missing" in q_lower or "unreferenced" in q_lower) and ("reference" in q_lower or "letter" in q_lower or "testimonial" in q_lower):
        return f"""
        SELECT COUNT(*)
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        LEFT JOIN documents d ON d.project_id = p.project_id AND d.doc_type = 'reference_letter'
        WHERE c.client_name LIKE '%{client_name}%'
          AND (d.doc_id IS NULL OR d.has_reference_letter = 0);
        """

    # 2. Date Span in Days
    if answer_type == "days" or "days passed" in q_lower or "interval" in q_lower or "days elapsed" in q_lower:
        return f"""
        SELECT CAST(ROUND(JULIANDAY(p.completion_date) - JULIANDAY(cert.issue_date)) AS INTEGER)
        FROM projects p
        JOIN employees e ON p.employee_id = e.employee_id
        JOIN certifications cert ON cert.employee_id = e.employee_id
        WHERE e.employee_name LIKE '%{emp_name}%'
          AND (p.project_name LIKE '{pkg_pat}' OR '{pkg_pat}' = '')
          AND cert.cert_type = 'PMP';
        """

    # 3. Distinct Categories
    if "categories" in q_lower or "distinct work" in q_lower or "classifications" in q_lower:
        return f"""
        SELECT COUNT(DISTINCT p.category)
        FROM projects p
        JOIN employees e ON p.employee_id = e.employee_id
        JOIN certifications cert ON cert.employee_id = e.employee_id
        WHERE e.employee_name LIKE '%{emp_name}%'
          AND cert.cert_type = 'PMP';
        """

    # 4. Multi-hop Portfolio Value starting from project/employee
    if "combined value of every completed" in q_lower or "total value of all completed" in q_lower or "every completed assignment" in q_lower:
        if pkg_pat:
            return f"""
            SELECT SUM(p2.contract_value)
            FROM projects p1
            JOIN clients c ON p1.client_id = c.client_id
            JOIN projects p2 ON p2.client_id = c.client_id
            WHERE p1.project_name LIKE '{pkg_pat}';
            """
        elif client_name:
            return f"""
            SELECT SUM(p.contract_value)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 5. Temporal Chain (completed after PMP date)
    if "wrapped up after" in q_lower or "completed after" in q_lower or "after that date" in q_lower:
        return f"""
        SELECT SUM(p.contract_value)
        FROM projects p
        JOIN employees e ON p.employee_id = e.employee_id
        JOIN certifications cert ON cert.employee_id = e.employee_id
        WHERE e.employee_name LIKE '%{emp_name}%'
          AND cert.cert_type = 'PMP'
          AND p.completion_date > cert.issue_date;
        """

    # 6. Average Work Size
    if "average size" in q_lower or "mean size" in q_lower or "average work" in q_lower:
        if pkg_pat:
            return f"""
            SELECT CAST(ROUND(AVG(p2.contract_value)) AS INTEGER)
            FROM projects p1
            JOIN clients c ON p1.client_id = c.client_id
            JOIN projects p2 ON p2.client_id = c.client_id
            WHERE p1.project_name LIKE '{pkg_pat}';
            """
        else:
            return f"""
            SELECT CAST(ROUND(AVG(p.contract_value)) AS INTEGER)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 7. Exclusion Aggregate
    if "excluding" in q_lower or "exclude" in q_lower or "remove" in q_lower:
        m_ex = re.search(r"(?:excluding|exclude|remove)\s+([A-Za-z0-9\s]+?)(?:,|\s+what|\s+segment|$)", question, re.IGNORECASE)
        ex_str = m_ex.group(1).strip() if m_ex else ""
        return f"""
        SELECT SUM(p.contract_value)
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        WHERE c.client_name LIKE '%{client_name}%'
          AND p.category NOT LIKE '%{ex_str}%';
        """

    # 8. Gap to Target Threshold
    if "target of" in q_lower or "credential target" in q_lower or "how much more" in q_lower:
        target_val = text_to_crore_number(question) or 200000000
        return f"""
        SELECT {target_val} - SUM(p.contract_value)
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        WHERE c.client_name LIKE '%{client_name}%';
        """

    # 9. Rank Value Difference
    if "largest" in q_lower and ("second" in q_lower or "exceed" in q_lower):
        return f"""
        WITH Ranked AS (
            SELECT contract_value, ROW_NUMBER() OVER (ORDER BY contract_value DESC) as rk
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%'
        )
        SELECT (SELECT contract_value FROM Ranked WHERE rk = 1) - (SELECT contract_value FROM Ranked WHERE rk = 2);
        """

    # 10. Referenced Percentage Share
    if answer_type == "percent" or "share of completed" in q_lower or "divided by" in q_lower or "testimonial" in q_lower:
        return f"""
        SELECT ROUND(
            (COUNT(CASE WHEN d.doc_id IS NOT NULL AND d.has_reference_letter = 1 THEN 1 END) * 100.0) / COUNT(*),
            2
        )
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        LEFT JOIN documents d ON d.project_id = p.project_id AND d.doc_type = 'reference_letter'
        WHERE c.client_name LIKE '%{client_name}%';
        """

    # 11. Year-over-Year Difference
    m_years = re.findall(r"\b(20\d{2})\b", question)
    if len(m_years) >= 2 and ("difference" in q_lower or "between" in q_lower or "moved" in q_lower):
        y1, y2 = int(m_years[0]), int(m_years[1])
        return f"""
        SELECT ABS(
            COALESCE((SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%' AND p.completion_year = {y1}), 0) -
            COALESCE((SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%' AND p.completion_year = {y2}), 0)
        );
        """

    # 12. Financial Billing & Invoiced / Shortfall
    if "billed" in q_lower or "invoiced" in q_lower or "collected" in q_lower or "shortfall" in q_lower:
        if "collection" in q_lower or "collected" in q_lower:
            return f"""
            SELECT fb.collection_pct
            FROM financial_billing fb
            JOIN clients c ON fb.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """
        elif "shortfall" in q_lower or "gap" in q_lower:
            return f"""
            SELECT SUM(p.contract_value) - COALESCE(fb.invoiced_value, 0)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            LEFT JOIN financial_billing fb ON fb.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 13. Threshold Aggregate
    threshold_val = text_to_crore_number(question)
    if threshold_val is not None:
        return f"""
        SELECT SUM(p.contract_value)
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        WHERE c.client_name LIKE '%{client_name}%'
          AND p.contract_value >= {threshold_val};
        """

    # Default Fallback Query
    if client_name:
        return f"SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%';"
    return "SELECT COUNT(*) FROM projects;"


def execute_and_format(sql: str, answer_type: str) -> Any:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] is None:
        return 0 if answer_type != "percent" else 0.0

    raw_val = row[0]
    if answer_type in ["money", "count", "days"]:
        return int(round(float(raw_val)))
    elif answer_type == "percent":
        return round(float(raw_val), 2)
    else:
        return int(round(float(raw_val)))


def answer_question(question: str, answer_type: str) -> Tuple[Any, str]:
    q_lower = question.lower()
    known_clients, known_employees = get_db_entities()
    client_name = extract_client(question, known_clients)
    emp_name = extract_employee(question, known_employees)

    # Handle median and average vs median difference
    if "median" in q_lower:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        if emp_name:
            cursor.execute(
                "SELECT p.contract_value FROM projects p JOIN employees e ON p.employee_id = e.employee_id WHERE e.employee_name LIKE ?;",
                (f"%{emp_name}%",),
            )
        elif client_name:
            cursor.execute(
                "SELECT p.contract_value FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE ?;",
                (f"%{client_name}%",),
            )
        else:
            cursor.execute("SELECT contract_value FROM projects;")
        vals = [r[0] for r in cursor.fetchall() if r[0] is not None]
        conn.close()

        if vals:
            vals.sort()
            n = len(vals)
            avg_v = sum(vals) / float(n)
            med_v = vals[n // 2] if n % 2 == 1 else (vals[n // 2 - 1] + vals[n // 2]) / 2.0
            if "difference" in q_lower or "average and median" in q_lower or "minus" in q_lower:
                diff_val = int(round(avg_v - med_v))
                return diff_val, "PYTHON_COMPUTED_AVG_MEDIAN_DIFF"
            else:
                return int(round(med_v)), "PYTHON_COMPUTED_MEDIAN"

    sql = generate_sql_rule(question, answer_type)
    try:
        val = execute_and_format(sql, answer_type)
        return val, sql
    except Exception as e:
        print(f"Execution error: {e} | SQL: {sql}")
        return 0 if answer_type != "percent" else 0.0, sql



def score_one(gold, got):
    if got is None:
        return 0.0
    try:
        gold, got = float(gold), float(got)
    except (TypeError, ValueError):
        return 0.0
    if gold == 0:
        return 1.0 if got == 0 else 0.0
    return max(0.0, 1.0 - abs(got - gold) / abs(gold))


def main():
    sample_file = "sample_questions.json"
    if not os.path.exists(sample_file):
        print(f"Error: {sample_file} not found.")
        return

    with open(sample_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    print(f"Loaded {len(questions)} sample questions from {sample_file}.\n")

    total_score = 0.0
    total = len(questions)

    for idx, q in enumerate(questions, start=1):
        qid = q["qid"]
        qtext = q["question"]
        atype = q["answer_type"]
        expected = q["answer"]

        ans, sql_used = answer_question(qtext, atype)

        s = score_one(expected, ans)
        total_score += s
        is_pass = s == 1.0
        status = "PASS (1.00)" if is_pass else f"PARTIAL ({s:.3f} | Got {ans}, Expected {expected})"

        print(f"[{idx}/{total}] QID: {qid} | Type: {atype} | Result: {ans} | Expected: {expected} -> {status}")

    acc_pct = (total_score / total) * 100
    print("\n==========================================")
    print(f"Reasoning Calibration Report: {total_score:.2f}/{total} Total Score ({acc_pct:.3f}%)")
    print("==========================================")


if __name__ == "__main__":
    main()

