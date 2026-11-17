import time
import threading
import requests
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import uuid

# --- Configuration ---
RENDEZVOUS_URL = "http://127.0.0.1:8000"
AGENT_IP = "127.0.0.1"
AGENT_PORT = 8001  # Should be dynamic in production
MY_PUBKEY = f"agent_{uuid.uuid4().hex[:8]}" # MVP Mock for Ed25519 PubKey

app = FastAPI(title=f"Swarm Agent Node - {MY_PUBKEY}")

class TaskRequest(BaseModel):
    sender_pubkey: str
    task_data: str

# --- P2P Server Logic ---
@app.post("/p2p/task")
def receive_task(req: TaskRequest):
    print(f"\n[P2P] Task received from {req.sender_pubkey}: {req.task_data}")
    # Proof-of-Utility: In a real scenario, compute happens here
    return {"status": "completed", "result": f"Successfully processed by {MY_PUBKEY}"}

# --- Rendezvous & Discovery Logic ---
def heartbeat_loop():
    """Keep agent registered in the Rendezvous server"""
    while True:
        try:
            payload = {"pubkey": MY_PUBKEY, "ip_port": f"{AGENT_IP}:{AGENT_PORT}"}
            requests.post(f"{RENDEZVOUS_URL}/heartbeat", json=payload, timeout=5)
            print(f"[Rendezvous] Heartbeat sent for {MY_PUBKEY}")
        except Exception as e:
            print(f"[Rendezvous] Connection failed: {e}")
        time.sleep(30)

def discover_and_trade():
    """Find peers and attempt direct P2P connections"""
    while True:
        time.sleep(35) # Wait for heartbeat to register first
        try:
            resp = requests.get(f"{RENDEZVOUS_URL}/peers", timeout=5)
            if resp.status_code == 200:
                peers = resp.json().get("peers", [])
                for p in peers:
                    if p["pubkey"] != MY_PUBKEY:
                        print(f"[P2P] Discovered peer: {p['pubkey']} at {p['ip_port']}")
                        # Attempt a P2P trade cycle
                        try:
                            task_payload = {"sender_pubkey": MY_PUBKEY, "task_data": "Ping! Requesting intelligence."}
                            peer_url = f"http://{p['ip_port']}/p2p/task"
                            peer_resp = requests.post(peer_url, json=task_payload, timeout=2)
                            print(f"[P2P] Trade successful with {p['pubkey']}: {peer_resp.json()}")
                        except:
                            print(f"[P2P] Peer {p['pubkey']} is unreachable.")
        except Exception as e:
            print(f"[Rendezvous] Peer discovery failed: {e}")

if __name__ == "__main__":
    print(f"Starting Swarm Agent: {MY_PUBKEY}")
    
    # Start background threads for Swarm networking
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=discover_and_trade, daemon=True).start()
    
    # Start local P2P server to receive requests from other agents
    uvicorn.run(app, host=AGENT_IP, port=AGENT_PORT)
