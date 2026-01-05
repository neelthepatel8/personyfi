import csv
import sys
import uuid
import hashlib
from datetime import datetime
from database import DatabaseClient

def parse_date(date_str):
    """
    Attempt to parse date from common formats.
    Expected output: YYYY-MM-DD
    """
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

def generate_transaction_id(row_data):
    """Generates a deterministic ID based on row content to avoid duplicates."""
    unique_str = "".join(str(v) for v in row_data.values())
    return hashlib.md5(unique_str.encode()).hexdigest()

def ingest_csv(file_path: str, account_id: str, bank_name: str):
    db = DatabaseClient()
    if not db.client:
        print("Database not connected.")
        return

    print(f"Ingesting {file_path} for account {account_id} ({bank_name})...")
    
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        
        success_count = 0
        skip_count = 0
        
        for row in reader:
            # Map columns based on Bank Name (Simple heuristic mapping)
            # You might need to adjust these column names based on your actual CSVs!
            
            date = None
            amount = 0.0
            desc = ""
            
            # Common column names guess
            keys = row.keys()
            
            # DATE
            for k in ["date", "Date", "Transaction Date", "Posting Date", "post_date", "Trans. Date"]:
                if k in row: date = parse_date(row[k]); break
            
            # AMOUNT
            for k in ["Amount", "Transaction Amount", "amount", "Amount (USD)"]:
                if k in row: 
                    try:
                        amount = float(row[k].replace("$","").replace(",",""))
                        # Apple Card: Purchases are Positive, Payments are Negative.
                        # Discover: Purchases are Positive, Payments are Negative.
                        # We want Expenses to be Negative.
                        if ("Apple" in bank_name and k == "Amount (USD)") or ("Discover" in bank_name and k == "Amount"):
                            amount = -amount
                    except: pass
                    break
            
            # DESCRIPTION
            for k in ["description", "Description", "Merchant", "Transaction Description", "payee"]:
                if k in row: desc = row[k]; break

            if not date or not desc:
                print(f"Skipping invalid row: {row}")
                skip_count += 1
                continue

            # Generate ID
            tx_id = f"manual_{generate_transaction_id(row)}"
            
            tx_data = {
                "id": tx_id,
                "account_id": account_id,
                "amount": amount,
                "date": date,
                "description": desc,
                "status": "posted",
                "source": "csv",
                "details": row # Save full row for debug
            }
            
            if db.upsert_transaction(tx_data):
                success_count += 1
            else:
                skip_count += 1
                
        print(f"Done. Imported {success_count}, Skipped {skip_count}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ingest_state.py <csv_file> <account_id> [bank_name]")
        sys.exit(1)
        
    fpath = sys.argv[1]
    acc_id = sys.argv[2]
    bank = sys.argv[3] if len(sys.argv) > 3 else "Unknown"
    
    ingest_csv(fpath, acc_id, bank)
