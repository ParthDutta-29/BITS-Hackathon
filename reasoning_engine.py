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

ALIAS_CLIENTS = {
    "trishakti": "Trishakti Power Generation Corporation",
    "mahanadi": "Mahanadi Steel Corporation",
    "subarnarekha": "Subarnarekha Valley Corporation",
    "meridian": "Meridian Constructors & Co.",
    "peninsular": "Peninsular Petroleum Corporation",
    "suvarna": "Suvarna Projects Limited",
    "lakshya": "Lakshya Engineering & Construction",
    "mega": "Mega Infrastructure Authority",
    "arunodaya": "Arunodaya Infrastructure",
    "gujarat pw": "Public Works Department, Govt of Gujarat",
    "bengal pw": "Public Works Department, Govt of West Bengal",
    "maharashtra pw": "Public Works Department, Govt of Maharashtra",
    "mah pwd": "Public Works Department, Govt of Maharashtra",
    "tn pw": "Public Works Department, Govt of Tamil Nadu",
    "central works": "Central Works & Buildings Bureau",
    "phed odisha": "Public Health Engineering Dept, Govt of Odisha",
    "odisha phed": "Public Health Engineering Dept, Govt of Odisha",
    "pheg gujarat": "Public Health Engineering Dept, Govt of Gujarat",
    "phed gujarat": "Public Health Engineering Dept, Govt of Gujarat",
    "neda": "National Expressway Development Authority",
}



