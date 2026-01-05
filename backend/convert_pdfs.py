import pdfplumber
import glob
import os
import re
import csv

PDF_DIR = "data/usbank"
OUTPUT_CSV = "usbank_transactions.csv"

def extract_from_pdf(pdf_path):
    transactions = []
    print(f"Processing {pdf_path}...")
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            
    lines = full_text.split('\n')
    
    date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2})')
    amount_pattern = re.compile(r'(-?\s?\$[\d,]+\.\d{2})')
    
    current_tx = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        # Check for new transaction start (Date)
        date_match = date_pattern.search(line)
        
        if date_match:
            # Save previous transaction if valid
            if current_tx and current_tx["amount"]:
                transactions.append(current_tx)

            # Start new
            raw_desc = line[len(date_match.group(1)):].strip()
            # print(f"DEBUG: Found Date {date_match.group(1)}. Raw Desc: '{raw_desc}'")
            
            # Check if this raw_desc is just a long ID (junk)
            if re.match(r'^[A-Za-z0-9_-]{15,}$', raw_desc):
                # print(f"DEBUG: Dropping ID-like desc: {raw_desc}")
                raw_desc = "" 
                
            current_tx = {
                "date": date_match.group(1),
                "description": raw_desc, 
                "amount": None,
                "desc_captured": bool(raw_desc)
            }
        elif current_tx:
            # We are inside a transaction block. Look for amount.
            # print(f"DEBUG: Checking amount on line: {repr(line)}")
            amount_match = amount_pattern.search(line)
            if amount_match:
                # Found amount
                # print(f"DEBUG: MATCHED AMOUNT: {amount_match.group(1)}")
                amt_str = amount_match.group(1).replace("$", "").replace(",", "").replace(" ", "")
                # print(f"DEBUG: Found Amount {amt_str} for {current_tx['date']}")
                current_tx["amount"] = amt_str
                
                # If we STILL haven't captured a description, maybe it's on this line?
                # e.g. "11:40 PM $60.00 Funds Transfer"
                if not current_tx["desc_captured"]:
                    # Remove amount and time
                    clean_line = amount_pattern.sub('', line)
                    clean_line = re.sub(r'\b\d{1,2}:\d{2}\s?(?:AM|PM)\b', '', clean_line).strip()
                    if clean_line:
                        # print(f"DEBUG: Captured desc from amount line: '{clean_line}'")
                        current_tx["description"] = clean_line
                        current_tx["desc_captured"] = True
                        
            else:
                # Text line. 
                # If we already have a description, IGNORE this line (User says it's location/junk)
                if not current_tx["desc_captured"]:
                   # Check if limit is too strict? 
                   # if re.match(r'^[A-Za-z0-9_-]{15,}$', line.strip()):
                   #    continue 
                   
                   current_tx["description"] = line.strip()
                   current_tx["desc_captured"] = True
                else:
                    # We already have a description line. 
                    # print(f"DEBUG: Skipping extra line (already have desc): '{line.strip()}'")
                    pass

    # Append last one
    if current_tx and current_tx["amount"]:
        transactions.append(current_tx)
        
    return transactions

def clean_description(desc):
    """Clean up raw PDF description text."""
    if not desc: return ""
    
    # 1. Remove timestamps (e.g. 11:40 PM)
    desc = re.sub(r'\b\d{1,2}:\d{2}\s?(?:AM|PM)\b', '', desc)
    
    # 2. Remove Timezones
    desc = re.sub(r'\b(?:CDT|CST|PST|PDT|EST|EDT)\b', '', desc)

    # 3. Remove "->" arrows
    desc = desc.replace('->', '')
    
    # 4. Remove location suffixes (State US) - keep it simple
    desc = re.sub(r'\s[A-Z]{2}\sUS\b', '', desc)
    desc = re.sub(r'\bUS\b$', '', desc)

    # Deduplicate repeated prefixes/words (e.g. "VENMO VENMO *Chase")
    words = desc.split()
    unique_words = []
    for w in words:
        if not unique_words or unique_words[-1].lower() != w.lower():
            unique_words.append(w)
    desc = " ".join(unique_words)

    # Remove generic "Funds Transfer with Validation" text
    desc = desc.replace('Funds Transfer with Validation', 'Transfer')

    # Collapse spaces
    desc = re.sub(r'\s+', ' ', desc).strip()
    
    return desc

def main():
    all_txs = []
    files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    if not files:
        print("No files found.")
        return

    for f in files:
        txs = extract_from_pdf(f)
        all_txs.extend(txs)
        
    # Write to CSV
    keys = ["date", "description", "amount"]
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for tx in all_txs:
            # Clean up description
            tx["description"] = clean_description(tx["description"])
            
            # Remove internal key if exists
            tx.pop("desc_captured", None)
            
            writer.writerow(tx)
            
    print(f"\nSuccessfully extracted {len(all_txs)} transactions to {OUTPUT_CSV}")
    print("Please review this file manually before ingesting!")

if __name__ == "__main__":
    main()
