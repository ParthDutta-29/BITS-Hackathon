import json
import sqlite3
import re

def clean_client(name):
    if not name:
        return None
    name = re.sub(r'\s+', ' ', name).strip()
    name = re.sub(r'\s*\((?:government|Government|psu|PSU|private|Private)\)', '', name)
    name = name.replace(',', '')
    return name.strip() or None

def clean_project(name):
    if not name:
        return None
    name = re.sub(r'\s+', ' ', name).strip()
    return name or None

def clean_employee(name):
    if not name:
        return None
    name = re.sub(r'\s+', ' ', name).strip()
    return name or None

def test_db():
    with open('extracted_database.json', 'r', encoding='utf-8') as f:
        extracted = json.load(f)

    print(f"Loaded {len(extracted)} extracted entities.")

    clients = set()
    employees = set()
    projects = {}  # proj_name -> dict of info

    for doc_id, e in extracted.items():
        c_name = clean_client(e.get('client_name'))
        p_name = clean_project(e.get('project_name'))
        emp_name = clean_employee(e.get('employee_name'))

        if c_name:
            clients.add(c_name)
        if emp_name:
            employees.add(emp_name)

        if p_name:
            if p_name not in projects:
                projects[p_name] = {
                    'client_name': c_name,
                    'employee_name': emp_name,
                    'contract_value': e.get('contract_value_rupees'),
                    'completion_date': e.get('completion_date'),
                    'category': e.get('project_category')
                }
            else:
                # Fill missing fields if available
                if not projects[p_name]['client_name'] and c_name:
                    projects[p_name]['client_name'] = c_name
                if not projects[p_name]['employee_name'] and emp_name:
                    projects[p_name]['employee_name'] = emp_name
                if not projects[p_name]['contract_value'] and e.get('contract_value_rupees'):
                    projects[p_name]['contract_value'] = e.get('contract_value_rupees')
                if not projects[p_name]['completion_date'] and e.get('completion_date'):
                    projects[p_name]['completion_date'] = e.get('completion_date')
                if not projects[p_name]['category'] and e.get('project_category'):
                    projects[p_name]['category'] = e.get('project_category')

    print(f"Unique clients: {len(clients)}")
    print(f"Unique employees: {len(employees)}")
    print(f"Unique projects: {len(projects)}")

if __name__ == '__main__':
    test_db()
