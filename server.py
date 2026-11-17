"""
Swarm Meeting - Rendezvous Node v1.2
Genesis Architect: Ehsanullah Rahimi (Ehsan)
Description: Decentralized P2P rendezvous protocol with cryptographic anti-poisoning.
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import sqlite3
import time
import threading
import re
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError
import base64

app = FastAPI(title="Swarm Meeting - Rendezvous Node v1.2")
DB_NAME = "rendezvous.db"
IP_PORT_REGEX = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}$")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS agents
                 (pubkey TEXT PRIMARY KEY, ip_port TEXT, last_seen REAL)''')
    c.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON agents(last_seen)")
    conn.commit()
    conn.close()

def cleanup_stale_agents():
    while True:
        time.sleep(300)
        try:
            conn = sqlite3.connect(DB_NAME, timeout=10)
            c = conn.cursor()
            cutoff = time.time() - 600
            c.execute("DELETE FROM agents WHERE last_seen < ?", (cutoff,))
            conn.commit()
            conn.close()
        except Exception:
            pass

init_db()
threading.Thread(target=cleanup_stale_agents, daemon=True).start()

class AgentHeartbeat(BaseModel):
    pubkey: str
    ip_port: str
    signature: str  # Ed25519 signature of (pubkey + ip_port)

@app.post("/heartbeat")
def heartbeat(agent: AgentHeartbeat):
    if not IP_PORT_REGEX.match(agent.ip_port):
        raise HTTPException(status_code=400, detail="Invalid ip_port format")
    
    # Verify Ed25519 Signature to prevent node-poisoning
    try:
        verify_key_bytes = bytes.fromhex(agent.pubkey)
        verify_key = VerifyKey(verify_key_bytes)
        message = f"{agent.pubkey}:{agent.ip_port}".encode('utf-8')
        sig_bytes = base64.b64decode(agent.signature.encode('utf-8'))
        verify_key.verify(message, sig_bytes)
    except (BadSignatureError, ValueError, Exception):
        raise HTTPException(status_code=401, detail="Invalid cryptographic signature")

    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    try:
        c.execute("REPLACE INTO agents (pubkey, ip_port, last_seen) VALUES (?, ?, ?)",
                  (agent.pubkey, agent.ip_port, time.time()))
        conn.commit()
    except sqlite3.Error:
        raise HTTPException(status_code=500, detail="Database busy")
    finally:
        conn.close()
    return {"status": "registered", "architect": "Ehsanullah Rahimi (Ehsan)"}

@app.get("/peers")
def get_peers(limit: int = 50):
    limit = min(limit, 100)
    conn = sqlite3.connect(DB_NAME, timeout=10)
    c = conn.cursor()
    cutoff = time.time() - 600
    c.execute("SELECT pubkey, ip_port FROM agents WHERE last_seen > ? ORDER BY RANDOM() LIMIT ?", (cutoff, limit))
    peers = [{"pubkey": row[0], "ip_port": row[1]} for row in c.fetchall()]
    conn.close()
    return {"peers": peers, "genesis_architect": "Ehsanullah Rahimi (Ehsan)"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
