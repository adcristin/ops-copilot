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
columns = inspector.get_columns('users')
print("Columns in 'users' table:")
for col in columns:
    print(f"- {col['name']} ({col['type']})")
