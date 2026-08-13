import os
import json
import sqlite3
import re
import glob
import argparse
import pandas as pd
from typing import Dict, Any, Optional, List
import pymupdf

DB_FILE = "construction_archive.db"
EXTRACTED_FILE = "extracted_database.json"

from extract_entities import clean_client_name, clean_employee_name, normalize_date, normalize_currency


def init_db(conn: sqlite3.Connection):
    cursor = conn.cursor()

    cursor.execute("CREATE TABLE IF NOT EXISTS clients (client_id INTEGER PRIMARY KEY AUTOINCREMENT, client_name TEXT UNIQUE NOT NULL);")
    cursor.execute("CREATE TABLE IF NOT EXISTS employees (employee_id INTEGER PRIMARY KEY AUTOINCREMENT, employee_name TEXT UNIQUE NOT NULL);")
    cursor.execute("""CREATE TABLE IF NOT EXISTS projects (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        pkg_num INTEGER UNIQUE NOT NULL,
        project_name TEXT UNIQUE NOT NULL,
        client_id INTEGER REFERENCES clients(client_id),
        employee_id INTEGER REFERENCES employees(employee_id),
        contract_value INTEGER,
        completion_date TEXT,
        completion_year INTEGER,
        category TEXT
    );""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS certifications (
        cert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER REFERENCES employees(employee_id),
        cert_type TEXT,
        issue_date TEXT
    );""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        doc_type TEXT,
        project_id INTEGER REFERENCES projects(project_id),
        client_id INTEGER REFERENCES clients(client_id),
        has_reference_letter INTEGER DEFAULT 0
    );""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS financial_billing (
        billing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER REFERENCES clients(client_id),
        invoiced_value INTEGER,
        paid_value INTEGER,
        due_value INTEGER,
        collection_pct REAL
    );""")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(client_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(employee_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(project_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_employee ON projects(employee_id);")

    conn.commit()


def find_matching_files(docs_dir: str, subfolder_name: str, ext: str = ".pdf") -> List[str]:
    matches = []
    for root, dirs, files in os.walk(docs_dir):
        rel = os.path.relpath(root, docs_dir).replace("\\", "/")
        if subfolder_name.lower() in rel.lower() or subfolder_name.lower() in root.lower():
            for f in files:
                if f.endswith(ext):
                    matches.append(os.path.join(root, f))
    if not matches:
        for root, dirs, files in os.walk(docs_dir):
            for f in files:
                if subfolder_name.lower() in f.lower() and f.endswith(ext):
                    matches.append(os.path.join(root, f))
    return sorted(matches)


def find_ageing_file(docs_dir: str) -> Optional[str]:
    for root, dirs, files in os.walk(docs_dir):
        for f in files:
            if "ageing" in f.lower() and f.endswith(".xlsx"):
                return os.path.join(root, f)
    default_path = os.path.join(docs_dir, "workbooks", "Receivables_Ageing.xlsx")
    return default_path if os.path.exists(default_path) else None


def build_database(docs_dir: str = "documents"):
    if not os.path.exists(EXTRACTED_FILE):
        print(f"Error: {EXTRACTED_FILE} not found. Please run extract_entities.py first.")
        return

    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        extracted = json.load(f)

    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cursor = conn.cursor()

    clients_map = {}
    employees_map = {}

    def get_client_id(c_name):
        if not c_name:
            return None
        c_clean = clean_client_name(c_name)
        if not c_clean:
            return None
        if c_clean not in clients_map:
            cursor.execute("INSERT INTO clients (client_name) VALUES (?);", (c_clean,))
            clients_map[c_clean] = cursor.lastrowid
        return clients_map[c_clean]

    def get_emp_id(e_name):
        if not e_name:
            return None
        e_clean = clean_employee_name(e_name)
        if not e_clean:
            return None
        if e_clean not in employees_map:
            cursor.execute("INSERT INTO employees (employee_name) VALUES (?);", (e_clean,))
            employees_map[e_clean] = cursor.lastrowid
        return employees_map[e_clean]

    # 1. Parse all company completion certificates for authoritative projects
    ccc_files = find_matching_files(docs_dir, "company_completion_certificate", ".pdf")
    projects_pkg_map = {}

    for f in ccc_files:
        d = pymupdf.open(f)
        txt = "\n".join([p.get_text() for p in d])
        d.close()

        m_pkg = re.search(r"Pkg-(\d+)", txt, re.IGNORECASE)
        pkg_num = int(m_pkg.group(1)) if m_pkg else None

        m_pname = re.search(
            r"(?:Work|Project Name)\s+(.*?)(?=\n(?:Client|Scope|Work Category|Category|Contract|Completion|Project Manager|Project Lead)\b|\n[A-Z]|\n\n|$)",
            txt,
            re.DOTALL,
        )
        pname = m_pname.group(1).replace("\n", " ").strip() if m_pname else f"Project_Pkg_{pkg_num}"

        m_client = re.search(
            r"Client\s+(.*?)(?=\n(?:Category|Scope|Executed Value|Contract|Completion|Project Lead|Project Manager)\b|\n[A-Z]|\n\n|$)",
            txt,
            re.DOTALL,
        )
        cname = m_client.group(1).replace("\n", " ").strip() if m_client else None
        c_id = get_client_id(cname)

        m_cat = re.search(
            r"(?:Work Category|Category)\s+(.*?)(?=\n(?:Contract Value|Executed Value|Completion|Project Lead|Project Manager)\b|\n[A-Z]|\n\n|$)",
            txt,
            re.DOTALL,
        )
        cat = m_cat.group(1).replace("\n", " ").strip() if m_cat else None

        m_val = re.search(
            r"(?:Executed Value|Contract Value)\s+(INR\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|Rs\.\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|[\d\.,]+\s+Crore|[\d\.,]+\s+Lakh)",
            txt,
            re.IGNORECASE,
        )
        val_raw = m_val.group(1).strip() if m_val else None
        val_inr = normalize_currency(val_raw)

        m_date = re.search(
            r"(?:Completion Date|Completion)\s+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            txt,
        )
        cdate = normalize_date(m_date.group(1).strip()) if m_date else None
        cyear = int(cdate[:4]) if cdate and len(cdate) >= 4 and cdate[:4].isdigit() else None

        m_mgr = re.search(
            r"(?:Project Lead|Project Manager|Contractor\'s Project Manager|supervised on the contractor\'s side by)[:\s]*\n?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)",
            txt,
        )
        mgr_name = m_mgr.group(1).strip() if m_mgr else None
        e_id = get_emp_id(mgr_name)

        cursor.execute(
            """
            INSERT INTO projects (pkg_num, project_name, client_id, employee_id, contract_value, completion_date, completion_year, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
            (pkg_num, pname, c_id, e_id, val_inr, cdate, cyear, cat),
        )

        projects_pkg_map[pkg_num] = cursor.lastrowid

    # 2. Map Certifications
    cert_count = 0
    for doc_id, doc in extracted.items():
        if doc.get("doc_type") == "personnel_certificate" and doc.get("certification_type"):
            e_name = doc.get("employee_name")
            e_id = get_emp_id(e_name)
            cert_type = doc.get("certification_type")
            issue_date = doc.get("certification_date")
            if e_id:
                cursor.execute(
                    "INSERT INTO certifications (employee_id, cert_type, issue_date) VALUES (?, ?, ?);",
                    (e_id, cert_type, issue_date),
                )
                cert_count += 1

    # 3. Map Reference Letters & Documents
    ref_pkg_nums = set()
    ref_files = find_matching_files(docs_dir, "reference_letter", ".pdf")
    for f in ref_files:
        d = pymupdf.open(f)
        txt = "\n".join([p.get_text() for p in d])
        d.close()
        m_pkg = re.search(r"Pkg-(\d+)", txt, re.IGNORECASE)
        if m_pkg:
            ref_pkg_nums.add(int(m_pkg.group(1)))

    doc_count = 0
    for doc_id, doc in extracted.items():
        doc_type = doc.get("doc_type")
        cname = doc.get("client_name")
        c_id = get_client_id(cname)

        pname = doc.get("project_name")
        pkg_num = None
        if pname:
            m_pkg = re.search(r"Pkg-(\d+)", pname, re.IGNORECASE)
            if m_pkg:
                pkg_num = int(m_pkg.group(1))

        p_id = projects_pkg_map.get(pkg_num) if pkg_num else None
        has_ref = 1 if (doc_type == "reference_letter" or (pkg_num and pkg_num in ref_pkg_nums)) else 0

        cursor.execute(
            "INSERT INTO documents (doc_id, doc_type, project_id, client_id, has_reference_letter) VALUES (?, ?, ?, ?, ?);",
            (doc_id, doc_type, p_id, c_id, has_ref),
        )
        doc_count += 1

    # 4. Populate financial_billing from Receivables_Ageing.xlsx
    ageing_file = find_ageing_file(docs_dir)
    if ageing_file and os.path.exists(ageing_file):
        try:
            df_age = pd.read_excel(ageing_file, sheet_name="AR Ageing")
            for client_raw, grp in df_age.groupby("Client"):
                c_norm = clean_client_name(client_raw)
                c_id = clients_map.get(c_norm) if c_norm else None
                if c_id:
                    tot_invoiced = int(round(grp["Invoiced (INR)"].sum()))
                    tot_paid = int(round(grp[grp["Status"] == "paid"]["Invoiced (INR)"].sum()))
                    tot_due = int(round(grp[grp["Status"] == "due"]["Invoiced (INR)"].sum()))
                    pct = round((tot_paid / tot_invoiced) * 100.0, 2) if tot_invoiced > 0 else 0.0

                    cursor.execute(
                        """
                        INSERT INTO financial_billing (client_id, invoiced_value, paid_value, due_value, collection_pct)
                        VALUES (?, ?, ?, ?, ?);
                    """,
                        (c_id, tot_invoiced, tot_paid, tot_due, pct),
                    )
        except Exception as e:
            print(f"Warning: Financial billing parsing error: {e}")

    conn.commit()
    conn.close()

    print("\nPhase 4 Database Population Summary:")
    print(f"- Clients populated: {len(clients_map)}")
    print(f"- Employees populated: {len(employees_map)}")
    print(f"- Projects populated: {len(projects_pkg_map)}")
    print(f"- Certifications populated: {cert_count}")
    print(f"- Documents populated: {doc_count}")
    print(f"Phase 4 Complete! SQLite database created at {DB_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build SQLite database from extracted entities")
    parser.add_argument("--docs", default="documents", help="Path to documents directory")
    args = parser.parse_args()

    build_database(args.docs)


