# database_actions.py
import sqlite3
from datetime import datetime
from config import DB_NAME
import pytz

def save_task(task_text, time):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (task, time) VALUES (?, ?)",
        (task_text, time)
    )
    conn.commit()
    conn.close()

def get_pending_tasks():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, task, time, notified_at FROM tasks WHERE status = 'pending'"
    )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def mark_task_missed(task_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'missed' WHERE id = ?",
        (task_id,)
    )
    conn.commit()
    conn.close()

def mark_task_completed(task_id, video_id, completed_at):
    TASHKENT_TZ = pytz.timezone("Asia/Tashkent")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = 'completed', video_id = ?, completed_at = ? WHERE id = ?",
        (video_id, datetime.now(TASHKENT_TZ).isoformat(), task_id)
    )
    conn.commit()
    conn.close()


def save_task_video(task_name: str, task_time: str, video_id: str, completed_at: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tasks (task, time, video_id, completed_at, status)
        VALUES (?, ?, ?, ?, 'completed')
    """, (task_name, task_time, video_id, completed_at))
    
    conn.commit()
    conn.close()

def get_latest_pending_task_id():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM tasks WHERE status = 'pending' ORDER BY id DESC LIMIT 1"
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_task_statistics():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    completed = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'missed'")
    missed = cursor.fetchone()[0]
    
    total = completed + missed
    completion_rate = (completed / total * 100) if total > 0 else 0
    
    conn.close()
    return completed, missed, completion_rate

def get_daily_response_times():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT date(notified_at), 
               (strftime('%s', completed_at) - strftime('%s', notified_at)) / 60.0 AS response_time
        FROM tasks 
        WHERE completed_at IS NOT NULL 
          AND notified_at IS NOT NULL
          AND completed_at > notified_at  -- Ensure positive response times
        ORDER BY date(notified_at)
    """)
    
    data = cursor.fetchall()
    conn.close()
    
    formatted_data = {}
    for date, response_minutes in data:
        if response_minutes is not None and response_minutes >= 0:
            if date not in formatted_data:
                formatted_data[date] = []
            formatted_data[date].append(response_minutes)
    
    return formatted_data