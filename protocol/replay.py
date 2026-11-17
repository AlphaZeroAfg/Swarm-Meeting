"""
Swarm Meeting - TNP v0.1 Durable Replay Protection Module
Genesis Architect: Ehsanullah Rahimi (Ehsan)
"""

import sqlite3
import time
import os

DB_NAME = "replay_protection.db"

def init_replay_db():
    """Initializes the persistent SQLite database for replay protection."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS processed_messages (
            sender_pubkey TEXT,
            msg_id TEXT,
            received_at REAL,
            PRIMARY KEY (sender_pubkey, msg_id)
        )
    ''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_received_at ON processed_messages(received_at)")
    conn.commit()
    conn.close()

def is_replayed_or_expired(sender_pubkey: str, msg_id: str, timestamp: int, max_drift_seconds: int = 300) -> bool:
    """
    Checks if a message is replayed or its timestamp is out of the acceptable window.
    Performs atomic insertion into SQLite to prevent race conditions.
    """
    current_time = int(time.time())
    
    # 1. Time-drift check (reject messages too old or from the future)
    if abs(current_time - timestamp) > max_drift_seconds:
        return True  # Expired / Invalid timestamp window

    init_replay_db()
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    
    try:
        # Atomic insert attempt; fails if (sender_pubkey, msg_id) already exists (UNIQUE constraint)
        c.execute(
            "INSERT INTO processed_messages (sender_pubkey, msg_id, received_at) VALUES (?, ?, ?)",
            (sender_pubkey, msg_id, time.time())
        )
        conn.commit()
        is_duplicate = False
    except sqlite3.IntegrityError:
        # If integrity error occurs, the message ID has already been processed for this sender
        is_duplicate = True
    finally:
        conn.close()
        
    return is_duplicate

def cleanup_old_messages(max_age_seconds: int = 604800):
    """Purges processed message records older than max_age_seconds (default 7 days)."""
    if not os.path.exists(DB_NAME):
        return
    cutoff = time.time() - max_age_seconds
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    c.execute("DELETE FROM processed_messages WHERE received_at < ?", (cutoff,))
    conn.commit()
    conn.close()
