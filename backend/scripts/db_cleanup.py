import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres.fhcnrqgbeqstedzmykia:WJxeXhP4QBEOLsBt@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres")
engine = create_engine(DATABASE_URL)

def cleanup():
    with engine.connect() as conn:
        conn.execute(text("COMMIT")) # Ensure we are in a transaction that can be committed
        
        print("--- Dropping RLS Policies ---")
        policies = [
            ("organizations", "Users can view their own organizations"),
            ("users_orgs", "Users can view their own memberships"),
            ("agents", "Users can view agents in their orgs"),
            ("calls", "Admins can delete calls in their org"),
            ("calls", "Admins can update calls in their org"),
            ("calls", "Users can view calls in their orgs"),
            ("qa_scores", "Users can view scores for calls in their orgs"),
        ]
        for table, policy in policies:
            try:
                conn.execute(text(f"DROP POLICY \"{policy}\" ON {table};"))
                print(f"Dropped policy {policy} on {table}")
            except Exception as e:
                print(f"Error dropping policy {policy} on {table}: {e}")

        print("\n--- Disabling RLS ---")
        tables_with_rls = ["organizations", "users_orgs", "agents", "calls", "qa_scores"]
        for table in tables_with_rls:
            try:
                conn.execute(text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
                print(f"Disabled RLS on {table}")
            except Exception as e:
                print(f"Error disabling RLS on {table}: {e}")

        print("\n--- Dropping users_orgs table ---")
        try:
            conn.execute(text("DROP TABLE IF EXISTS users_orgs CASCADE;"))
            print("Dropped users_orgs table")
        except Exception as e:
            print(f"Error dropping users_orgs: {e}")
        
        conn.commit()

if __name__ == "__main__":
    cleanup()
