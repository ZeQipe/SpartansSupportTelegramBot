import sqlite3
from typing import List, Dict

class HistoryManager:
    def __init__(self, db_path: str = 'conversation_history.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.init_db()
    
    def init_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            role TEXT,
            content TEXT
        )''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON messages (user_id)')
        self.conn.commit()
    
    def add_message(self, user_id: int, role: str, content: str):
        cursor = self.conn.cursor()
        cursor.execute('INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
        self.conn.commit()
        # Limit to 20: delete oldest if over
        cursor.execute('SELECT COUNT(*) FROM messages WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        if count > 20:
            cursor.execute('''DELETE FROM messages WHERE id IN (
                SELECT id FROM messages WHERE user_id = ? ORDER BY timestamp ASC LIMIT ?
            )''', (user_id, count - 20))
            self.conn.commit()
    
    def get_history(self, user_id: int) -> List[Dict[str, str]]:
        cursor = self.conn.cursor()
        # Fetch last 20 messages in insertion order using auto-incremented id for reliable ordering
        cursor.execute('SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 20', (user_id,))
        rows = cursor.fetchall()
        return [{'role': row[0], 'content': row[1]} for row in reversed(rows)]  # Reverse to chronological order
    
    def reset_history(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM messages WHERE user_id = ?', (user_id,))
        self.conn.commit()
    
    def __del__(self):
        self.conn.close() 