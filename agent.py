import asyncio
import logging
import os
import random
import uuid
from contextlib import asynccontextmanager
import httpx
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

# --- Standard Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("SwarmAgent")

# --- Environment-Aware Configuration ---
RENDEZVOUS_URL = os.getenv("RENDEZVOUS_URL", "http://127.0.0.1:8000")
AGENT_IP = os.getenv("AGENT_IP", "127.0.0.1")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))
MY_PUBKEY = os.getenv("AGENT_PUBKEY", f"agent_{uuid.uuid4().hex[:12]}")
MAX_CONCURRENT_TRADES = 5
MAX_PEERS_PER_CYCLE = 5

# Track unreachable peers: {pubkey: consecutive_failures}
failed_peers: dict[str, int] = {}
shutdown_event = asyncio.Event()

class TaskRequest(BaseModel):
    sender_pubkey: str = Field(..., min_length=4, max_length=128)
    task_data: str = Field(..., min_length=1, max_length=2048)
    signature: str = Field(default="placeholder", max_length=256)

async def heartbeat_loop(client: httpx.AsyncClient):
    """Non-blocking heartbeat with exponential backoff"""
    backoff = 5
    while not shutdown_event.is_set():
        try:
            payload = {
                "pubkey": MY_PUBKEY,
                "ip_port": f"{AGENT_IP}:{AGENT_PORT}",
                "signature": "placeholder"
            }
            resp = await client.post(f"{RENDEZVOUS_URL}/heartbeat", json=payload, timeout=5.0)
            resp.raise_for_status()
            logger.info(f"[Rendezvous] Heartbeat registered for {MY_PUBKEY}")
            backoff = 5  # Reset on success
            await asyncio.sleep(30)
        except Exception as e:
            logger.warning(f"[Rendezvous] Heartbeat failed: {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 120)

async def trade_with_peer(client: httpx.AsyncClient, sem: asyncio.Semaphore, peer: dict):
    """Execute a single P2P request bounded by a concurrency semaphore"""
    pubkey = peer.get("pubkey")
    ip_port = peer.get("ip_port")
    if not pubkey or not ip_port:
        return

    async with sem:
        try:
            task_payload = {
                "sender_pubkey": MY_PUBKEY,
                "task_data": "Ping! Requesting Swarm intelligence.",
                "signature": "placeholder"
            }
            peer_url = f"http://{ip_port}/p2p/task"
            resp = await client.post(peer_url, json=task_payload, timeout=3.0)
            resp.raise_for_status()
            failed_peers.pop(pubkey, None)  # Reset failure count on success
            logger.info(f"[P2P] Trade successful with {pubkey}: {resp.json()}")
        except Exception as e:
            failed_peers[pubkey] = failed_peers.get(pubkey, 0) + 1
            logger.debug(f"[P2P] Peer {pubkey} unreachable (fails: {failed_peers[pubkey]}): {e}")

async def discover_and_trade(client: httpx.AsyncClient):
    """Async peer discovery with random sampling and dead-peer filtering"""
    sem = asyncio.Semaphore(MAX_CONCURRENT_TRADES)
    await asyncio.sleep(10)  # Wait for initial heartbeat
    while not shutdown_event.is_set():
        try:
            resp = await client.get(f"{RENDEZVOUS_URL}/peers", timeout=5.0)
            resp.raise_for_status()
            all_peers = resp.json().get("peers", [])

            # Exclude self and peers with >= 3 consecutive failures
            candidates = [
                p for p in all_peers
                if p.get("pubkey") != MY_PUBKEY and failed_peers.get(p.get("pubkey"), 0) < 3
            ]

            selected = random.sample(candidates, min(len(candidates), MAX_PEERS_PER_CYCLE))
            if selected:
                logger.info(f"[P2P] Initiating concurrent trade with {len(selected)} peer(s)")
                await asyncio.gather(*(trade_with_peer(client, sem, p) for p in selected))
        except Exception as e:
            logger.warning(f"[Rendezvous] Peer discovery error: {e}")

        await asyncio.sleep(35)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage graceful startup and shutdown of background P2P tasks"""
    logger.info(f"Starting Swarm Agent Node: {MY_PUBKEY} on {AGENT_IP}:{AGENT_PORT}")
    async with httpx.AsyncClient() as client:
        hb_task = asyncio.create_task(heartbeat_loop(client))
        dt_task = asyncio.create_task(discover_and_trade(client))
        yield
        logger.info("Shutting down Swarm Agent gracefully...")
        shutdown_event.set()
        hb_task.cancel()
        dt_task.cancel()
        await asyncio.gather(hb_task, dt_task, return_exceptions=True)

app = FastAPI(title=f"Swarm Agent Node v1.1.1 - {MY_PUBKEY}", lifespan=lifespan)

@app.post("/p2p/task")
async def receive_task(req: TaskRequest):
    logger.info(f"[P2P] Task received from {req.sender_pubkey}: {req.task_data[:60]}")
    return {"status": "completed", "responder": MY_PUBKEY}

if __name__ == "__main__":
    uvicorn.run(app, host=AGENT_IP, port=AGENT_PORT)
