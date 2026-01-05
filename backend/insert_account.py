from database import DatabaseClient
import sys

def main():
    db = DatabaseClient()
    if not db.client:
        print("Database connection failed.")
        sys.exit(1)
        
    account = {
        "id": "manual_discover",
        "name": "Discover Card",
        "type": "credit_card", 
        "institution_name": "Discover"
    }
    
    res = db.upsert_account(account)
    if res:
        print(f"Successfully inserted account: {account['id']}")
    else:
        print("Failed to insert account.")
        sys.exit(1)

if __name__ == "__main__":
    main()
