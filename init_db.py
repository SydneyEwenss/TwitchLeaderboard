import sqlite3

# Create the SQLite database file and tables
def create_db():
    # Connect to SQLite (this will create the database file if it doesn't exist)
    conn = sqlite3.connect('twitch_tracker.db')
    cursor = conn.cursor()

    # Create the streamers table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS streamers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        streams_this_year INTEGER DEFAULT 0
    )
    ''')

    # Create the streams table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS streams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        created_at TEXT
    )
    ''')

    # Commit and close connection
    conn.commit()
    conn.close()

    print("Database and tables created successfully.")

# Run the function to create the database and tables
if __name__ == '__main__':
    create_db()
