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
    project_category: Optional[str] = None  # Water Treatment, Bridge, Road, Building
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


def clean_employee_name(name: Optional[str]) -> Optional[str]:
    if not name or not isinstance(name, str):
        return None
    n = re.sub(r"\s+", " ", name).strip()
    if (
        "national infrastructure" in n.lower()
        or "director" in n.lower()
        or "authorise" in n.lower()
        or "department" in n.lower()
        or len(n) > 35
    ):
        return None
    return n or None


def clean_client_name(client: Optional[str]) -> Optional[str]:
    if not client or not isinstance(client, str):
        return None
    c = client.strip()
    if "works for " in c:
        m = re.search(r"works for\s+([A-Za-z0-9\s,\.&]+?)(?=\s+completed|\s*$)", c)
        if m:
            c = m.group(1)
    c = re.sub(
        r"\s+(?:GOVERNMENT|PRIVATE|PSU|CLIENT|IN REFERENCE LETTER|To Whomsoever|Reference Letter).*$",
        "",
        c,
        flags=re.IGNORECASE,
    )
    c = re.sub(r"\s*\((?:government|Government|psu|PSU|private|Private)\)", "", c)
    c = re.sub(r"^(?:For\s+|Issued by\s+|Client\s+|Office of\s+)", "", c)
    c = re.sub(r"\s+", " ", c).strip()

    c_lower = c.lower()
    if c_lower in [
        "gujarat",
        "odisha",
        "jharkhand",
        "delhi",
        "rajasthan",
        "maharashtra",
        "west bengal",
        "tamil nadu",
        "madhya pradesh",
    ]:
        return None

    if "jal nigam" in c_lower and "jharkhand" in c_lower:
        return "Jal Nigam, Jharkhand"
    elif "jal nigam" in c_lower and "gujarat" in c_lower:
        return "Jal Nigam, Gujarat"
    elif "jal nigam" in c_lower and "uttar pradesh" in c_lower:
        return "Jal Nigam, Uttar Pradesh"
    elif "public health engineering" in c_lower and (
        "gujarat" in c_lower or "govt of gujarat" in c_lower
    ):
        return "Public Health Engineering Dept, Govt of Gujarat"
    elif "public health engineering" in c_lower and (
        "odisha" in c_lower or "govt of odisha" in c_lower
    ):
        return "Public Health Engineering Dept, Govt of Odisha"
    elif "public works department" in c_lower and "gujarat" in c_lower:
        return "Public Works Department, Govt of Gujarat"
    elif "public works department" in c_lower and "maharashtra" in c_lower:
        return "Public Works Department, Govt of Maharashtra"
    elif "public works department" in c_lower and "west bengal" in c_lower:
        return "Public Works Department, Govt of West Bengal"
    elif "public works department" in c_lower and "tamil nadu" in c_lower:
        return "Public Works Department, Govt of Tamil Nadu"
    elif "irrigation & waterways" in c_lower and "west bengal" in c_lower:
        return "Irrigation & Waterways Dept, Govt of West Bengal"
    elif "irrigation & waterways" in c_lower and "uttar pradesh" in c_lower:
        return "Irrigation & Waterways Dept, Govt of Uttar Pradesh"
    elif "irrigation & waterways" in c_lower and "rajasthan" in c_lower:
        return "Irrigation & Waterways Dept, Govt of Rajasthan"
    elif "jharkhand municipal" in c_lower:
        return "Jharkhand Municipal Corporation"
    elif "maharashtra municipal" in c_lower:
        return "Maharashtra Municipal Corporation"
    elif "gujarat municipal" in c_lower:
        return "Gujarat Municipal Corporation"
    elif "tamil nadu municipal" in c_lower:
        return "Tamil Nadu Municipal Corporation"
    elif "lakshya engineering" in c_lower:
        return "Lakshya Engineering & Construction"
    elif "national expressway" in c_lower:
        return "National Expressway Development Authority"
    elif "national special projects" in c_lower:
        return "National Special Projects Office"
    elif "mega infrastructure" in c_lower:
        return "Mega Infrastructure Authority"
    elif "meridian constructors" in c_lower:
        return "Meridian Constructors & Co."
    elif "peninsular petroleum" in c_lower:
        return "Peninsular Petroleum Corporation"
    elif "suvarna projects" in c_lower:
        return "Suvarna Projects Limited"
    elif "trishakti power" in c_lower:
        return "Trishakti Power Generation Corporation"
    elif "mahanadi steel" in c_lower:
        return "Mahanadi Steel Corporation"
    elif "subarnarekha valley" in c_lower:
        return "Subarnarekha Valley Corporation"
    elif "arunodaya infrastructure" in c_lower:
        return "Arunodaya Infrastructure"
    elif "central works" in c_lower:
        return "Central Works & Buildings Bureau"

    return c or None


