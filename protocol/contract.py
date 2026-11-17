"""
Swarm Meeting - TNP v0.1 Contract Schema & Hashing Module
Genesis Architect: Ehsanullah Rahimi (Ehsan)
"""

import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from protocol.crypto import canonicalize_json
import hashlib

class ContractSchema(BaseModel):
    contract_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    protocol_version: str = Field(default="0.1")
    initiator: str = Field(..., description="Initiator public key hex")
    counterparty: str = Field(..., description="Counterparty public key hex")
    task_description: str = Field(..., description="Clear description of the task")
    task_hash: str = Field(..., description="SHA-256 hash of task details")
    capabilities_required: list[str] = Field(default_factory=list)
    terms: Dict[str, Any] = Field(..., description="Economic terms, compensation, and limits")
    verification_type: str = Field(..., description="STRUCTURAL, DETERMINISTIC, or SUBJECTIVE")
    deadline: int = Field(..., description="Epoch timestamp deadline for execution")
    created_at: int = Field(...)
    expires_at: int = Field(..., description="Proposal/Contract expiration timestamp")

def generate_contract_hash(contract: ContractSchema) -> str:
    """
    Computes a deterministic cryptographic hash of the contract contents 
    using canonical JSON formatting (RFC 8785 compliant approximation).
    """
    contract_dict = contract.model_dump(exclude={"signatures"}) if hasattr(contract, "signatures") else contract.model_dump()
    canonical_bytes = canonicalize_json(contract_dict)
    return hashlib.sha256(canonical_bytes).hexdigest()
