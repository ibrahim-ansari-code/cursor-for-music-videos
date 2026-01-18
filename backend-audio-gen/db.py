import sqlite3
import os
from pathlib import Path


class VoiceCache:
    def __init__(self, db_path: str = "./voice_cache.db"):
        self.db_path = db_path
        self._create_table()
    
    def _create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voices (
                book_id TEXT,
                character_id TEXT,
                voice_id TEXT,
                PRIMARY KEY(book_id, character_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def get_voice_id(self, book_id: str, character_id: str) -> str | None:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT voice_id FROM voices WHERE book_id = ? AND character_id = ?",
            (book_id, character_id)
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    
    def set_voice_id(self, book_id: str, character_id: str, voice_id: str):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO voices (book_id, character_id, voice_id) VALUES (?, ?, ?)",
            (book_id, character_id, voice_id)
        )
        conn.commit()
        conn.close()
