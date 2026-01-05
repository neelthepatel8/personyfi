from database import DatabaseClient

def main():
    db = DatabaseClient()
    if not db.client: return
    
    res = db.client.table("transactions").select("id", count="exact").execute()
    total = res.count
    print(f"Total Transactions: {total}")
    
    # Check Accounts
    res_acc = db.client.table("accounts").select("*").execute()
    print("\nAccounts Used:")
    for acc in res_acc.data:
        print(f"- {acc['id']} ({acc['name']}, {acc['type']})")
        
    print("\nSample Data:")
    res_tx = db.client.table("transactions").select("account_id, source").limit(5).execute()
    for row in res_tx.data:
        print(row)

if __name__ == "__main__":
    main()
