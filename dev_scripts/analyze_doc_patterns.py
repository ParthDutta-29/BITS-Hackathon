import json
import re


def analyze():
    with open("parsed_corpus.json", "r", encoding="utf-8") as f:
        corpus = json.load(f)

    ccc_list = [
        v for v in corpus.values() if v["doc_type"] == "company_completion_certificate"
    ]
    cc_list = [v for v in corpus.values() if v["doc_type"] == "completion_certificate"]
    ref_list = [v for v in corpus.values() if v["doc_type"] == "reference_letter"]
    pcert_list = [
        v for v in corpus.values() if v["doc_type"] == "personnel_certificate"
    ]
    cv_list = [v for v in corpus.values() if v["doc_type"] == "cv"]

    print("Sample company_completion_certificate:")
    for doc in ccc_list[:3]:
        print("---")
        print(doc["filename"])
        print(doc["content"])

    print("\nSample completion_certificate:")
    for doc in cc_list[:3]:
        print("---")
        print(doc["filename"])
        print(doc["content"])

    print("\nSample reference_letter:")
    for doc in ref_list[:3]:
        print("---")
        print(doc["filename"])
        print(doc["content"])

    print("\nSample personnel_certificate:")
    for doc in pcert_list[:3]:
        print("---")
        print(doc["filename"])
        print(doc["content"])


if __name__ == "__main__":
    analyze()
