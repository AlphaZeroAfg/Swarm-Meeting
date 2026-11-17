"""
Swarm Meeting - TNP v0.1 Message Envelope & Schema Module
Genesis Architect: Ehsanullah Rahimi (Ehsan)
"""

from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field

# Supported TNP v0.1 Message Types
MessageType = Literal[
    "CAPABILITY_QUERY",
    "CAPABILITY_ANNOUNCE",
    "PROPOSE",
    "COUNTER",
    "ACCEPT",
    "REJECT",
    "CANCEL",
    "EXECUTE_TASK",
    "EXECUTE_RESULT",
    "VERIFY",
    "SETTLE",
    "DISPUTED"
]

class MessageEnvelope(BaseModel):
    protocol: Literal["swarm-tnp"] = "swarm-tnp"
    version: Literal["0.1"] = "0.1"
    msg_type: MessageType
    msg_id: str = Field(..., description="UUIDv4 unique message identifier")
    correlation_id: Optional[str] = Field(None, description="Links related messages in a negotiation flow")
    timestamp: int = Field(..., description="Epoch seconds timestamp")
    nonce: str = Field(..., description="Random hex string for replay mitigation")
    sender: str = Field(..., description="Sender Ed25519 public key hex")
    recipient: str = Field(..., description="Recipient Ed25519 public key hex")
    contract_id: Optional[str] = Field(None, description="Active contract UUID if applicable")
    body: Dict[str, Any] = Field(default_factory=dict, description="Payload corresponding to msg_type")
    signature: Optional[str] = Field(None, description="Base64 Ed25519 signature over canonicalized envelope")
