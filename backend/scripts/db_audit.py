import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.fhcnrqgbeqstedzmykia:WJxeXhP4QBEOLsBt@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres")
engine = create_engine(DATABASE_URL)

def audit():
    with engine.connect() as conn:
        print("--- Tables ---")
        res = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname != 'pg_catalog' AND schemaname != 'information_schema';"))
        for row in res:
            print(row[0])

        print("\n--- RLS Policies ---")
        res = conn.execute(text("SELECT tablename, policyname FROM pg_policies;"))
        for row in res:
            print(f"Table: {row[0]}, Policy: {row[1]}")

        print("\n--- auth.users count ---")
        try:
            res = conn.execute(text("SELECT count(*) FROM auth.users;"))
            print(res.scalar())
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    audit()
