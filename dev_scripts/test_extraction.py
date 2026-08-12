import json
import re

def normalize_currency(value_str):
    if not value_str or not isinstance(value_str, str):
        return None
    val_clean = value_str.strip().replace(',', '')
    cr_match = re.search(r'([\d\.]+)\s*(?:cr|crore|crores)', val_clean, re.IGNORECASE)
    if cr_match:
        try:
            return int(round(float(cr_match.group(1)) * 10000000))
        except ValueError:
            pass
    lakh_match = re.search(r'([\d\.]+)\s*(?:lakh|lakhs)', val_clean, re.IGNORECASE)
    if lakh_match:
        try:
            return int(round(float(lakh_match.group(1)) * 100000))
        except ValueError:
            pass
    num_match = re.search(r'[\d\.]+', val_clean)
    if num_match:
        try:
            return int(round(float(num_match.group(0))))
        except ValueError:
            pass
    return None

def test():
    with open('parsed_corpus.json', 'r', encoding='utf-8') as f:
        corpus = json.load(f)
        
    print(f"Total documents loaded: {len(corpus)}")
    
    # Test currency normalization examples
    test_cases = [
        "INR 33.38 Cr",
        "33.38 Crore",
        "3,338 Lakh",
        "3338.00 Lakhs",
        "33,38,00,000",
        "333800000",
        "Rs. 65.46 Lakh"
    ]
    print("\nTesting currency normalization:")
    for tc in test_cases:
        print(f"  '{tc}' -> {normalize_currency(tc)}")

if __name__ == '__main__':
    test()
