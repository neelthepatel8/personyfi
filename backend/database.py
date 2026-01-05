import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class DatabaseClient:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            print("Warning: SUPABASE_URL or SUPABASE_KEY not found in environment.")
            self.client = None
        else:
            try:
                self.client: Client = create_client(url, key)
            except Exception as e:
                print(f"Failed to initialize Supabase client: {e}")
                self.client = None

    def upsert_account(self, account_data: dict):
        """
        Upsert account into 'accounts' table.
        Expects dict with keys matching table columns.
        """
        if not self.client:
            return None
        
        try:
            data, count = self.client.table("accounts").upsert(account_data).execute()
            return data
        except Exception as e:
            print(f"Error upserting account {account_data.get('id')}: {e}")
            return None

    def upsert_transaction(self, transaction_data: dict):
        """
        Upsert transaction into 'transactions' table.
        """
        if not self.client:
            return None
            
        try:
            data, count = self.client.table("transactions").upsert(transaction_data).execute()
            return data
        except Exception as e:
            print(f"Error upserting transaction {transaction_data.get('id')}: {e}")
            return None

    def get_account(self, account_id: str):
        if not self.client: return None
        try:
            response = self.client.table("accounts").select("*").eq("id", account_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception:
            return None