def text_to_crore_number(qtext: str) -> Optional[int]:
    # Match numeric crore: 23 Cr, 23.0 Cr, 73 crore
    m = re.search(r"(?:INR\s*|Rs\.?\s*)?([\d]+(?:\.[\d]+)?)\s*(?:cr|crore)", qtext, re.IGNORECASE)
    if m:
        try:
            return int(round(float(m.group(1)) * 10000000))
        except ValueError:
            pass

    # Match word crore: twenty-three crore, forty-three crore
    m = re.search(r"\b([a-z]+(?:-[a-z]+)?)\s+crore\b", qtext, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
        if word in WORD_NUMS:
            return WORD_NUMS[word] * 10000000
        parts = word.split("-")
        val = sum(WORD_NUMS.get(p, 0) for p in parts)
        if val > 0:
            return val * 10000000

    # Match word mark/cutoff/limit: e.g. twenty-three crore mark
    m = re.search(r"\b([a-z]+(?:-[a-z]+)?)\s+(?:mark|cutoff|limit|threshold|target)\b", qtext, re.IGNORECASE)
    if m:
        word = m.group(1).lower()
        if word in WORD_NUMS:
            return WORD_NUMS[word] * 10000000

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


def extract_package(qtext: str) -> str:
    m = re.search(r"pkg[-_\s]*(\d+)|package\s*(\d+)", qtext, re.IGNORECASE)
    if m:
        val = m.group(1) or m.group(2)
        return f"%Pkg-{val}%"
    return ""


def extract_client(qtext: str, known_clients: List[str]) -> str:
    q_lower = qtext.lower()

    # 1. Direct match on known database clients (sorted longest first)
    sorted_clients = sorted(known_clients, key=lambda x: len(x), reverse=True)
    for c in sorted_clients:
        if c.lower() in q_lower:
            return c

    # 2. Alias mapping lookup
    for kw, target_c in ALIAS_CLIENTS.items():
        if kw in q_lower:
            return target_c

    # 3. Package-first resolution if package number is specified
    pkg_pat = extract_package(qtext)
    if pkg_pat:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT c.client_name FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE p.project_name LIKE ?;", (pkg_pat,))
        r = c.fetchone()
        conn.close()
        if r:
            return r[0]


    if "irrigation" in q_lower or "waterways" in q_lower:
        if "west bengal" in q_lower or "bengal" in q_lower:
            return "Irrigation & Waterways Dept, Govt of West Bengal"
        if "uttar pradesh" in q_lower or "up " in q_lower or "u.p." in q_lower:
            return "Irrigation & Waterways Dept, Govt of Uttar Pradesh"
        if "rajasthan" in q_lower:
            return "Irrigation & Waterways Dept, Govt of Rajasthan"

    if "public health" in q_lower or "phe" in q_lower or "phed" in q_lower:
        if "gujarat" in q_lower:
            return "Public Health Engineering Dept, Govt of Gujarat"
        if "odisha" in q_lower:
            return "Public Health Engineering Dept, Govt of Odisha"

    if "public works" in q_lower or "pwd" in q_lower or " pw" in q_lower:
        if "west bengal" in q_lower or "bengal" in q_lower:
            return "Public Works Department, Govt of West Bengal"
        if "maharashtra" in q_lower:
            return "Public Works Department, Govt of Maharashtra"
        if "gujarat" in q_lower:
            return "Public Works Department, Govt of Gujarat"
        if "tamil nadu" in q_lower:
            return "Public Works Department, Govt of Tamil Nadu"

    if "jal nigam" in q_lower:
        if "jharkhand" in q_lower:
            return "Jal Nigam, Jharkhand"
        if "gujarat" in q_lower:
            return "Jal Nigam, Gujarat"
        if "uttar pradesh" in q_lower or "up " in q_lower:
            return "Jal Nigam, Uttar Pradesh"

    if "municipal" in q_lower:
        if "jharkhand" in q_lower:
            return "Jharkhand Municipal Corporation"
        if "maharashtra" in q_lower:
            return "Maharashtra Municipal Corporation"
        if "gujarat" in q_lower:
            return "Gujarat Municipal Corporation"
        if "tamil nadu" in q_lower:
            return "Tamil Nadu Municipal Corporation"

    sorted_clients = sorted(known_clients, key=lambda x: len(x), reverse=True)
    for c in sorted_clients:
        if c.lower() in q_lower:
            return c

    # Match state names for State Authority clients
    states = ["madhya pradesh", "uttar pradesh", "west bengal", "maharashtra", "tamil nadu", "jharkhand", "rajasthan", "gujarat", "odisha", "delhi"]
    for st in states:
        if st in q_lower:
            for c in known_clients:
                if st in c.lower():
                    return c

    return ""




def extract_employee(qtext: str, known_employees: List[str]) -> str:
    q_lower = qtext.lower()
    sorted_employees = sorted(known_employees, key=lambda x: len(x), reverse=True)
    for e in sorted_employees:
        if e.lower() in q_lower:
            return e
    for e in sorted_employees:
        first_name = e.split()[0]
        if len(first_name) >= 4 and f" {first_name.lower()} " in f" {q_lower} ":
            return e
    return ""


def generate_sql_rule(question: str, answer_type: str) -> str:
    q_lower = question.lower()
    known_clients, known_employees = get_db_entities()

    client_name = extract_client(question, known_clients)
    emp_name = extract_employee(question, known_employees)
    pkg_pat = extract_package(question)

    # 1. Combined value for Employee + Client (only for money answer types when asking for specific employee's work for that client)
    if answer_type == "money" and emp_name and client_name and re.search(r"\b(?:he|she)\s+(?:has\s+)?(?:done|led|delivered|completed|finished)\b|\b(?:her|his)\s+assignments\b", q_lower):
        return f"""
        SELECT SUM(p.contract_value)
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        JOIN employees e ON p.employee_id = e.employee_id
        WHERE c.client_name LIKE '%{client_name}%'
          AND e.employee_name LIKE '%{emp_name}%';
        """





    # 2. Absence / Unreferenced Count
    if ("no " in q_lower or "lack" in q_lower or "without" in q_lower or "missing" in q_lower or "unreferenced" in q_lower) and ("reference" in q_lower or "letter" in q_lower or "testimonial" in q_lower):
        if client_name and emp_name:
            return f"""
            SELECT COUNT(*)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            JOIN employees e ON p.employee_id = e.employee_id
            LEFT JOIN documents d ON d.project_id = p.project_id AND d.doc_type = 'reference_letter'
            WHERE c.client_name LIKE '%{client_name}%'
              AND e.employee_name LIKE '%{emp_name}%'
              AND (d.doc_id IS NULL OR d.has_reference_letter = 0);
            """
        elif client_name:
            return f"""
            SELECT COUNT(*)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            LEFT JOIN documents d ON d.project_id = p.project_id AND d.doc_type = 'reference_letter'
            WHERE c.client_name LIKE '%{client_name}%'
              AND (d.doc_id IS NULL OR d.has_reference_letter = 0);
            """

    # 3. Pending / Due Amount
    if "pending amount" in q_lower or "remaining balance" in q_lower or "due" in q_lower:
        if client_name:
            return f"""
            SELECT fb.due_value
            FROM financial_billing fb
            JOIN clients c ON fb.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 4. Category vs Category Difference
    if ("versus" in q_lower or "against the" in q_lower or "subtract" in q_lower or "difference between the" in q_lower) and ("scopes" in q_lower or "portfolio" in q_lower or "spend" in q_lower or "totals" in q_lower or "epc" in q_lower):
        cats = []
        for cat_name in ["Large Bridges", "Water Treatment", "Irrigation", "Sewerage Drainage", "Expressways", "Roads Highways", "Industrial EPC", "Small Buildings", "Buildings"]:
            if cat_name.lower() in q_lower or any(w in q_lower for w in cat_name.lower().split()):
                cats.append(cat_name)
        if len(cats) >= 2 and client_name:
            return f"""
            SELECT ABS(
                COALESCE((SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%' AND p.category LIKE '%{cats[0]}%'), 0) -
                COALESCE((SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%' AND p.category LIKE '%{cats[1]}%'), 0)
            );
            """

    # 5. Date Span in Days
    if answer_type == "days" or "days passed" in q_lower or "days elapsed" in q_lower or "interval" in q_lower or "real elapsed period" in q_lower:
        if pkg_pat:
            return f"""
            SELECT CAST(ROUND(JULIANDAY(p.completion_date) - JULIANDAY(cert.issue_date)) AS INTEGER)
            FROM projects p
            JOIN employees e ON p.employee_id = e.employee_id
            JOIN certifications cert ON cert.employee_id = e.employee_id
            WHERE p.project_name LIKE '{pkg_pat}' AND cert.cert_type = 'PMP';
            """
        elif emp_name:
            return f"""
            SELECT CAST(ROUND(JULIANDAY(p.completion_date) - JULIANDAY(cert.issue_date)) AS INTEGER)
            FROM projects p
            JOIN employees e ON p.employee_id = e.employee_id
            JOIN certifications cert ON cert.employee_id = e.employee_id
            WHERE e.employee_name LIKE '%{emp_name}%' AND cert.cert_type = 'PMP'
            LIMIT 1;
            """

    # 6. Average Work Size
    if "average size" in q_lower or "mean size" in q_lower or "average work" in q_lower or "rupee mean" in q_lower or "mean volume" in q_lower:
        if client_name:
            return f"""
            SELECT CAST(ROUND(AVG(p.contract_value)) AS INTEGER)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 7. Distinct Categories
    if "categories" in q_lower or "classifications" in q_lower or "distinct work" in q_lower:
        if emp_name:
            return f"""
            SELECT COUNT(DISTINCT p.category)
            FROM projects p
            JOIN employees e ON p.employee_id = e.employee_id
            WHERE e.employee_name LIKE '%{emp_name}%';
            """

    # 8. Referenced Percentage Share
    if answer_type == "percent" and ("share" in q_lower or "divided by" in q_lower or "testimonial" in q_lower or "reference letter" in q_lower or "client approval" in q_lower):
        if client_name:
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

    # 9. Financial Collection Percentage
    if answer_type == "percent" and ("collection" in q_lower or "billed" in q_lower or "collected" in q_lower or "cleared" in q_lower):
        if client_name:
            return f"""
            SELECT fb.collection_pct
            FROM financial_billing fb
            JOIN clients c ON fb.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 10. Financial Shortfall / Gap (Awarded - Invoiced)
    if "shortfall" in q_lower or "gap" in q_lower or "invoiced" in q_lower:
        if client_name:
            return f"""
            SELECT SUM(p.contract_value) - COALESCE(fb.invoiced_value, 0)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            LEFT JOIN financial_billing fb ON fb.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 11. Exclusion Aggregate
    if "excluding" in q_lower or "exclude" in q_lower or "remove" in q_lower or "minus" in q_lower:
        m_ex = re.search(r"(?:excluding|exclude|remove|minus)\s+(?:the\s+)?([A-Za-z0-9\s]+?)(?:[,\u2014\–\-]|what|side|segment|$)", question, re.IGNORECASE)
        ex_str = m_ex.group(1).strip() if m_ex else ""
        if client_name:
            return f"""
            SELECT SUM(p.contract_value)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%'
              AND p.category NOT LIKE '%{ex_str}%';
            """

    # 12. Target Gap Threshold (Target - Total)
    if "target" in q_lower or "how much more" in q_lower or "need to clear" in q_lower or "bar" in q_lower:
        t_val = text_to_crore_number(question) or 200000000
        if client_name:
            return f"""
            SELECT {t_val} - SUM(p.contract_value)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%';
            """

    # 13. Rank Value Difference (1st - 2nd Largest)
    if "largest" in q_lower and ("second" in q_lower or "exceed" in q_lower or "difference" in q_lower):
        if client_name:
            return f"""
            WITH Ranked AS (
                SELECT contract_value, ROW_NUMBER() OVER (ORDER BY contract_value DESC) as rk
                FROM projects p
                JOIN clients c ON p.client_id = c.client_id
                WHERE c.client_name LIKE '%{client_name}%'
            )
            SELECT (SELECT contract_value FROM Ranked WHERE rk = 1) - (SELECT contract_value FROM Ranked WHERE rk = 2);
            """

    # 14. Year-over-Year Difference
    m_years = re.findall(r"\b(20\d{2})\b", question)
    if len(m_years) >= 2 and ("difference" in q_lower or "between" in q_lower or "moved" in q_lower or "vs" in q_lower or "shifted" in q_lower or "variance" in q_lower):
        y1, y2 = int(m_years[0]), int(m_years[1])
        if client_name:
            return f"""
            SELECT ABS(
                COALESCE((SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%' AND p.completion_year = {y1}), 0) -
                COALESCE((SELECT SUM(contract_value) FROM projects p JOIN clients c ON p.client_id = c.client_id WHERE c.client_name LIKE '%{client_name}%' AND p.completion_year = {y2}), 0)
            );
            """

    # 15. Temporal Chain (completed after cert date)
    if "after that date" in q_lower or "completed after" in q_lower or "wrapped up after" in q_lower or "finished after" in q_lower or "reached completion after" in q_lower:
        if emp_name:
            return f"""
            SELECT SUM(p.contract_value)
            FROM projects p
            JOIN employees e ON p.employee_id = e.employee_id
            JOIN certifications cert ON cert.employee_id = e.employee_id
            WHERE e.employee_name LIKE '%{emp_name}%'
              AND cert.cert_type = 'PMP'
              AND p.completion_date > cert.issue_date;
            """

    # 16. Threshold Aggregate
    threshold_val = text_to_crore_number(question)
    if threshold_val is not None and ("clear" in q_lower or "crossing" in q_lower or "hitting" in q_lower or "cutoff" in q_lower or "exceed" in q_lower or "mark" in q_lower or "limit" in q_lower or "threshold" in q_lower or "bar" in q_lower):
        if client_name:
            return f"""
            SELECT SUM(p.contract_value)
            FROM projects p
            JOIN clients c ON p.client_id = c.client_id
            WHERE c.client_name LIKE '%{client_name}%'
              AND p.contract_value >= {threshold_val};
            """

    # 17. Default Fallback query per client
    if client_name:
        return f"""
        SELECT SUM(p.contract_value)
        FROM projects p
        JOIN clients c ON p.client_id = c.client_id
        WHERE c.client_name LIKE '%{client_name}%';
        """

    return "SELECT COUNT(*) FROM projects;"




def execute_and_format(sql: str, answer_type: str) -> Any:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(sql)
    row = cursor.fetchone()
    conn.close()

    if not row or row[0] is None:
        return 0 if answer_type != "percent" else "0.00"

    raw_val = row[0]
    if answer_type in ["money", "count", "days"]:
        return int(round(float(raw_val)))
    elif answer_type == "percent":
        return f"{float(raw_val):.2f}"
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

