import os
import pandas as pd
import json
import re
import pdfplumber

# Initialization and Mapping
index_df = pd.read_csv("document_index.csv")
documents_dir = "documents/"

# This dictionary will hold the extracted corpus
# Schema: { "doc_id": {"doc_type": "...", "filename": "...", "content": "..."} }
extracted_corpus = {}


def extract_text_from_pdf(filepath):
    text = ""
    try:
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                # Extract raw text, preserving page order
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def extract_text_from_excel(filepath):
    text = ""
    try:
        # reads sheets; cached values are returned by pandas
        xls = pd.read_excel(filepath, sheet_name=None, engine="openpyxl")
        for sheet_name, df in xls.items():
            text += f"--- Sheet: {sheet_name} ---\n"
            # Convert dataframe to a string representation for the LLM context
            text += df.to_string(index=False, na_rep="") + "\n"
        return text
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""


def clean_text(raw_text):
    if not raw_text:
        return ""
    # Condense multiple spaces/newlines into a single space
    cleaned = re.sub(r"\s+", " ", raw_text)
    # Strip non-ASCII characters and hidden artifacts
    cleaned = re.sub(r"[^\x00-\x7F]+", " ", cleaned)
    return cleaned.strip()


def main():
    total_docs = len(index_df)
    print(f"Starting ingestion of {total_docs} documents from {documents_dir}...")

    for index, row in index_df.iterrows():
        doc_id = row["doc_id"]
        doc_type = row["doc_type"]
        filename = row["filename"]
        filepath = os.path.join(documents_dir, filename)

        if (index + 1) % 50 == 0 or (index + 1) == total_docs:
            print(f"Processing {doc_id} ({index + 1}/{total_docs})...")

        raw_text = ""
        if filename.endswith(".pdf"):
            raw_text = extract_text_from_pdf(filepath)
        elif filename.endswith(".xlsx"):
            raw_text = extract_text_from_excel(filepath)

        cleaned_text = clean_text(raw_text)

        extracted_corpus[doc_id] = {
            "doc_type": doc_type,
            "filename": filename,
            "content": cleaned_text,
        }

    # Export the parsed corpus to a JSON file with UTF-8 encoding
    with open("parsed_corpus.json", "w", encoding="utf-8") as f:
        json.dump(extracted_corpus, f, indent=4)

    print(
        f"Phase 2 Complete! Extracted data saved to parsed_corpus.json ({len(extracted_corpus)} documents)"
    )


if __name__ == "__main__":
    main()
