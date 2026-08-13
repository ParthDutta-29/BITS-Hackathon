import os
import pandas as pd
import json
import re
import argparse

try:
    import pymupdf as fitz
except ImportError:
    import fitz


def extract_text_from_pdf(filepath):
    text = ""
    try:
        doc = fitz.open(filepath)
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
        doc.close()
    except Exception as e:
        print(f"PyMuPDF error reading {filepath}: {e}")

    if not text.strip():
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except Exception as e:
            pass

    return text


def extract_text_from_excel(filepath):
    text = ""
    try:
        xls = pd.read_excel(filepath, sheet_name=None, engine="openpyxl")
        for sheet_name, df in xls.items():
            text += f"--- Sheet: {sheet_name} ---\n"
            text += df.to_string(index=False, na_rep="") + "\n"
        return text
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def clean_text(raw_text):
    if not raw_text:
        return ""
    cleaned = re.sub(r"[ \t\r\f\v]+", " ", raw_text)
    cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
    return cleaned.strip()


def classify_doc_type(filename, filepath, content, root, docs_dir):
    path_lower = filepath.replace("\\", "/").lower()
    fname_lower = filename.lower()
    content_lower = content[:1000].lower() if content else ""

    if "company_completion_certificate" in path_lower or "company completion" in content_lower:
        return "company_completion_certificate"
    if "completion_certificate" in path_lower or "completion certificate" in content_lower or "work completion certificate" in content_lower:
        return "completion_certificate"
    if "reference_letter" in path_lower or "letter of recommendation" in content_lower or "letter of appreciation" in content_lower or "reference" in path_lower:
        return "reference_letter"
    if "personnel_certificate" in path_lower or "credential type" in content_lower or "conferred upon" in content_lower or "personnel" in path_lower:
        return "personnel_certificate"
    if "cv" in path_lower or "curriculum vitae" in content_lower or "engineer profile" in content_lower:
        return "cv"
    if "compliance_matrix" in path_lower or "compliance" in content_lower:
        return "compliance_matrix"
    if "general_ledger" in path_lower or "ledger" in content_lower:
        return "general_ledger_book"
    if "bank_statement" in path_lower or "bank statement" in content_lower:
        return "bank_statement"
    if "financial_statement" in path_lower or "balance sheet" in content_lower:
        return "financial_statement"
    if "ra_bill" in path_lower or "running account" in content_lower or "boq" in content_lower:
        return "ra_bill"
    if "tender_dossier" in path_lower or "tender" in content_lower:
        return "tender_dossier"
    if "iso_certificate" in path_lower or "iso 9001" in content_lower:
        return "iso_certificate"
    if "annual_report" in path_lower or "annual report" in content_lower:
        return "annual_report"
    if "past_performance" in path_lower or "portfolio" in content_lower:
        return "past_performance_portfolio"
    if fname_lower.endswith(".xlsx"):
        return "workbooks"

    rel_dir = os.path.relpath(root, docs_dir)
    return rel_dir.replace("\\", "/") if rel_dir != "." else "general"


def main():
    parser = argparse.ArgumentParser(description="Ingest document tree into parsed_corpus.json")
    parser.add_argument("--docs", default="documents", help="Path to documents directory")
    args = parser.parse_args()

    docs_dir = args.docs
    index_file = os.path.join(docs_dir, "document_index.csv")
    if not os.path.exists(index_file) and os.path.exists("document_index.csv"):
        index_file = "document_index.csv"

    index_map = {}
    if os.path.exists(index_file):
        try:
            df = pd.read_csv(index_file)
            for _, row in df.iterrows():
                fname = str(row["filename"]).strip()
                index_map[fname] = {
                    "doc_id": str(row["doc_id"]).strip(),
                    "doc_type": str(row["doc_type"]).strip(),
                }
        except Exception as e:
            print(f"Warning: Could not read {index_file}: {e}")

    extracted_corpus = {}
    file_list = []

    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            f_lower = file.lower()
            if f_lower.endswith(".pdf") or f_lower.endswith(".xlsx"):
                full_path = os.path.join(root, file)
                file_list.append((file, full_path, root))

    total_docs = len(file_list)
    print(f"Starting ingestion of {total_docs} documents from {docs_dir}...")

    for idx, (filename, filepath, root) in enumerate(file_list, start=1):
        if idx % 50 == 0 or idx == total_docs:
            print(f"Processing {filename} ({idx}/{total_docs})...")

        raw_text = ""
        f_lower = filename.lower()
        if f_lower.endswith(".pdf"):
            raw_text = extract_text_from_pdf(filepath)
        elif f_lower.endswith(".xlsx"):
            raw_text = extract_text_from_excel(filepath)

        cleaned_text = clean_text(raw_text)

        if filename in index_map:
            doc_id = index_map[filename]["doc_id"]
            doc_type = index_map[filename]["doc_type"]
        else:
            doc_id = os.path.splitext(filename)[0]
            doc_type = classify_doc_type(filename, filepath, cleaned_text, root, docs_dir)

        extracted_corpus[doc_id] = {
            "doc_type": doc_type,
            "filename": filename,
            "filepath": filepath,
            "content": cleaned_text,
        }

    with open("parsed_corpus.json", "w", encoding="utf-8") as f:
        json.dump(extracted_corpus, f, indent=4, ensure_ascii=False)

    print(
        f"Phase 2 Complete! Extracted data saved to parsed_corpus.json ({len(extracted_corpus)} documents)"
    )


if __name__ == "__main__":
    main()

