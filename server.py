import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import time

app = FastAPI(title="Swarm Meeting - Rendezvous Node v1.1")

# Database Setup
DB_NAME = "rendezvous.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS agents
                 (pubkey TEXT PRIMARY KEY, ip_port TEXT, last_seen REAL)''')
    conn.commit()
    conn.close()

init_db()

class AgentHeartbeat(BaseModel):
    pubkey: str
    ip_port: str

@app.post("/heartbeat")
def heartbeat(agent: AgentHeartbeat):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("REPLACE INTO agents (pubkey, ip_port, last_seen) VALUES (?, ?, ?)",
              (agent.pubkey, agent.ip_port, time.time()))
    conn.commit()
    conn.close()
    return {"status": "registered"}

@app.get("/peers")
def get_peers():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Return peers seen in the last 10 minutes (600 seconds)
    cutoff = time.time() - 600
    c.execute("SELECT pubkey, ip_port FROM agents WHERE last_seen > ?", (cutoff,))
    peers = [{"pubkey": row[0], "ip_port": row[1]} for row in c.fetchall()]
    conn.close()
    return {"peers": peers}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
