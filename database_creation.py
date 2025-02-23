# database_creation.py
import sqlite3
from config import DB_NAME

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Existing tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Changed to AUTOINCREMENT for consistency
                 task TEXT NOT NULL,
                 time TEXT NOT NULL,
                 status TEXT DEFAULT 'pending',
                 notified_at TEXT DEFAULT NULL,
                 video_id TEXT DEFAULT NULL,
                 completed_at TEXT DEFAULT NULL)''')
    
    # New bills table for tracking daily transactions
    c.execute('''CREATE TABLE IF NOT EXISTS bills (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 date TEXT NOT NULL,  -- Date of the transaction (YYYY-MM-DD)
                 type TEXT NOT NULL,  -- 'income', 'expense', or 'addition'
                 amount REAL NOT NULL,  -- Amount of money (positive for income/addition, negative for expense)
                 description TEXT,  -- Description or reason for the transaction
                 time TEXT NOT NULL  -- Time of the transaction (HH:MM)
                 )''')
    
    conn.commit()
    conn.close()