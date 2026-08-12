import os
import json
import re
from typing import Optional, Dict, Any, List
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
    project_category: Optional[str] = None
    has_reference_letter: Optional[bool] = None


def normalize_currency(value_str: Optional[str]) -> Optional[int]:
    if not value_str or not isinstance(value_str, str):
        return None
    val_clean = value_str.strip().replace(",", "")

    # Check Crore / Cr
    cr_match = re.search(r"([\d\.]+)\s*(?:cr|crore|crores)", val_clean, re.IGNORECASE)
    if cr_match:
        try:
            return int(round(float(cr_match.group(1)) * 10000000))
        except ValueError:
            pass

    # Check Lakh / Lakhs
    lakh_match = re.search(r"([\d\.]+)\s*(?:lakh|lakhs)", val_clean, re.IGNORECASE)
    if lakh_match:
        try:
            return int(round(float(lakh_match.group(1)) * 100000))
        except ValueError:
            pass

    # Direct numeric figure
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

    # DD Mon YYYY
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", date_str)
    if m:
        mon = months.get(m.group(2).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"

    return date_str


def clean_employee_name(name: Optional[str]) -> Optional[str]:
    if not name or not isinstance(name, str):
        return None
    n = re.sub(r"\s+", " ", name).strip()
    n = re.split(r"\n|Employee|ID|National|Credential|Defect|Client|Retention|Director|DOC-|\.", n)[0].strip()
    if (
        "national infrastructure" in n.lower()
        or "director" in n.lower()
        or "authorise" in n.lower()
        or "department" in n.lower()
        or len(n) > 35
        or len(n) < 3
    ):
        return None
    return n or None


def clean_client_name(client: Optional[str]) -> Optional[str]:
    if not client or not isinstance(client, str):
        return None
    c = client.strip()
    c = re.sub(r"\s*\((?:government|psu|private)\)", "", c, flags=re.IGNORECASE).strip()
    c = re.sub(r"^(?:For\s+|Issued by\s+|Client\s+|Office of\s+)", "", c).strip()
    c = re.sub(r"\s+", " ", c).strip()
    if not c or c.lower() in ["gujarat", "odisha", "jharkhand", "delhi", "rajasthan", "maharashtra", "west bengal", "tamil nadu", "madhya pradesh"]:
        return None
    return c or None


def extract_document_entity(
    doc_id: str, doc_type: str, filename: str, content: str
) -> ExtractedEntity:
    entity = ExtractedEntity(doc_id=doc_id, doc_type=doc_type)

    if doc_type in ["company_completion_certificate", "completion_certificate"]:
        # Project Name
        pm = (
            re.search(r"(?:Work|Project Name)\s+(.*?)(?=\n(?:Client|Scope|Work Category|Category|Contract|Completion|Project Manager|Project Lead)\b|\n[A-Z]|\n\n|$)", content, re.DOTALL)
            or re.search(r"Name of Work\s+(.*?)(?=\n(?:Nature|Category|Contract|Completion|Defect)\b|$)", content, re.DOTALL)
            or re.search(r"work of\s+([A-Za-z0-9\s\-\–\—\.\,\&]+?)\s*\(", content)
            or re.search(r"work of\s+([A-Za-z0-9\s\-\–\—\.\,\&]+?)\s*,", content)
            or re.search(r"work of\s+([A-Za-z0-9\s\-\–\—\.\,\&]+?)\s+awarded to", content)
        )
        if pm:
            entity.project_name = pm.group(1).replace("\n", " ").strip()

        # Client Name
        cm = (
            re.search(r"Client\s+(.*?)(?=\n(?:Category|Scope|Executed Value|Contract|Completion|Project Lead|Project Manager)\b|\n[A-Z]|\n\n|$)", content, re.DOTALL)
            or re.search(r"Issued by\s+(.*?)(?=\s+REF|Ref|Date|$)", content)
            or re.search(r"Office of the Executive Engineer\s+(.*?)(?=\s+IN No|Dated|$)", content)
            or re.search(r"^(.*?)\s+(?:Work Completion Certificate|WORK COMPLETION CERTIFICATE)", content, re.MULTILINE)
        )
        if cm:
            entity.client_name = clean_client_name(cm.group(1).replace("\n", " "))

        # Category
        catm = (
            re.search(r"(?:Work Category|Category)\s+(.*?)(?=\n(?:Contract Value|Executed Value|Completion|Project Lead|Project Manager)\b|\n[A-Z]|\n\n|$)", content, re.DOTALL)
            or re.search(r"Nature / Category\s+(.*?)(?=\s+Contract)", content)
        )
        if catm:
            entity.project_category = catm.group(1).replace("\n", " ").strip()

        # Executed Value
        vm = re.search(
            r"(?:gross executed value of|Executed Value|Contract Value|Value)\s+(INR\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|Rs\.\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|[\d\.,]+\s+Crore|[\d\.,]+\s+Lakh)",
            content,
            re.IGNORECASE,
        )
        if vm:
            entity.contract_value_raw = vm.group(1).strip()

        # Completion Date
        dm = re.search(
            r"(?:Completion Date|Completion|completed on)\s+(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            content,
        )
        if dm:
            entity.completion_date = normalize_date(dm.group(1).strip())

        # Employee Name (Project Lead / Manager)
        em = re.search(
            r"(?:Project Lead|Project Manager|Contractor\'s Project Manager|supervised on the contractor\'s side by)[:\s]*\n?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)",
            content,
        )
        if em:
            entity.employee_name = clean_employee_name(em.group(1))

    elif doc_type == "reference_letter":
        entity.has_reference_letter = True

        # Client Name
        cm = (
            re.search(r"^(.*?)\s*(?:Letter of Recommendation|Letter of Appreciation|government|PSU CLIENT|PRIVATE CLIENT|Ref:)", content, re.MULTILINE)
            or re.search(r"For\s+(.*?)\s+DOC-REF", content)
        )
        if cm:
            entity.client_name = clean_client_name(cm.group(1).replace("\n", " "))

        # Project Name
        pm = (
            re.search(r"Work Executed\s*\n?\s*([^\n]+)", content)
            or re.search(r"for the work\s+[^\w]*([^\n\(]+?)[^\w]*\s*\(INR", content, re.IGNORECASE)
            or re.search(r"Subject:.*?[–—\-]\s*[^\w]*([^\n”\"\'\’\ufffd]+)", content)
            or re.search(r"Project Name\s*\n?\s*([^\n]+)", content)
            or re.search(r"([A-Za-z0-9\s\-\–\—\.\,\&]+?\s+Pkg-\d+)", content)
        )
        if pm:
            entity.project_name = pm.group(1).strip()

    elif doc_type == "personnel_certificate":
        # Certified Person Name
        em = (
            re.search(r"conferred upon\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)", content)
            or re.search(r"certify that\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)", content)
            or re.search(r"Name\s*\n?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)", content)
        )
        if em:
            entity.employee_name = clean_employee_name(em.group(1))

        # Certification Type
        ctm = (
            re.search(r"(PMP|Six Sigma Black Belt|ISO 9001 Lead Auditor|PRINCE2 Practitioner|LEED AP)", content, re.IGNORECASE)
            or re.search(r"Credential Type\s*\n?\s*([A-Za-z0-9\s]+)", content)
        )
        if ctm:
            entity.certification_type = ctm.group(1).strip()

        # Issue Date
        dtm = re.search(
            r"(?:Issued|Date of Issue|Dated)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            content,
            re.IGNORECASE,
        )
        if dtm:
            entity.certification_date = normalize_date(dtm.group(1).strip())

    elif doc_type == "cv":
        em = re.search(r"Name\s*\n?\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)+)", content)
        if em:
            entity.employee_name = clean_employee_name(em.group(1))

    # Calculate contract_value_rupees if raw contract value exists
    if entity.contract_value_raw:
        entity.contract_value_rupees = normalize_currency(entity.contract_value_raw)

    return entity


def main():
    parsed_file = "parsed_corpus.json"
    output_file = "extracted_database.json"

    if not os.path.exists(parsed_file):
        print(f"Error: {parsed_file} not found. Please run ingest.py first.")
        return

    print(f"Loading {parsed_file}...")
    with open(parsed_file, "r", encoding="utf-8") as f:
        corpus = json.load(f)

    print(f"Processing entity extraction across {len(corpus)} documents...")
    extracted_database = {}

    for doc_id, doc in corpus.items():
        doc_type = doc.get("doc_type", "")
        filename = doc.get("filename", "")
        content = doc.get("content", "")

        entity = extract_document_entity(doc_id, doc_type, filename, content)
        extracted_database[doc_id] = entity.model_dump()

    print(f"Saving extracted entities to {output_file}...")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(extracted_database, f, indent=4, ensure_ascii=False)

    # Print summary statistics
    projects_cnt = sum(1 for e in extracted_database.values() if e.get("project_name"))
    clients_cnt = sum(1 for e in extracted_database.values() if e.get("client_name"))
    employees_cnt = sum(1 for e in extracted_database.values() if e.get("employee_name"))
    certs_cnt = sum(1 for e in extracted_database.values() if e.get("certification_type"))
    values_cnt = sum(1 for e in extracted_database.values() if e.get("contract_value_rupees") is not None)
    ref_letters_cnt = sum(1 for e in extracted_database.values() if e.get("has_reference_letter"))

    print("\nPhase 3 Extraction Summary:")
    print(f"- Total documents processed: {len(extracted_database)}")
    print(f"- Extracted Project Names: {projects_cnt}")
    print(f"- Extracted Client Names: {clients_cnt}")
    print(f"- Extracted Employee Names: {employees_cnt}")
    print(f"- Extracted Certifications: {certs_cnt}")
    print(f"- Extracted Normalized Values (Rupees): {values_cnt}")
    print(f"- Reference Letters Identified: {ref_letters_cnt}")
    print(f"Phase 3 Complete! Output written to {output_file}")


if __name__ == "__main__":
    main()

