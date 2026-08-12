import json
import re
from typing import Optional
from pydantic import BaseModel


class ExtractedEntity(BaseModel):
    doc_id: str
    doc_type: str
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    employee_name: Optional[str] = None
    certification_type: Optional[str] = None  # PMP, Six Sigma Black Belt
    certification_date: Optional[str] = None  # YYYY-MM-DD
    completion_date: Optional[str] = None  # YYYY-MM-DD
    contract_value_raw: Optional[str] = None
    contract_value_rupees: Optional[int] = None
    project_category: Optional[str] = None  # Water Treatment, Bridge, Road, Building
    has_reference_letter: Optional[bool] = None


def normalize_currency(value_str: Optional[str]) -> Optional[int]:
    if not value_str or not isinstance(value_str, str):
        return None
    val_clean = value_str.strip().replace(",", "")
    cr_match = re.search(r"([\d\.]+)\s*(?:cr|crore|crores)", val_clean, re.IGNORECASE)
    if cr_match:
        try:
            return int(round(float(cr_match.group(1)) * 10000000))
        except ValueError:
            pass
    lakh_match = re.search(r"([\d\.]+)\s*(?:lakh|lakhs)", val_clean, re.IGNORECASE)
    if lakh_match:
        try:
            return int(round(float(lakh_match.group(1)) * 100000))
        except ValueError:
            pass
    num_match = re.search(r"[\d\.]+", val_clean)
    if num_match:
        try:
            return int(round(float(num_match.group(0))))
        except ValueError:
            pass
    return None


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    date_str = date_str.strip()
    # DD/MM/YYYY
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_str)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    # YYYY-MM-DD
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # DD Mon YYYY (e.g. 06 Feb 2011)
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", date_str)
    if m:
        mon = months.get(m.group(2).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return date_str


def extract_rule_based(doc_id: str, doc_type: str, content: str) -> ExtractedEntity:
    entity = ExtractedEntity(doc_id=doc_id, doc_type=doc_type)

    if doc_type in ["company_completion_certificate", "completion_certificate"]:
        # Project Name
        pm = (
            re.search(
                r"Project Name\s+(.*?)(?=\s+(?:Client|Scope|Work|Contract|Completion|Project Manager|$))",
                content,
            )
            or re.search(
                r"Work\s+(.*?)(?=\s+(?:Client|Category|Executed Value|Completion|Project Lead|$))",
                content,
            )
            or re.search(
                r"Name of Work\s+(.*?)(?=\s+(?:Nature|Category|Contract|Completion|Defect|$))",
                content,
            )
            or re.search(r"work of\s+(.*?)\s*\(", content)
            or re.search(r"work of\s+(.*?)\s*,", content)
        )
        if pm:
            entity.project_name = pm.group(1).strip()

        # Client Name
        cm = (
            re.search(
                r"Client\s+(.*?)(?=\s+(?:Scope|Category|Executed Value|Contract|Completion|Project Lead|Manager|\(government\)|\(Government\)|\(psu\)|\(PSU\)|\(Private\)|$))",
                content,
            )
            or re.search(r"Issued by\s+(.*?)(?=\s+REF|Date|$)", content)
            or re.search(
                r"Office of the Executive Engineer\s+(.*?)(?=\s+IN No|Dated|$)", content
            )
            or re.search(r"^(.*?)\s+Work Completion Certificate", content, re.MULTILINE)
            or re.search(r"^(.*?)\s+WORK COMPLETION CERTIFICATE", content, re.MULTILINE)
        )
        if cm:
            client_clean = re.sub(
                r"\s*\((?:government|Government|psu|PSU|private|Private)\)",
                "",
                cm.group(1).strip(),
            )
            entity.client_name = client_clean

        # Category
        catm = re.search(
            r"(?:Work Category|Category)\s+(.*?)(?=\s+(?:Contract Value|Executed Value|Completion|Project Lead|$))",
            content,
        ) or re.search(r"\(([^)]+)\),\s*awarded to M/s", content)
        if catm:
            entity.project_category = catm.group(1).strip()

        # Contract Value Raw
        vm = re.search(
            r"(?:Executed Value|Contract Value|gross executed value of)\s+(INR\s+[\d\.]+\s+[A-Za-z]+|Rs\.\s+[\d\.]+\s+[A-Za-z]+|[\d\.,]+\s+Crore|[\d\.,]+)",
            content,
            re.IGNORECASE,
        )
        if vm:
            entity.contract_value_raw = vm.group(1).strip()

        # Completion Date
        dm = re.search(
            r"(?:Completion Date|Completion|completed on)\s+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            content,
        ) or re.search(r"on\s+(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})", content)
        if dm:
            entity.completion_date = normalize_date(dm.group(1).strip())

        # Employee Name (Project Lead / Manager)
        em = re.search(
            r"(?:Project Lead|Project Manager|supervised on the contractor\'s side by)\s+([A-Za-z\s]+?)(?=\s+(?:Defect|Client|Retention|Director|DOC-|$))",
            content,
        )
        if em:
            entity.employee_name = em.group(1).strip()

    elif doc_type == "reference_letter":
        entity.has_reference_letter = True

        # Client Name (from header)
        cm = re.search(
            r"^(.*?)\s+(?:Letter of Recommendation|government|Ref:)", content
        )
        if cm:
            entity.client_name = cm.group(1).strip()

        # Project Name
        pm = re.search(r"work\s+([A-Za-z0-9\s\-]+?)\s+\(", content) or re.search(
            r"Work Executed\s+([A-Za-z0-9\s\-]+?)\s+Value", content
        )
        if pm:
            entity.project_name = pm.group(1).strip()

        # Contract Value Raw
        vm = re.search(
            r"\((INR\s+[\d\.]+\s+[A-Za-z]+)\)|Value\s+(INR\s+[\d\.]+\s+[A-Za-z]+)",
            content,
        )
        if vm:
            entity.contract_value_raw = (vm.group(1) or vm.group(2)).strip()

        # Completion Date
        dm = re.search(
            r"(?:completed on|Completed)\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
            content,
        )
        if dm:
            entity.completion_date = normalize_date(dm.group(1).strip())

    elif doc_type == "personnel_certificate":
        # Certified Person Name
        em = re.search(
            r"certify that\s+([A-Za-z\s]+?)\s+Employee ID", content
        ) or re.search(r"Registrar\s+([A-Za-z\s]+?)\s+PMI", content)
        if em:
            entity.employee_name = em.group(1).strip()

        # Certification Type
        ctm = re.search(
            r"Credential Type\s+([A-Za-z0-9\s]+?)(?=\s+Credential ID|\s+Issuing|$)",
            content,
        ) or re.search(r"([A-Za-z0-9\s]+?)\s+CERTIFICATION", content)
        if ctm:
            entity.certification_type = ctm.group(1).strip()

        # Issue Date
        dtm = re.search(
            r"(?:Issued|Date of Issue):\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})",
            content,
        )
        if dtm:
            entity.certification_date = normalize_date(dtm.group(1).strip())

    elif doc_type == "cv":
        em = re.search(r"Name\s+([A-Za-z\s]+?)\s+Employee ID", content)
        if em:
            entity.employee_name = em.group(1).strip()

    # Calculate contract_value_rupees if raw exists
    if entity.contract_value_raw:
        entity.contract_value_rupees = normalize_currency(entity.contract_value_raw)

    return entity


def run_test():
    with open("parsed_corpus.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)

    extracted = {}
    for doc_id, doc_data in corpus.items():
        extracted[doc_id] = extract_rule_based(
            doc_id, doc_data["doc_type"], doc_data["content"]
        ).model_dump()

    print(f"Extracted {len(extracted)} entity records.")

    # Check stats
    projects = sum(1 for e in extracted.values() if e["project_name"])
    clients = sum(1 for e in extracted.values() if e["client_name"])
    employees = sum(1 for e in extracted.values() if e["employee_name"])
    certs = sum(1 for e in extracted.values() if e["certification_type"])
    values = sum(1 for e in extracted.values() if e["contract_value_rupees"])

    print(
        f"Extracted statistics:\n  Project names: {projects}\n  Client names: {clients}\n  Employee names: {employees}\n  Certifications: {certs}\n  Contract values (rupees): {values}"
    )


if __name__ == "__main__":
    run_test()
