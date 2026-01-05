-- Enable UUID extension (usually enabled by default in Supabase, but good practice)
create extension if not exists "uuid-ossp";

-- Accounts Table
create table if not exists accounts (
  id text primary key, -- 'acc_...' from Teller or 'manual_...'
  name text not null,
  institution_name text,
  type text, -- 'credit', 'depository'
  enrollment_id text,
  last_visited_at timestamp with time zone default now()
);

-- Transactions Table
create table if not exists transactions (
  id text primary key, -- 'txn_...' from Teller or generated hash
  account_id text references accounts(id),
  amount numeric not null,
  date date not null,
  description text not null,
  status text, -- 'posted', 'pending'
  category text, 
  source text default 'teller', -- 'teller' or 'csv'
  details jsonb, -- Store raw extra details here
  created_at timestamp with time zone default now()
);

-- Indexes for performance
create index if not exists idx_transactions_account_id on transactions(account_id);
create index if not exists idx_transactions_date on transactions(date);
