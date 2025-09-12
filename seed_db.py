import sqlite3, os

DB_PATH = os.path.join("instance", "database.db")
os.makedirs("instance", exist_ok=True)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Create tables
c.execute("DROP TABLE IF EXISTS users")
c.execute("DROP TABLE IF EXISTS foods")

c.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

c.execute("""
CREATE TABLE foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT,
    calories INTEGER,
    protein REAL,
    fat REAL,
    carbs REAL
)
""")

# Insert sample user (username: admin, password: 1234)
c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("admin", "1234"))

# Insert sample foods
foods = [
    ("Burger", "junk", 500, 20, 25, 50),
    ("Pizza", "junk", 600, 22, 30, 55),
    ("French Fries", "junk", 400, 5, 22, 45),
    ("Salad", "healthy", 150, 5, 2, 20),
    ("Grilled Chicken", "healthy", 250, 35, 5, 0),
    ("Oatmeal", "healthy", 180, 6, 3, 30)
]

c.executemany("INSERT INTO foods (name, type, calories, protein, fat, carbs) VALUES (?, ?, ?, ?, ?, ?)", foods)

conn.commit()
conn.close()

print("Database created with sample data ✅")
