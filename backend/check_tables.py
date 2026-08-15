import os
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    print("DATABASE_URL not found")
    exit(1)

engine = create_engine(url)
inspector = inspect(engine)
existing_tables = inspector.get_table_names()
expected_tables = [
    "agents", "calls", "organizations", "users", 
    "tasks", "background_tasks", "mailbox_items", "qa_scores"
]

print(f"Existing tables: {existing_tables}")
missing = [t for t in expected_tables if t not in existing_tables]
if missing:
    print(f"Missing tables: {missing}")
else:
    print("All expected tables exist.")