def extract_document_entity(
    doc_id: str, doc_type: str, filename: str, content: str
) -> ExtractedEntity:
    entity = ExtractedEntity(doc_id=doc_id, doc_type=doc_type)

    if doc_type in ["company_completion_certificate", "completion_certificate"]:
        # Project Name
        pm = (
            re.search(
                r"Project Name\s+(.*?)(?=\s+\b(?:Client|Scope|Work Category|Category|Contract|Completion|Project Manager)\b|$)",
                content,
            )
            or re.search(
                r"Name of Work\s+(.*?)(?=\s+\b(?:Nature|Category|Contract|Completion|Defect)\b|$)",
                content,
            )
            or re.search(r"work of\s+([A-Za-z0-9\s\-]+?)\s*\(", content)
            or re.search(r"work of\s+([A-Za-z0-9\s\-]+?)\s*,", content)
            or re.search(r"work of\s+([A-Za-z0-9\s\-]+?)\s+awarded to", content)
            or re.search(
                r"Work\s+(.*?)(?=\s+\b(?:Client|Category|Executed Value|Completion|Project Lead)\b|$)",
                content,
            )
        )
        if pm:
            entity.project_name = pm.group(1).strip()

        # Client Name
        cm = (
            re.search(
                r"Client\s+(.*?)(?=\s+(?:Scope|Category|Executed Value|Contract|Completion|Project Lead|Manager|$))",
                content,
            )
            or re.search(r"Issued by\s+(.*?)(?=\s+REF|Ref|Date|$)", content)
            or re.search(
                r"Office of the Executive Engineer\s+(.*?)(?=\s+IN No|Dated|$)", content
            )
            or re.search(r"for\s+(.*?)\s+completed \d{4}", content)
            or re.search(
                r"^(.*?)\s+(?:Work Completion Certificate|WORK COMPLETION CERTIFICATE)",
                content,
                re.MULTILINE,
            )
        )
        if cm:
            entity.client_name = clean_client_name(cm.group(1))

        # Category
        catm = (
            re.search(
                r"(?:Work Category|Category)\s+(.*?)(?=\s+(?:Contract Value|Executed Value|Completion|Project Lead|$))",
                content,
            )
            or re.search(r"Nature / Category\s+(.*?)(?=\s+Contract)", content)
            or re.search(r"\(([^)]+)\),\s*awarded to M/s", content)
        )
        if catm:
            entity.project_category = catm.group(1).strip()

        # Contract Value Raw
        vm = re.search(
            r"(?:gross executed value of|Executed Value|Contract Value|Value)\s+(INR\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|Rs\.\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|[\d\.,]+\s+Crore|[\d\.,]+\s+Lakh)",
            content,
            re.IGNORECASE,
        ) or re.search(
            r"(INR\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?|Rs\.\s+[\d\.,]+(?:\/\-)?\s*(?:Cr|Crore|Lakh|Lakhs)?)",
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
            r"(?:Project Lead|Project Manager|Contractor\'s Project Manager|supervised on the contractor\'s side by)\s+([A-Za-z\s]+?)(?=\s+2\.|\s+DECLARATION|\s+Defect|\s+Client|\s+Retention|\s+Director|\s+DOC-|\.|$)",
            content,
        ) or re.search(
            r"Manager\s+([A-Za-z\s]+?)(?=\s+2\.|\s+DECLARATION|\s+DOC-|$)", content
        )
        if em:
            entity.employee_name = clean_employee_name(em.group(1))

    elif doc_type == "reference_letter":
        entity.has_reference_letter = True

        # Client Name
        cm = (
            re.search(
                r"^(.*?)\s+(?:Letter of Recommendation|government|PSU CLIENT|PRIVATE CLIENT|Ref:)",
                content,
                re.MULTILINE,
            )
            or re.search(r"For\s+(.*?)\s+DOC-REF", content)
            or re.search(
                r"Contact for Verification\s+[A-Za-z\s]+\s+([A-Za-z0-9\s,\.]+?)\s+DOC-REF",
                content,
            )
        )
        if cm:
            entity.client_name = clean_client_name(cm.group(1))

        # Project Name
        pm = (
            re.search(
                r"Project Name\s+(.*?)(?=\s+(?:Scope|Nature|Contract|Date|$))", content
            )
            or re.search(r"work\s+([A-Za-z0-9\s\-]+?)\s*\(", content)
            or re.search(
                r"Work Executed\s+([A-Za-z0-9\s\-]+?)\s+(?:Value|Completed)", content
            )
            or re.search(
                r"Subject: Performance of M/s National Infrastructure Corp\. Ltd\.\s+([A-Za-z0-9\s\-]+)",
                content,
            )
        )
        if pm:
            entity.project_name = pm.group(1).strip()

        # Contract Value Raw
        vm = re.search(
            r"\((INR\s+[\d\.]+\s+[A-Za-z]+)\)|Value\s+(INR\s+[\d\.]+\s+[A-Za-z]+|Rs\.\s+[\d\.]+\s+[A-Za-z]+)",
            content,
        )
        if vm:
            entity.contract_value_raw = (vm.group(1) or vm.group(2)).strip()

        # Completion Date
        dm = re.search(
            r"(?:completed on|Completed|Date of Completion)\s+(\d{1,2}\s+[A-Za-z]{3}\s+\d{4}|\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})",
            content,
        )
        if dm:
            entity.completion_date = normalize_date(dm.group(1).strip())

    elif doc_type == "personnel_certificate":
        # Certified Person Name
        em = (
            re.search(r"conferred upon\s+([A-Za-z\s]+?)\s+of", content)
            or re.search(r"certify that\s+([A-Za-z\s]+?)\s+Employee ID", content)
            or re.search(r"Registrar\s+([A-Za-z\s]+?)\s+(?:PMI|ASQ)", content)
            or re.search(r"Name\s+([A-Za-z\s]+?)\s+Employee ID", content)
        )
        if em:
            entity.employee_name = clean_employee_name(em.group(1))

        # Certification Type
        ctm = (
            re.search(
                r"Credential Type\s+([A-Za-z0-9\s]+?)(?=\s+Credential ID|\s+Issuing|$)",
                content,
            )
            or re.search(
                r"(PMP|Six Sigma Black Belt|ISO 9001 Lead Auditor|PRINCE2 Practitioner|LEED AP)",
                content,
                re.IGNORECASE,
            )
            or re.search(r"([A-Za-z0-9\s]+?)\s+CERTIFICATION", content)
        )
        if ctm:
            entity.certification_type = ctm.group(1).strip()

        # Issue Date
        dtm = re.search(
            r"(?:Issued|Date of Issue)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{1,2}\s+[A-Za-z]{3}\s+\d{4})",
            content,
        )
        if dtm:
            entity.certification_date = normalize_date(dtm.group(1).strip())

    elif doc_type == "cv":
        em = re.search(r"Name\s+([A-Za-z\s]+?)\s+Employee ID", content) or re.search(
            r"CurriCulum Vitae\s+([A-Za-z\s]+?)\s+Designation", content
        )
        if em:
            entity.employee_name = clean_employee_name(em.group(1))

    elif doc_type == "performance_bond":
        # Client / Employer
        cm = re.search(
            r"To:\s*(.*?)(?=\s+Subject|\s+India|\s+The Employer|$)", content
        ) or re.search(r"To,\s*(.*?)(?=\s+Subject|$)", content)
        if cm:
            entity.client_name = clean_client_name(cm.group(1))

        # Project / Tender Ref
        pm = (
            re.search(
                r"Subject:\s*Performance Bond\s+([A-Za-z0-9\s\-\(\)]+?)(?=\s+Dear|\s+Subject|\s+Value|$)",
                content,
            )
            or re.search(
                r"Tender Ref:\s*([A-Za-z0-9\-\s]+?)(?=\s+Dear|\s+Subject|\s+Value|$)",
                content,
            )
            or re.search(
                r"work of\s+([A-Za-z0-9\s,\-]+?)(?=\s*,|\s+and WHEREAS|$)", content
            )
        )
        if pm:
            entity.project_name = pm.group(1).strip()

        # Bond Value
        vm = re.search(
            r"(?:exceeding|amount of|not exceeding)\s+(Rs\.\s+[\d\.]+\s+[A-Za-z]+|INR\s+[\d\.]+\s+[A-Za-z]+|Rs\.\s+[\d\.,]+)",
            content,
        )
        if vm:
            entity.contract_value_raw = vm.group(1).strip()

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
        json.dump(extracted_database, f, indent=4)

    # Print summary statistics
    projects_cnt = sum(1 for e in extracted_database.values() if e.get("project_name"))
    clients_cnt = sum(1 for e in extracted_database.values() if e.get("client_name"))
    employees_cnt = sum(
        1 for e in extracted_database.values() if e.get("employee_name")
    )
    certs_cnt = sum(
        1 for e in extracted_database.values() if e.get("certification_type")
    )
    values_cnt = sum(
        1
        for e in extracted_database.values()
        if e.get("contract_value_rupees") is not None
    )
    ref_letters_cnt = sum(
        1 for e in extracted_database.values() if e.get("has_reference_letter")
    )

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
