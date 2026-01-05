import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

from teller_client import TellerClient
from database import DatabaseClient

def normalize_account_type(subtype: str, type_: str) -> str:
    """Normalize Teller subtype/type to user's 3 preferred categories."""
    # subtype is usually more specific (checking, savings)
    if subtype in ("checking", "savings"):
        return subtype
    if type_ == "credit" or subtype == "credit_card":
        return "credit_card"
    return subtype or type_  # Fallback

def main():
    token = os.getenv("TELLER_TOKEN")
    if token:
        token = token.strip()
    cert_path = os.getenv("CERT")
    key_path = os.getenv("CERT_KEY")
    
    if not token:
        print("Error: TELLER_TOKEN env var is required.")
        return
        
    cert_tuple = None
    if cert_path and key_path:
        cert_tuple = (cert_path, key_path)
    
    # Initialize Clients
    teller = TellerClient(token=token, cert=cert_tuple)
    db = DatabaseClient()
    
    masked_token = token[:4] + "..." if len(token) > 4 else "***"
    print(f"Initializing TellerClient with token: {masked_token}")
    print("Database Client Initialized.")
    
    # Date Filter: July 2025
    CUTOFF_DATE = "2025-07-01"

    try:
        print("\n--- Fetching Accounts ---")
        accounts = teller.list_accounts()
        print(f"Found {len(accounts)} accounts.")
        
        for acc in accounts:
            print(f"Processing Account: {acc.name} ({acc.institution.name})")
            
            # --- CUSTOM ID OVERRIDE ---
            # User requested friendly names for IDs.
            # We map specific institutions to custom IDs if needed.
            db_acc_id = acc.id
            if "Bank of America" in acc.institution.name:
                db_acc_id = "bankofamerica"
            # --------------------------
            
            # 1. Upsert Account
            acc_type = normalize_account_type(acc.subtype, acc.type)
            acc_data = {
                "id": db_acc_id,
                "name": acc.name,
                "institution_name": acc.institution.name,
                "type": acc_type,
                "enrollment_id": acc.enrollment_id
            }
            res_acc = db.upsert_account(acc_data)
            if res_acc:
                print(f"  -> Saved to DB (ID: {db_acc_id}, Type: {acc_type})")
            else:
                print("  -> [!] Failed to save account to DB")

            # 2. Fetch Transactions (fetch a large batch to cover back to 2025)
            # Teller allows 'count' param. Pagination would be better for huge histories, 
            # but let's start with a large count.
            print(f"  -> Fetching transactions for {acc.name}...")
            transactions = teller.list_transactions(acc.id, count=1000)
            
            saved_count = 0
            skipped_count = 0
            
            for tx in transactions:
                # Filter by Date
                if tx.date < CUTOFF_DATE:
                    skipped_count += 1
                    continue
                
                # Upsert Transaction
                tx_data = {
                    "id": tx.id,
                    "account_id": db_acc_id, # Link to the (potentially overridden) DB account ID
                    "amount": float(tx.amount),
                    "date": tx.date,
                    "description": tx.description,
                    "status": tx.status,
                    "category": tx.details.get("category"),
                    "source": "teller",
                    "details": tx.details # Save raw details json
                }
                res_tx = db.upsert_transaction(tx_data)
                if res_tx:
                    saved_count += 1
            
            print(f"  -> Transactions: {saved_count} processed/verified (older than {CUTOFF_DATE} skipped)")
            
            # Send Notification if we actually saved meaningful data (optional: logic to distinguish new vs verified)
            # Since 'saved_count' currently tracks Upserts (which return true even on update), 
            # we might spam confirmations. For now, let's only notify if we decide to change the return logic
            # OR just notify that we ran successfully.
            # User request: "updated records".
            
            # Let's simple notify that we synced X txns for verification.
            if saved_count > 0:
                send_notification(saved_count, acc.name)

    except Exception as e:
        print(f"\nError occurred: {e}")

def send_notification(new_count, account_name):
    topic = os.getenv("NTFY_TOPIC", "personyfi_updates_123") # Default or Env Var
    if new_count > 0:
        try:
            requests.post(
                f"https://ntfy.sh/{topic}",
                data=f"💸 Processed {new_count} transactions for {account_name}".encode("utf-8"),
                headers={"Title": "New Finance Data", "Priority": "3"}
            )
            print(f"  -> Notification sent to ntfy.sh/{topic}")
        except Exception as e:
            print(f"  -> Notification failed: {e}")

if __name__ == "__main__":
    main()
