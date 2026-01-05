from database import DatabaseClient
import sys

def main():
    db = DatabaseClient()
    if not db.client:
        print("Database connection failed.")
        sys.exit(1)
        
    print("WARNING: This will delete ALL transactions and accounts.")
    # Assuming cascade delete works or we delete transactions first
    # Supabase/Postgres usually requires deleting children first if no cascade
    
    print("Deleting existing transactions...")
    try:
        db.client.table("transactions").delete().neq("id", "0").execute()
    except Exception as e:
        print(f"Error deleting transactions: {e}")

    print("Deleting existing accounts...")
    try:
        db.client.table("accounts").delete().neq("id", "0").execute()
    except Exception as e:
        print(f"Error deleting accounts: {e}")

    # Seed new accounts
    accounts = [
        {
            "id": "usbank",
            "name": "US Bank Focus",
            "type": "checking",
            "institution_name": "US Bank"
        },
        {
            "id": "apple",
            "name": "Apple Card",
            "type": "credit_card",
            "institution_name": "Apple Card"
        },
        {
            "id": "discover",
            "name": "Discover Card",
            "type": "credit_card",
            "institution_name": "Discover"
        },
        # bankofamerica will typically be created by Teller logic, but we can seed it if needed.
        # However, Teller logic uses the ID returned by Teller API usually.
        # We need to see if we can force Teller to use 'bankofamerica'.
    ]
    
    print("Seeding new accounts...")
    for acc in accounts:
        res = db.upsert_account(acc)
        if res:
            print(f"Inserted: {acc['id']}")
        else:
            print(f"Failed: {acc['id']}")

if __name__ == "__main__":
    main()
