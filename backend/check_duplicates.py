from database import DatabaseClient
from collections import Counter

def main():
    db = DatabaseClient()
    if not db.client:
        print("Database connection failed.")
        return

    print("Fetching all transactions...")
    # Fetch all (this might be slow if thousands, but 1700 is fine)
    # Supabase limit is usually 1000, may need range
    
    all_txs = []
    
    # Simple pagination
    batch_size = 1000
    start = 0
    while True:
        res = db.client.table("transactions").select("*").range(start, start + batch_size - 1).execute()
        if not res.data:
            break
        all_txs.extend(res.data)
        if len(res.data) < batch_size:
            break
        start += batch_size

    print(f"Total rows fetched: {len(all_txs)}")

    # Check 1: Duplicate IDs
    ids = [t['id'] for t in all_txs]
    id_counts = Counter(ids)
    duplicates = [i for i, c in id_counts.items() if c > 1]
    
    if duplicates:
        print(f"CRITICAL: Found {len(duplicates)} duplicate IDs!")
    else:
        print("Pass: No duplicate IDs found (Primary Key integrity ok).")

    # Check 2: Content Duplicates (Same Date, Amount, Description, Account)
    # This detects if we ingested the same transaction twice with DIFFERENT IDs
    content_hashes = []
    for tx in all_txs:
        # Create a hash of the content
        # Round amount to 2 decimals to be safe
        amt = float(tx['amount'])
        content_key = (tx['account_id'], tx['date'], round(amt, 2), tx['description'])
        content_hashes.append(content_key)
        
    content_counts = Counter(content_hashes)
    content_dupes = {k: v for k, v in content_counts.items() if v > 1}
    
    if content_dupes:
        print(f"\nFound {len(content_dupes)} groups of potential content duplicates:")
        count = 0
        for k, v in content_dupes.items():
            if count < 5:
                # Find the IDs for this group
                group_ids = [t['id'] for t in all_txs if (t['account_id'], t['date'], round(float(t['amount']), 2), t['description']) == k]
                print(f"  - {v}x: {k}")
                print(f"    IDs: {group_ids}")
            count += 1
        if count >= 5: print("  ... and more")
    else:
        print("Pass: No content duplicates found.")

    # Breakdown by Source
    print("\nBreakdown by Account:")
    acc_counts = Counter([t['account_id'] for t in all_txs])
    for acc, c in acc_counts.items():
        print(f"  - {acc}: {c}")

if __name__ == "__main__":
    main()
