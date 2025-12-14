import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "nutrition.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            daily_calorie_goal INTEGER DEFAULT 2000
        )
    ''')
    
    # Create logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            food_name TEXT,
            calories INTEGER,
            protein REAL,
            carbs REAL,
            fats REAL,
            micronutrients TEXT,
            health_score INTEGER,
            meal_period TEXT DEFAULT 'Snack',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Migration: Add new columns if they don't exist (for existing DBs)
    try:
        cursor.execute("ALTER TABLE logs ADD COLUMN micronutrients TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists
        
    try:
        cursor.execute("ALTER TABLE logs ADD COLUMN health_score INTEGER")
    except sqlite3.OperationalError:
        pass # Column likely exists

    try:
        cursor.execute("ALTER TABLE logs ADD COLUMN meal_period TEXT DEFAULT 'Snack'")
    except sqlite3.OperationalError:
        pass # Column likely exists

    try:
        cursor.execute("ALTER TABLE logs ADD COLUMN meal_group_id TEXT")
    except sqlite3.OperationalError:
        pass # Column likely exists
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_logs_by_group(meal_group_id: str):
    """
    Retrieves all logs belonging to a specific meal group.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs WHERE meal_group_id = ?", (meal_group_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_daily_summary(user_id: int):
    """
    Retrieves the total nutrition for the current day for a specific user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            SUM(calories) as total_calories,
            SUM(protein) as total_protein,
            SUM(carbs) as total_carbs,
            SUM(fats) as total_fats,
            AVG(health_score) as avg_health_score,
            GROUP_CONCAT(food_name, ', ') as food_items
        FROM logs 
        WHERE user_id = ? AND date(timestamp) = date('now')
    ''', (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    return row

def get_daily_logs(user_id: int):
    """
    Retrieves all individual log entries for the current day.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * 
        FROM logs 
        WHERE user_id = ? AND date(timestamp) = date('now')
        ORDER BY timestamp DESC
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_log(log_id: int):
    """
    Deletes a specific log entry by ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()

def clear_daily_logs(user_id: int):
    """
    Deletes all logs for the current day for a specific user.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs WHERE user_id = ? AND date(timestamp) = date('now')", (user_id,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
