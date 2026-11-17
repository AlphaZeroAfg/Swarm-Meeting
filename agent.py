"""
Swarm Agent Node v1.2
Genesis Architect: Ehsanullah Rahimi (Ehsan)
Description: P2P Agent with Ed25519 Identity & Economic Debt Cap (D_0 = 10).
"""

import asyncio
import logging
import os
import random
import base64
from contextlib import asynccontextmanager
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SwarmAgent")

# --- Genesis Architect Identity ---
GENESIS_ARCHITECT = "Ehsanullah Rahimi (Ehsan)"

# --- Key Management ---
KEY_FILE = "agent.key"
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        signing_key = SigningKey(f.read())
    logger.info("[Identity] Loaded existing Ed25519 key from disk.")
else:
    signing_key = SigningKey.generate()
    with open(KEY_FILE, "wb") as f:
        f.write(signing_key.encode())
    logger.info("[Identity] Generated new Ed25519 key pair.")

my_verify_key = signing_key.verify_key
MY_PUBKEY_HEX = my_verify_key.encode().hex()

RENDEZVOUS_URL = os.getenv("RENDEZVOUS_URL", "http://127.0.0.1:8000")
AGENT_IP = os.getenv("AGENT_IP", "127.0.0.1")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8001"))
MAX_DEBT_CAP = 10  # D_0 = 10

# Economic Ledger: Tracks debt owed to/by peers
peer_debts: dict[str, int] = {}
failed_peers: dict[str, int] = {}
shutdown_event = asyncio.Event()

class TaskRequest(BaseModel):
    sender_pubkey: str
    task_data: str
    signature: str

async def heartbeat_loop(client: httpx.AsyncClient):
    backoff = 5
    while not shutdown_event.is_set():
        try:
            message = f"{MY_PUBKEY_HEX}:{AGENT_IP}:{AGENT_PORT}".encode('utf-8')
            signed = signing_key.sign(message)
            sig_b64 = base64.b64encode(signed.signature).decode('utf-8')

            payload = {
                "pubkey": MY_PUBKEY_HEX,
                "ip_port": f"{AGENT_IP}:{AGENT_PORT}",
                "signature": sig_b64
            }
            resp = await client.post(f"{RENDEZVOUS_URL}/heartbeat", json=payload, timeout=5.0)
            resp.raise_for_status()
            logger.info(f"[Rendezvous] Heartbeat registered under Architect: {GENESIS_ARCHITECT}")
            backoff = 5
            await asyncio.sleep(30)
        except Exception as e:
            logger.warning(f"[Rendezvous] Heartbeat failed: {e}. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 120)

async def trade_with_peer(client: httpx.AsyncClient, peer: dict):
    pubkey = peer.get("pubkey")
    ip_port = peer.get("ip_port")
    if not pubkey or not ip_port:
        return

    # Check Debt Cap before requesting service
    current_debt = peer_debts.get(pubkey, 0)
    if current_debt >= MAX_DEBT_CAP:
        logger.warning(f"[Economy] Debt cap D_0 reached for peer {pubkey[:8]}... Trade blocked until settlement.")
        return

    try:
        task_text = "Requesting swarm compute intelligence."
        message = f"{MY_PUBKEY_HEX}:{task_text}".encode('utf-8')
        signed = signing_key.sign(message)
        sig_b64 = base64.b64encode(signed.signature).decode('utf-8')

        payload = {"sender_pubkey": MY_PUBKEY_HEX, "task_data": task_text, "signature": sig_b64}
        resp = await client.post(f"http://{ip_port}/p2p/task", json=payload, timeout=3.0)
        resp.raise_for_status()
        
        # Successful interaction increases debt toward peer (we consumed resources)
        peer_debts[pubkey] = current_debt + 1
        failed_peers.pop(pubkey, None)
        logger.info(f"[P2P Trade] Success with {pubkey[:8]}... Current local debt ledger: {peer_debts[pubkey]}/{MAX_DEBT_CAP}")
    except Exception as e:
        failed_peers[pubkey] = failed_peers.get(pubkey, 0) + 1
        logger.debug(f"[P2P] Peer {pubkey[:8]} unreachable: {e}")

async def discover_and_trade(client: httpx.AsyncClient):
    await asyncio.sleep(10)
    while not shutdown_event.is_set():
        try:
            resp = await client.get(f"{RENDEZVOUS_URL}/peers", timeout=5.0)
            resp.raise_for_status()
            all_peers = resp.json().get("peers", [])
            candidates = [p for p in all_peers if p.get("pubkey") != MY_PUBKEY_HEX and failed_peers.get(p.get("pubkey"), 0) < 3]
            selected = random.sample(candidates, min(len(candidates), 3))
            for p in selected:
                await trade_with_peer(client, p)
        except Exception as e:
            logger.warning(f"[Discovery] Error: {e}")
        await asyncio.sleep(35)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Initializing Swarm Agent. Architect: {GENESIS_ARCHITECT} | PubKey: {MY_PUBKEY_HEX[:16]}...")
    async with httpx.AsyncClient() as client:
        hb = asyncio.create_task(heartbeat_loop(client))
        dt = asyncio.create_task(discover_and_trade(client))
        yield
        shutdown_event.set()
        hb.cancel()
        dt.cancel()
        await asyncio.gather(hb, dt, return_exceptions=True)

app = FastAPI(title=f"Swarm Agent - {GENESIS_ARCHITECT}", lifespan=lifespan)

@app.post("/p2p/task")
async def receive_task(req: TaskRequest):
    # Verify sender signature
    try:
        v_key = VerifyKey(bytes.fromhex(req.sender_pubkey))
        msg = f"{req.sender_pubkey}:{req.task_data}".encode('utf-8')
        v_key.verify(msg, base64.b64decode(req.signature.encode('utf-8')))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid P2P signature")

    logger.info(f"[P2P Task] Verified task received from {req.sender_pubkey[:8]}...")
    return {"status": "completed", "architect": GENESIS_ARCHITECT}

if __name__ == "__main__":
    uvicorn.run(app, host=AGENT_IP, port=AGENT_PORT)
