import sqlite3

def verify():
    conn = sqlite3.connect('construction_archive.db')
    cursor = conn.cursor()

    tables = ['clients', 'employees', 'projects', 'certifications', 'documents']
    print("=== Table Counts ===")
    for t in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {t};")
        cnt = cursor.fetchone()[0]
        print(f"Table {t}: {cnt} rows")

    print("\n=== Indexes ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = [row[0] for row in cursor.fetchall()]
    print(", ".join(indexes))

    print("\n=== Test Query 1: Projects joined with Client & Employee ===")
    query1 = """
    SELECT p.project_id, p.project_name, c.client_name, e.employee_name, p.contract_value, p.completion_date, p.category
    FROM projects p
    LEFT JOIN clients c ON p.client_id = c.client_id
    LEFT JOIN employees e ON p.employee_id = e.employee_id
    LIMIT 5;
    """
    for row in cursor.execute(query1):
        print(" ", row)

    print("\n=== Test Query 2: Certifications per Employee ===")
    query2 = """
    SELECT e.employee_name, cert.cert_type, cert.issue_date
    FROM certifications cert
    JOIN employees e ON cert.employee_id = e.employee_id
    LIMIT 5;
    """
    for row in cursor.execute(query2):
        print(" ", row)

    print("\n=== Test Query 3: Reference Letter Absence Analysis ===")
    query3 = """
    SELECT 
        c.client_name,
        COUNT(p.project_id) AS total_projects,
        SUM(CASE WHEN d.has_reference_letter = 1 THEN 1 ELSE 0 END) AS projects_with_ref,
        SUM(CASE WHEN d.has_reference_letter = 0 THEN 1 ELSE 0 END) AS projects_without_ref
    FROM projects p
    JOIN clients c ON p.client_id = c.client_id
    LEFT JOIN documents d ON d.project_id = p.project_id AND d.doc_type = 'completion_certificate'
    GROUP BY c.client_name
    HAVING projects_without_ref > 0
    LIMIT 5;
    """
    for row in cursor.execute(query3):
        print(" ", row)

    conn.close()

if __name__ == '__main__':
    verify()
