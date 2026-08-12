import os
import json
import sqlite3
import re
from typing import Dict, Any, Optional

DB_FILE = "construction_archive.db"
EXTRACTED_FILE = "extracted_database.json"

from extract_entities import clean_client_name


def clean_name(val: Optional[str]) -> Optional[str]:
    if not val or not isinstance(val, str):
        return None
    cleaned = re.sub(r"\s+", " ", val).strip()
    return cleaned or None


def init_db(conn: sqlite3.Connection):
    cursor = conn.cursor()

    # Clients Table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS clients (
        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT UNIQUE NOT NULL
    );
    """
    )

    # Employees Table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS employees (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_name TEXT UNIQUE NOT NULL
    );
    """
    )

    # Projects Table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS projects (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_name TEXT UNIQUE NOT NULL,
        client_id INTEGER,
        employee_id INTEGER,
        contract_value INTEGER,
        completion_date TEXT,
        category TEXT,
        FOREIGN KEY(client_id) REFERENCES clients(client_id),
        FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
    );
    """
    )

    # Certifications Table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS certifications (
        cert_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        cert_type TEXT,
        issue_date TEXT,
        FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
    );
    """
    )

    # Documents Table
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS documents (
        doc_id TEXT PRIMARY KEY,
        doc_type TEXT,
        project_id INTEGER,
        client_id INTEGER,
        has_reference_letter INTEGER DEFAULT 0,
        FOREIGN KEY(project_id) REFERENCES projects(project_id),
        FOREIGN KEY(client_id) REFERENCES clients(client_id)
    );
    """
    )

    # Indexes
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(client_name);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_employees_name ON employees(employee_name);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(project_name);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_client ON projects(client_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_projects_employee ON projects(employee_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_certifications_employee ON certifications(employee_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id);"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_documents_client ON documents(client_id);"
    )

    conn.commit()


def build_database():
    if not os.path.exists(EXTRACTED_FILE):
        print(
            f"Error: {EXTRACTED_FILE} not found. Please run extract_entities.py first."
        )
        return

    with open(EXTRACTED_FILE, "r", encoding="utf-8") as f:
        extracted = json.load(f)

    # Remove existing DB file for a clean rebuild
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)

    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cursor = conn.cursor()

    # Collect and deduplicate Clients and Employees
    clients_set = set()
    employees_set = set()
    projects_dict: Dict[str, Dict[str, Any]] = {}

    # Identify projects with reference letters
    projects_with_ref_letter = set()
    for doc_id, doc in extracted.items():
        if doc.get("doc_type") == "reference_letter" or doc.get("has_reference_letter"):
            p_name = clean_name(doc.get("project_name"))
            if p_name:
                projects_with_ref_letter.add(p_name)

    # Process company_completion_certificate documents first for authoritative metadata
    for doc_id, doc in extracted.items():
        if doc.get("doc_type") != "company_completion_certificate":
            continue
        c_name = clean_client_name(doc.get("client_name"))
        emp_name = clean_name(doc.get("employee_name"))
        p_name = clean_name(doc.get("project_name"))

        if c_name:
            clients_set.add(c_name)
        if emp_name:
            employees_set.add(emp_name)

        if p_name:
            projects_dict[p_name] = {
                "client_name": c_name,
                "employee_name": emp_name,
                "contract_value": doc.get("contract_value_rupees"),
                "completion_date": doc.get("completion_date"),
                "category": doc.get("project_category"),
            }

    # Process remaining documents without overwriting locked fields
    for doc_id, doc in extracted.items():
        if doc.get("doc_type") == "company_completion_certificate":
            continue
        c_name = clean_client_name(doc.get("client_name"))
        emp_name = clean_name(doc.get("employee_name"))
        p_name = clean_name(doc.get("project_name"))

        if c_name:
            clients_set.add(c_name)
        if emp_name:
            employees_set.add(emp_name)

        if p_name:
            if p_name not in projects_dict:
                projects_dict[p_name] = {
                    "client_name": c_name,
                    "employee_name": emp_name,
                    "contract_value": doc.get("contract_value_rupees"),
                    "completion_date": doc.get("completion_date"),
                    "category": doc.get("project_category"),
                }
            else:
                if not projects_dict[p_name]["client_name"] and c_name:
                    projects_dict[p_name]["client_name"] = c_name
                if not projects_dict[p_name]["employee_name"] and emp_name:
                    projects_dict[p_name]["employee_name"] = emp_name
                if doc.get("contract_value_rupees"):
                    curr_val = projects_dict[p_name]["contract_value"]
                    new_val = doc.get("contract_value_rupees")
                    if curr_val is None or (
                        curr_val % 100000 == 0 and new_val % 100000 != 0
                    ):
                        projects_dict[p_name]["contract_value"] = new_val
                if not projects_dict[p_name]["completion_date"] and doc.get(
                    "completion_date"
                ):
                    projects_dict[p_name]["completion_date"] = doc.get(
                        "completion_date"
                    )
                if not projects_dict[p_name]["category"] and doc.get(
                    "project_category"
                ):
                    projects_dict[p_name]["category"] = doc.get("project_category")

    # Insert Clients
    client_name_to_id = {}
    for c_name in sorted(clients_set):
        cursor.execute("INSERT INTO clients (client_name) VALUES (?);", (c_name,))
        client_name_to_id[c_name] = cursor.lastrowid

    # Insert Employees
    employee_name_to_id = {}
    for emp_name in sorted(employees_set):
        cursor.execute("INSERT INTO employees (employee_name) VALUES (?);", (emp_name,))
        employee_name_to_id[emp_name] = cursor.lastrowid

    # Insert Projects
    project_name_to_id = {}
    for p_name, p_info in sorted(projects_dict.items()):
        c_id = (
            client_name_to_id.get(p_info["client_name"])
            if p_info["client_name"]
            else None
        )
        e_id = (
            employee_name_to_id.get(p_info["employee_name"])
            if p_info["employee_name"]
            else None
        )

        cursor.execute(
            """
            INSERT INTO projects (project_name, client_id, employee_id, contract_value, completion_date, category)
            VALUES (?, ?, ?, ?, ?, ?);
        """,
            (
                p_name,
                c_id,
                e_id,
                p_info["contract_value"],
                p_info["completion_date"],
                p_info["category"],
            ),
        )
        project_name_to_id[p_name] = cursor.lastrowid

    # Insert Certifications
    cert_count = 0
    for doc_id, doc in extracted.items():
        if doc.get("doc_type") == "personnel_certificate" and doc.get(
            "certification_type"
        ):
            emp_name = clean_name(doc.get("employee_name"))
            e_id = employee_name_to_id.get(emp_name) if emp_name else None
            cert_type = doc.get("certification_type")
            issue_date = doc.get("certification_date")

            if e_id:
                cursor.execute(
                    """
                    INSERT INTO certifications (employee_id, cert_type, issue_date)
                    VALUES (?, ?, ?);
                """,
                    (e_id, cert_type, issue_date),
                )
                cert_count += 1

    # Insert Documents
    doc_count = 0
    for doc_id, doc in extracted.items():
        doc_type = doc.get("doc_type")
        p_name = clean_name(doc.get("project_name"))
        c_name = clean_client_name(doc.get("client_name"))

        p_id = project_name_to_id.get(p_name) if p_name else None
        c_id = client_name_to_id.get(c_name) if c_name else None

        has_ref = (
            1
            if (
                doc_type == "reference_letter"
                or (p_name and p_name in projects_with_ref_letter)
            )
            else 0
        )

        cursor.execute(
            """
            INSERT INTO documents (doc_id, doc_type, project_id, client_id, has_reference_letter)
            VALUES (?, ?, ?, ?, ?);
        """,
            (doc_id, doc_type, p_id, c_id, has_ref),
        )
        doc_count += 1

    conn.commit()
    conn.close()

    print("\nPhase 4 Database Population Summary:")
    print(f"- Clients populated: {len(client_name_to_id)}")
    print(f"- Employees populated: {len(employee_name_to_id)}")
    print(f"- Projects populated: {len(project_name_to_id)}")
    print(f"- Certifications populated: {cert_count}")
    print(f"- Documents populated: {doc_count}")
    print(f"Phase 4 Complete! SQLite database created at {DB_FILE}")


if __name__ == "__main__":
    build_database()
