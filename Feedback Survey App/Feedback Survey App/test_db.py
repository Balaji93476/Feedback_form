from App import init_db
import sqlite3

# Initialize database
init_db()

# Check tables
conn = sqlite3.connect('feedback.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print('Tables:', tables)

# Check schema
for table in tables:
    table_name = table[0]
    c.execute(f"PRAGMA table_info({table_name})")
    columns = c.fetchall()
    print(f"\n{table_name} columns:")
    for col in columns:
        print(f"  {col}")

conn.close()
