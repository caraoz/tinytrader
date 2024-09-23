import sqlite3

def create_schema():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    # Create the cleared_trades table
    c.execute('''
        CREATE TABLE IF NOT EXISTS cleared_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            order_type TEXT NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            cleared_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            filler_user_id TEXT NOT NULL,
            filled_user_id TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_schema()
    print("Database schema for cleared trades created successfully.")