import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import time
import threading
import re

app = FastAPI(title="Swarm Meeting - Rendezvous Node v1.1.1")
DB_NAME = "rendezvous.db"

# Regex for basic IP:PORT validation
IP_PORT_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}$")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    # Enable WAL mode for high concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS agents
                 (pubkey TEXT PRIMARY KEY, ip_port TEXT, last_seen REAL)''')
    # Create Index for faster queries
    c.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON agents(last_seen)")
    conn.commit()
    conn.close()

def cleanup_stale_agents():
    """Background thread to prevent infinite DB growth by removing old records"""
    while True:
        time.sleep(300) # Run every 5 minutes
        try:
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            cutoff = time.time() - 600
            c.execute("DELETE FROM agents WHERE last_seen < ?", (cutoff,))
            conn.commit()
            conn.close()
            print("[Cleanup] Stale agents removed.")
        except Exception as e:
            print(f"[Cleanup Error] {e}")

init_db()
# Start the cleanup worker
threading.Thread(target=cleanup_stale_agents, daemon=True).start()

class AgentHeartbeat(BaseModel):
    pubkey: str
    ip_port: str
    signature: str = "placeholder" # Ready for Ed25519 enforcement

@app.post("/heartbeat")
def heartbeat(agent: AgentHeartbeat):
    if not IP_PORT_REGEX.match(agent.ip_port):
        raise HTTPException(status_code=400, detail="Invalid ip_port format")
    
    # Timeout=10 added to prevent 'database is locked' errors
    conn = sqlite3.connect(DB_NAME, timeout=10) 
    c = conn.cursor()
    try:
        c.execute("REPLACE INTO agents (pubkey, ip_port, last_seen) VALUES (?, ?, ?)",
                  (agent.pubkey, agent.ip_port, time.time()))
        conn.commit()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database busy, try again")
    finally:
        conn.close()
    return {"status": "registered"}

@app.get("/peers")
def get_peers(limit: int = 50):
    limit = min(limit, 100) # Anti-Flooding cap
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    cutoff = time.time() - 600
    # RANDOM() helps distribute connections rather than hitting the same peers
    c.execute("SELECT pubkey, ip_port FROM agents WHERE last_seen > ? ORDER BY RANDOM() LIMIT ?", (cutoff, limit))
    peers = [{"pubkey": row[0], "ip_port": row[1]} for row in c.fetchall()]
    conn.close()
    return {"peers": peers}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
